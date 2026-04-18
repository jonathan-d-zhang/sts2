from fastapi import APIRouter
from psycopg.types.json import Jsonb

from sts2.database import get_pool
from sts2.models import Run

router = APIRouter(prefix="/api/v1")


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
