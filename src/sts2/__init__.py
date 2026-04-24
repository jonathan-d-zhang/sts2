from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import sts2.database as _db
from sts2.routers.runs import router as runs_router

SITE_DIR = Path(__file__).parent.parent.parent / "site"
SITE_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await _db.open_pool()
    await _db.init_db()
    yield
    await _db.close_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(runs_router)
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
