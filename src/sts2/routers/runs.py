from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from psycopg.types.json import Jsonb

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
    limit: int
    offset: int


@router.get("/runs")
async def list_runs(
    cards: Annotated[list[str], Query()] = [],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunsPage:
    # GIN index on decks.card_ids makes the containment check efficient.
    where = (
        "WHERE EXISTS (SELECT 1 FROM decks d WHERE d.run_id = r.id AND d.card_ids @> %s::text[])"
        if cards
        else ""
    )
    params = ([cards] if cards else []) + [limit, offset]

    async with get_pool().connection() as conn:
        rows = await (
            await conn.execute(
                f"""
                SELECT r.id, r.ascension, r.win, r.build_id
                FROM runs r
                {where}
                ORDER BY r.id DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
        ).fetchall()

    return RunsPage(
        items=[
            RunSummary(id=r[0], ascension=r[1], win=r[2], build_id=r[3]) for r in rows
        ],
        limit=limit,
        offset=offset,
    )


@router.post("/run", status_code=201)
async def create_run(run: Run) -> dict[str, int]:
    async with get_pool().connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                """
                INSERT INTO runs (ascension, win, build_id, data)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    run.ascension,
                    run.win,
                    run.build_id,
                    Jsonb(run.model_dump(mode="json")),
                ),
            )
            run_id = (await cur.fetchone())[0]

            for player in run.players:
                await conn.execute(
                    "INSERT INTO decks (run_id, card_ids) VALUES (%s, %s)",
                    (run_id, [card.id for card in player.deck]),
                )

    return {"id": run_id}
