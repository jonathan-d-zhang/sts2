from typing import Annotated, Literal

from fastapi import APIRouter, Query
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from sts2.database import get_pool
from sts2.models import Run

router = APIRouter(prefix="/api/v1")


class RunSummary(BaseModel):
    id: int
    ascension: int
    win: bool
    build_id: str


class RunsPage(BaseModel):
    items: list[RunSummary]
    total: int
    wins: int
    limit: int
    offset: int


@router.get("/runs")
async def list_runs(
    cards: Annotated[list[str] | None, Query()] = None,
    mode: Annotated[Literal["single", "multi", "both"], Query()] = "single",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunsPage:
    cards = cards or []
    conditions: list[str] = []
    params: list = []

    if cards:
        # GIN index on decks.card_ids makes the containment check efficient.
        conditions.append("EXISTS (SELECT 1 FROM decks d WHERE d.run_id = r.id AND d.card_ids @> %s::text[])")
        params.append(cards)
    if mode == "single":
        conditions.append("jsonb_array_length(r.data->'players') = 1")
    elif mode == "multi":
        conditions.append("jsonb_array_length(r.data->'players') > 1")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    query = f"""
        SELECT r.id, r.ascension, r.win, r.build_id,
               COUNT(*) OVER () AS total,
               SUM(CASE WHEN r.win THEN 1 ELSE 0 END) OVER () AS wins
        FROM runs r
        {where}
        ORDER BY r.id DESC
        LIMIT %s OFFSET %s
        """  # noqa: S608
    async with get_pool().connection() as conn:
        rows = await (await conn.execute(query, params)).fetchall()

    return RunsPage(
        items=[RunSummary(id=r[0], ascension=r[1], win=r[2], build_id=r[3]) for r in rows],
        total=rows[0][4] if rows else 0,
        wins=rows[0][5] if rows else 0,
        limit=limit,
        offset=offset,
    )


@router.get("/cards")
async def list_cards() -> list[str]:
    async with get_pool().connection() as conn:
        rows = await (
            await conn.execute("SELECT DISTINCT unnest(card_ids) AS card_id FROM decks ORDER BY card_id")
        ).fetchall()
    return [r[0] for r in rows]


@router.post("/runs", status_code=201)
async def create_runs(runs: list[Run]) -> dict[str, list[int]]:
    if not runs:
        return {"ids": []}
    placeholders = ", ".join(["(%s, %s, %s, %s)"] * len(runs))
    run_values = [v for run in runs for v in (run.ascension, run.win, run.build_id, Jsonb(run.model_dump(mode="json")))]
    async with get_pool().connection() as conn, conn.transaction():
        query = f"INSERT INTO runs (ascension, win, build_id, data) VALUES {placeholders} RETURNING id"  # noqa: S608
        ids = [row[0] for row in await (await conn.execute(query, run_values)).fetchall()]
        deck_params = [
            (run_id, [card.id for card in player.deck])
            for run_id, run in zip(ids, runs, strict=True)
            for player in run.players
        ]
        if deck_params:
            async with conn.cursor() as cur:
                await cur.executemany(
                    "INSERT INTO decks (run_id, card_ids) VALUES (%s, %s)",
                    deck_params,
                )
    return {"ids": ids}
