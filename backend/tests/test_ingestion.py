import json

import pytest
from conftest import snapshot
from sqlalchemy import func, select

from app.models import InferredDelta, QueueItem, Snapshot


def ingest(app, doc):
    return app.state.ingestor.ingest_bytes(json.dumps(doc).encode())


def dashboard(client, career, query=""):
    response = client.get(f"/api/v1/careers/{career}/dashboard{query}")
    assert response.status_code == 200, response.text
    return response.json()


def test_same_snapshot_three_times(app, client, career, save):
    for _ in range(3):
        ingest(app, snapshot())
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 1
        assert db.scalar(select(func.count()).select_from(InferredDelta)) == 0
    assert dashboard(client, career)["kpis"]["goals"] == 4


def test_cumulative_not_sum_and_delta_two_goals(app, client, career, save):
    ingest(app, snapshot())
    ingest(app, snapshot(apps=11, goals=6, day=2))
    assert dashboard(client, career)["kpis"]["goals"] == 6
    delta = client.get(f"/api/v1/careers/{career}/changes").json()[0]
    assert delta["values"]["goals"] == 2
    assert delta["interval_label"] == "Между снимками"
    assert delta["confidence"] == "INTERVAL"


def test_multiple_appearances_are_interval_not_match(app, client, career, save):
    ingest(app, snapshot())
    ingest(app, snapshot(apps=12, goals=6, day=2))
    delta = client.get(f"/api/v1/careers/{career}/changes").json()[0]
    assert delta["values"]["appearances"] == 2
    assert delta["confidence"] == "AMBIGUOUS"
    assert "матч" not in delta["interval_label"].lower()


def test_rollback_preserved_until_explicit_branch_choice(app, client, career, save):
    ingest(app, snapshot(goals=8))
    assert ingest(app, snapshot(goals=3, day=2))["status"] == "CONFLICT"
    assert dashboard(client, career)["kpis"]["goals"] == 8
    assert client.get(f"/api/v1/careers/{career}/changes").json() == []
    assert (
        client.post(f"/api/v1/careers/{career}/saves/{save}/resolve", json={"strategy": "adopt"}).status_code
        == 200
    )
    assert dashboard(client, career)["kpis"]["goals"] == 3
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 2


def test_reject_and_hold_conflicting_branch(app, client, career, save):
    ingest(app, snapshot(goals=8))
    ingest(app, snapshot(goals=3, day=2))
    assert ingest(app, snapshot(goals=4, day=3))["status"] == "HELD"
    client.post(f"/api/v1/careers/{career}/saves/{save}/resolve", json={"strategy": "reject"})
    assert dashboard(client, career)["kpis"]["goals"] == 8


def test_season_rollover_keeps_both_seasons(app, client, career, save):
    ingest(app, snapshot(goals=8))
    assert ingest(app, snapshot(goals=1, apps=1, assists=0, year=2028, day=2))["status"] == "IMPORTED"
    d = dashboard(client, career)
    assert d["kpis"]["goals"] == 9
    assert [r["goals"] for r in d["chart"]] == [8, 1]
    assert client.get(f"/api/v1/careers/{career}/changes").json() == []


def test_null_is_not_zero_and_avg_unavailable(app, client, career, save):
    doc = snapshot()
    del doc["rows"][0]["goals"]
    del doc["rows"][0]["clean_sheets"]
    ingest(app, doc)
    player = dashboard(client, career)["items"][0]
    assert player["goals"] is None
    assert player["goal_contributions"] is None
    assert player["clean_sheets"] is None
    assert player["rating"] is None


def test_invalid_json_quarantine_no_partial_database(app, client, career, save):
    assert app.state.ingestor.ingest_bytes(b"{broken")["status"] == "QUARANTINE"
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 0
    assert list((app.state.ingestor.settings.data_dir / "quarantine").glob("*.json"))


def test_atomic_failure_and_successful_retry(app, client, career, save, monkeypatch):
    import app.ingestion as module

    original = module.live_player

    def crash(*args):
        raise RuntimeError("test interrupted import")

    monkeypatch.setattr(module, "live_player", crash)
    with pytest.raises(RuntimeError):
        ingest(app, snapshot())
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 0
        assert db.scalar(select(func.count()).select_from(QueueItem)) == 0
    monkeypatch.setattr(module, "live_player", original)
    assert ingest(app, snapshot())["status"] == "IMPORTED"


def test_only_date_changed_no_match_or_delta(app, client, career, save):
    ingest(app, snapshot())
    assert ingest(app, snapshot(day=2))["status"] == "NO_CHANGE"
    assert client.get(f"/api/v1/careers/{career}/changes").json() == []
    assert dashboard(client, career)["kpis"]["goals"] == 4


def test_unknown_context_requires_binding(app, client, career):
    assert ingest(app, snapshot())["status"] == "NEEDS_BINDING"
    with app.state.factory() as db:
        assert db.scalar(select(func.count()).select_from(Snapshot)) == 0


def test_unbound_delivery_can_be_retried_after_explicit_binding(app, client, career):
    ingest(app, snapshot())
    client.post(f"/api/v1/careers/{career}/saves/bind", json={"instance_key": "test-save-0001"})
    result = client.post(f"/api/v1/careers/{career}/sync/retry").json()
    assert result["results"][0]["status"] == "IMPORTED"
    assert len(client.get(f"/api/v1/careers/{career}/snapshots").json()) == 1


def test_incomplete_competitions_not_claimed_as_total(app, client, career, save):
    ingest(app, snapshot(completeness="UNKNOWN"))
    assert dashboard(client, career)["kpis"]["goals"] is None
    comp = client.get(f"/api/v1/careers/{career}/competitions").json()[0]["id"]
    assert dashboard(client, career, f"?competition_id={comp}")["kpis"]["goals"] == 4


def test_missing_player_preserved_and_detected_on_return(app, client, career, save):
    ingest(app, snapshot(goals=8))
    ingest(app, snapshot(day=2, rows=[]))
    assert dashboard(client, career)["kpis"]["goals"] == 8
    assert ingest(app, snapshot(goals=3, day=3))["status"] == "CONFLICT"


def test_as_of_uses_latest_cumulative(app, client, career, save):
    ingest(app, snapshot(goals=4))
    ingest(app, snapshot(goals=6, apps=11, day=2))
    assert dashboard(client, career, "?as_of=2026-10-01T13:00:00Z")["kpis"]["goals"] == 4


def test_inconsistent_growth_marked_invalid(app, client, career, save):
    ingest(app, snapshot())
    ingest(app, snapshot(goals=6, day=2))
    assert client.get(f"/api/v1/careers/{career}/changes").json()[0]["confidence"] == "INVALID"


def test_watcher_stable_file_and_restart_duplicate(app, client, career, save):
    spool = app.state.ingestor.settings.data_dir / "spool"
    path = spool / "capture.json"
    path.write_text("{")
    app.state.watcher.scan()
    path.write_text(json.dumps(snapshot()))
    app.state.watcher.scan()
    assert client.get(f"/api/v1/careers/{career}/snapshots").json() == []
    app.state.watcher.scan()
    assert len(client.get(f"/api/v1/careers/{career}/snapshots").json()) == 1
    path.write_text(json.dumps(snapshot()))
    from app.ingestion import Watcher

    restarted = Watcher(app.state.ingestor)
    restarted.scan()
    restarted.scan()
    assert len(client.get(f"/api/v1/careers/{career}/snapshots").json()) == 1


@pytest.mark.parametrize(
    "change", [dict(season_start_year=None), dict(user_team_id=None), dict(instance_key="another-save")]
)
def test_missing_context_never_guessed(app, client, career, save, change):
    assert ingest(app, snapshot(**change))["status"] == "NEEDS_BINDING"


@pytest.mark.parametrize("field,value", [("goals", -1), ("app", True), ("goals", "4")])
def test_strict_counter_validation(app, client, career, save, field, value):
    doc = snapshot()
    doc["rows"][0][field] = value
    assert ingest(app, doc)["status"] == "QUARANTINE"
