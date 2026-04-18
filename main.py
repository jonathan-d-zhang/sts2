from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

SITE_DIR = Path(__file__).parent / "site"
SITE_DIR.mkdir(exist_ok=True)

app = FastAPI()

app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
