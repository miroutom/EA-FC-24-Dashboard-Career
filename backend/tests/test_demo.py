import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import Settings
from app.main import create_app
from app.models import Career, CareerSave, HistoricalStat, Snapshot


@pytest.fixture
def demo_app(tmp_path):
    return create_app(
        Settings(data_dir=tmp_path / "demo", demo_mode=True, watcher_enabled=False, http_port=8001)
    )


def test_demo_is_labelled_populated_and_never_game_verified(demo_app):
    with TestClient(demo_app) as client:
        assert client.get("/api/v1/health").json()["demo_mode"] is True
        careers = client.get("/api/v1/careers").json()
        assert len(careers) == 2
        d = client.get(f"/api/v1/careers/{careers[0]['id']}/dashboard").json()
        assert d["players_count"] == 22 and d["seasons_count"] == 8
        assert d["kpis"]["goals"] > 0
        assert d["data_quality"] == ["demo"]
        assert all(p["sources"] == ["demo"] for p in d["items"])
        sync = client.get(f"/api/v1/careers/{careers[0]['id']}/sync/status").json()
        assert sync["collector"] == "demo simulator (synthetic)"
        assert sync["capabilities"]["auto_capture"] == "SIMULATED"
    with demo_app.state.factory() as db:
        assert not any(s.verified_live for s in db.scalars(select(CareerSave)))


def test_demo_restart_is_idempotent_and_preserves_real_database(tmp_path):
    real_dir, demo_dir = tmp_path / "real", tmp_path / "demo"
    real = create_app(Settings(data_dir=real_dir, watcher_enabled=False))
    with TestClient(real) as client:
        client.post("/api/v1/careers", json={"name": "My actual career"})
    original = (real_dir / "analytics.sqlite3").read_bytes()
    for _ in range(2):
        demo = create_app(Settings(data_dir=demo_dir, demo_mode=True, watcher_enabled=False))
        with demo.state.factory() as db:
            assert db.scalar(select(func.count()).select_from(Snapshot)) == 3
        demo.state.factory.kw["bind"].dispose()
    assert (real_dir / "analytics.sqlite3").read_bytes() == original


def test_cannot_use_existing_real_database_for_demo(app):
    with pytest.raises(ValueError, match="not a demo sandbox"):
        create_app(Settings(data_dir=app.state.ingestor.settings.data_dir, demo_mode=True))


def test_demo_advance_uses_watcher_and_increases_cumulative_totals(demo_app):
    with TestClient(demo_app) as client:
        cid = client.get("/api/v1/careers").json()[0]["id"]
        before = client.get(f"/api/v1/careers/{cid}/dashboard").json()["kpis"]["goals"]
        response = client.post("/api/v1/demo/advance", json={}, headers={"Origin": "http://127.0.0.1:8001"})
        assert response.status_code == 200 and response.json()["status"] == "QUEUED"
        demo_app.state.watcher.scan()
        demo_app.state.watcher.scan()
        after = client.get(f"/api/v1/careers/{cid}/dashboard").json()["kpis"]["goals"]
        assert after > before
        assert len(client.get(f"/api/v1/careers/{cid}/snapshots").json()) == 4


def test_normal_app_never_seeds_demo_and_rejects_synthetic_producer(app, client):
    assert client.get("/api/v1/health").json()["demo_mode"] is False
    assert client.get("/api/v1/careers").json() == []
    assert client.post("/api/v1/demo/advance", json={}).status_code in (404, 405)
    from conftest import snapshot

    document = snapshot(producer="lca-demo-simulator")
    assert app.state.ingestor.ingest_bytes(json.dumps(document).encode())["status"] == "QUARANTINE"


def test_demo_careers_have_separate_player_identities(demo_app):
    with TestClient(demo_app) as client:
        careers = client.get("/api/v1/careers").json()
        first = client.get(f"/api/v1/careers/{careers[0]['id']}/players").json()["items"]
        second = client.get(f"/api/v1/careers/{careers[1]['id']}/players").json()["items"]
        assert not ({p["id"] for p in first} & {p["id"] for p in second})


def test_extended_demo_history_is_added_once(demo_app):
    from app.demo_data import seed_demo

    with demo_app.state.factory() as db:
        cid = db.scalar(select(Career.id).where(Career.name == "ДЕМО · Leicester City"))
        before = db.scalar(
            select(func.count()).select_from(HistoricalStat).where(HistoricalStat.career_id == cid)
        )
    assert before == 22 * 7  # Seven historical seasons plus one cumulative snapshot season.
    seed_demo(demo_app.state.factory)
    with demo_app.state.factory() as db:
        after = db.scalar(
            select(func.count()).select_from(HistoricalStat).where(HistoricalStat.career_id == cid)
        )
    assert after == before
