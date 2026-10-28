import pytest
from conftest import snapshot
from test_import_api import commit, csv, preview
from test_ingestion import dashboard, ingest


def test_observed_goal_share_and_live_competition_breakdown(app, client, career, save):
    commit(client, career, preview(client, career, csv(8, name="Player A")))
    commit(client, career, preview(client, career, csv(2, name="Player B")))
    data = dashboard(client, career)
    assert data["items"][0]["observed_goals_share"] == pytest.approx(0.8)
    ingest(app, snapshot())
    live_comp = client.get(f"/api/v1/careers/{career}/competitions").json()[0]["id"]
    pid = dashboard(client, career, f"?competition_id={live_comp}")["items"][0]["id"]
    detail = client.get(f"/api/v1/careers/{career}/players/{pid}?competition_id={live_comp}").json()
    assert detail["competition_history"][0]["goals"] == 4
    assert detail["competition_history"][0]["competition"] == "Турнир #1"
