from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sts2 import app


def make_pool(rows: list) -> MagicMock:
    cursor = MagicMock()
    cursor.fetchall = AsyncMock(return_value=rows)
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=cursor)
    pool = MagicMock()
    pool.connection.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.connection.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


@pytest.fixture(scope="module")
def client():
    with (
        patch("sts2.database.open_pool", new_callable=AsyncMock),
        patch("sts2.database.init_db", new_callable=AsyncMock),
        TestClient(app) as c,
    ):
        yield c


def test_list_runs_returns_items(client):
    rows = [(1, 10, True, "build_001"), (2, 5, False, "build_002")]
    with patch("sts2.database.get_pool", return_value=make_pool(rows)):
        resp = client.get("/api/v1/runs")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == [
        {"id": 1, "ascension": 10, "win": True, "build_id": "build_001"},
        {"id": 2, "ascension": 5, "win": False, "build_id": "build_002"},
    ]
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_list_runs_empty(client):
    with patch("sts2.database.get_pool", return_value=make_pool([])):
        resp = client.get("/api/v1/runs")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_runs_cards_filter_uses_containment(client):
    pool = make_pool([(1, 10, True, "build_001")])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?cards=Bash&cards=Strike")

    assert resp.status_code == 200
    query, params = (
        pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    )
    assert "@>" in query
    assert params[0] == ["Bash", "Strike"]


def test_list_runs_no_cards_omits_where(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs")

    query, _ = (
        pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    )
    assert "WHERE" not in query


def test_list_runs_pagination(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?limit=5&offset=10")

    assert resp.status_code == 200
    assert resp.json()["limit"] == 5
    assert resp.json()["offset"] == 10
    _, params = (
        pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    )
    assert params[-2:] == [5, 10]
