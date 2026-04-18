# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                   # install all dependencies (including dev)
uv run pytest             # run all tests
uv run pytest tests/test_runs.py::test_list_runs_empty  # run a single test
uv run uvicorn sts2:app --reload  # run the dev server
docker compose up --build # run app + postgres locally
```

Pre-commit hooks run ruff-format and ruff on every commit. To run manually:
```bash
uv run ruff check --fix --select I .
uv run ruff format .
uv run ruff check --fix .
```

## Architecture

This is a FastAPI app that serves a static site and exposes a JSON API for Slay the Spire 2 run history.

**Entry point:** `src/sts2/__init__.py` — creates the `FastAPI` app, wires the lifespan (pool open → DB init → pool close), registers routers, and mounts the static site from `site/` at `/`.

**Request flow:** `src/sts2/routers/runs.py` → `src/sts2/database.py` (psycopg3 async pool via `get_pool()`) → PostgreSQL.

**Database lifecycle:** `database.py` exposes `open_pool` / `close_pool` / `init_db` (runs `schema.sql`) and a `get_pool()` getter. The pool is a module-level private `_pool`; importing the name directly doesn't work — always call `get_pool()` at request time.

**Schema:** Two tables. `runs` stores top-level fields (`ascension`, `win`, `build_id`) plus the full run payload as `data JSONB`. `decks` stores each player's final card IDs as `TEXT[]` with a GIN index for efficient card-containment queries (`@>`).

**Models:** `src/sts2/models.py` defines the full Pydantic v2 schema for `.run` JSON files. `Run = SinglePlayerRun | MultiPlayerRun` — discriminated by checking `len(players)`. The parser is in `src/sts2/history.py`.

**Config:** `src/sts2/config.py` uses `pydantic-settings` with the `STS2_` env prefix. `STS2_DATABASE_URL` is the only required variable. Tests set it via `tests/conftest.py` before any `sts2` import.

**Testing:** Tests mock `open_pool`, `init_db`, and `get_pool` so no real database is needed. The `client` fixture in `test_runs.py` is `scope="module"` — the lifespan runs once per file.
