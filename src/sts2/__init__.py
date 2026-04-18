from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from sts2.database import close_pool, init_db, open_pool
from sts2.routers.runs import router as runs_router

SITE_DIR = Path(__file__).parent.parent.parent / "site"
SITE_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    await init_db()
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(runs_router)
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
