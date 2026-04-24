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


def run_row(  # noqa: PLR0913
    run_id=1,
    ascension=10,
    win=True,  # noqa: FBT002
    build_id="build_001",
    player_count=1,
    total=1,
    wins=1,
    character="CHARACTER.IRONCLAD",
):
    return (run_id, ascension, win, build_id, player_count, total, wins, character)


@pytest.fixture(scope="module")
def client():
    with (
        patch("sts2.database.open_pool", new_callable=AsyncMock),
        patch("sts2.database.init_db", new_callable=AsyncMock),
        TestClient(app) as c,
    ):
        yield c


def test_list_runs_returns_items(client):
    rows = [run_row(1, 10, win=True, build_id="build_001"), run_row(2, 5, win=False, build_id="build_002", wins=0)]
    with patch("sts2.database.get_pool", return_value=make_pool(rows)):
        resp = client.get("/api/v1/runs")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == [
        {
            "id": 1,
            "ascension": 10,
            "win": True,
            "build_id": "build_001",
            "player_count": 1,
            "character": "CHARACTER.IRONCLAD",
        },
        {
            "id": 2,
            "ascension": 5,
            "win": False,
            "build_id": "build_002",
            "player_count": 1,
            "character": "CHARACTER.IRONCLAD",
        },
    ]
    assert data["total"] == 1
    assert data["wins"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_list_runs_empty(client):
    with patch("sts2.database.get_pool", return_value=make_pool([])):
        resp = client.get("/api/v1/runs")

    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["wins"] == 0


def test_list_runs_cards_filter_uses_containment(client):
    pool = make_pool([run_row()])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?cards=Bash&cards=Strike")

    assert resp.status_code == 200
    query, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "@>" in query
    assert params[0] == ["Bash", "Strike"]


def test_list_runs_no_cards_omits_where(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?mode=both")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "WHERE" not in query


def test_list_runs_pagination(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?limit=5&offset=10")

    assert resp.status_code == 200
    assert resp.json()["limit"] == 5
    assert resp.json()["offset"] == 10
    _, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert params[-2:] == [5, 10]


def test_list_runs_character_filter(client):
    pool = make_pool([run_row(character="CHARACTER.NECROBINDER")])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?character=CHARACTER.NECROBINDER")

    assert resp.status_code == 200
    assert resp.json()["items"][0]["character"] == "CHARACTER.NECROBINDER"
    query, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "players'->0->>'character'" in query
    assert "CHARACTER.NECROBINDER" in params


def test_list_runs_result_win_filter(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?result=win")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "r.win = true" in query


def test_list_runs_result_loss_filter(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?result=loss")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "r.win = false" in query


def test_list_runs_result_both_no_win_filter(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?result=both")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "r.win =" not in query


def test_list_runs_mode_single_filter(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?mode=single")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "jsonb_array_length" in query
    assert "= 1" in query


def test_list_runs_mode_multi_filter(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/runs?mode=multi")

    query, _ = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "jsonb_array_length" in query
    assert "> 1" in query


def test_list_runs_ascension_filter(client):
    pool = make_pool([run_row(ascension=5)])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/runs?ascension=5")

    assert resp.status_code == 200
    query, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "r.ascension = %s" in query
    assert 5 in params


def test_list_runs_invalid_result_rejected(client):
    resp = client.get("/api/v1/runs?result=draw")
    assert resp.status_code == 422


def test_list_runs_ascension_out_of_range_rejected(client):
    resp = client.get("/api/v1/runs?ascension=11")
    assert resp.status_code == 422


def test_top_cards_returns_items(client):
    rows = [("CARD.BASH", 10, 7), ("CARD.STRIKE_IRONCLAD", 8, 3)]
    with patch("sts2.database.get_pool", return_value=make_pool(rows)):
        resp = client.get("/api/v1/top-cards")

    assert resp.status_code == 200
    data = resp.json()
    assert data == [
        {"card_id": "CARD.BASH", "picks": 10, "wins": 7},
        {"card_id": "CARD.STRIKE_IRONCLAD", "picks": 8, "wins": 3},
    ]


def test_top_cards_character_filter(client):
    pool = make_pool([("CARD.BASH", 5, 3)])
    with patch("sts2.database.get_pool", return_value=pool):
        resp = client.get("/api/v1/top-cards?character=CHARACTER.IRONCLAD")

    assert resp.status_code == 200
    query, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert "players'->0->>'character'" in query
    assert "CHARACTER.IRONCLAD" in params


def test_top_cards_empty(client):
    with patch("sts2.database.get_pool", return_value=make_pool([])):
        resp = client.get("/api/v1/top-cards")

    assert resp.status_code == 200
    assert resp.json() == []


def test_top_cards_limit(client):
    pool = make_pool([])
    with patch("sts2.database.get_pool", return_value=pool):
        client.get("/api/v1/top-cards?limit=5")

    _, params = pool.connection.return_value.__aenter__.return_value.execute.call_args.args
    assert params[-1] == 5
