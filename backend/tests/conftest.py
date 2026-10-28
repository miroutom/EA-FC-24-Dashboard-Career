import pytest
from fastapi.testclient import TestClient

from app.core import Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(Settings(data_dir=tmp_path, watcher_enabled=False))


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def career(client):
    return client.post("/api/v1/careers", json={"name": "Test career", "start_year": 2027}).json()["id"]


@pytest.fixture
def save(client, career):
    response = client.post(
        f"/api/v1/careers/{career}/saves/bind",
        json={
            "instance_key": "test-save-0001",
            "verified_live": True,
            "evidence": "SYNTHETIC TEST ONLY, not real game verification",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def snapshot(apps=10, goals=4, assists=3, day=1, year=2027, **changes):
    """Synthetic fixtures ONLY. Never seeded by production startup."""
    doc = {
        "schema_version": 1,
        "producer": "fc24-live-editor-lua",
        "collector_version": "test",
        "game_version": "EA FC 24",
        "captured_at_utc": f"2026-10-{day:02}T12:00:00Z",
        "event": "test_fixture",
        "save_uid": None,
        "instance_key": "test-save-0001",
        "in_game_date": None,
        "user_team_id": 95,
        "season_start_year": year,
        "completeness": "COMPLETE",
        "rows": [
            {
                "playerid": 12345,
                "teamid": 95,
                "compobjid": 1,
                "app": apps,
                "goals": goals,
                "assists": assists,
                "yellow": 0,
                "red": 0,
                "clean_sheets": 1,
                "avg": 72,
                "display_name": "Synthetic Player",
            }
        ],
    }
    doc.update(changes)
    return doc
