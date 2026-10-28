import io
from pathlib import Path

import openpyxl
from conftest import snapshot
from test_ingestion import dashboard, ingest

ROOT = Path(__file__).resolve().parents[2]


def csv(goals=8, name="Hložek", year="2027/28"):
    return f"Сезон,Игрок,Позиция,Матчи,Голы,Ассисты,Сухие матчи,Г+П\n{year},{name},ФРВ,10,{goals},3,,999\n".encode()


def preview(client, career, data, filename="test.csv"):
    response = client.post(f"/api/v1/careers/{career}/imports/preview", files={"file": (filename, data)})
    assert response.status_code == 200, response.text
    return response.json()


def commit(client, career, p, strategy="reject"):
    return client.post(
        f"/api/v1/careers/{career}/imports/commit",
        json={"preview_token": p["preview_token"], "strategy": strategy},
    )


def test_unicode_preview_commit_idempotency_and_derived_ga(client, career):
    p = preview(client, career, csv())
    assert dashboard(client, career)["players_count"] == 0
    assert commit(client, career, p).status_code == 200
    assert commit(client, career, p).json()["duplicate"] is True
    player = dashboard(client, career)["items"][0]
    assert player["name"] == "Hložek"
    assert player["goal_contributions"] == 11
    assert player["clean_sheets"] is None
    assert client.get(f"/api/v1/careers/{career}/players?search=Hlož").json()["total"] == 1


def test_conflict_requires_explicit_replace(client, career):
    commit(client, career, preview(client, career, csv(8)))
    p = preview(client, career, csv(9))
    assert p["conflicts"][0]["existing"]["goals"] == 8
    assert commit(client, career, p).status_code == 409
    assert dashboard(client, career)["kpis"]["goals"] == 8
    assert commit(client, career, p, "replace").status_code == 200
    assert dashboard(client, career)["kpis"]["goals"] == 9


def test_real_workbook_only_all_seasons_and_totals_match(client, career):
    content = (ROOT / "leicester_rebuilt_with_career_totals.xlsx").read_bytes()
    p = preview(client, career, content, "history.xlsx")
    assert p["rows_count"] == 123
    assert not p["errors"]
    assert commit(client, career, p).status_code == 200
    workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = list(workbook["Все сезоны"].values)[1:]
    d = dashboard(client, career)
    assert d["kpis"]["goals"] == sum(row[4] for row in rows)
    assert d["kpis"]["assists"] == sum(row[5] for row in rows)
    assert d["kpis"]["appearances"] == sum(row[3] for row in rows)
    assert d["seasons_count"] == 5
    assert sum(r["goals"] for r in d["chart"]) == d["kpis"]["goals"]
    for player in d["items"]:
        assert sum(r["goals"] for r in player["history"]) == player["goals"]
    assert (
        commit(client, career, preview(client, career, content, "renamed.xlsx")).json()["duplicate"] is True
    )


def test_two_careers_never_mix_players_previews_saves_or_notes(app, client, career, save):
    other = client.post("/api/v1/careers", json={"name": "Second"}).json()["id"]
    p = preview(client, career, csv())
    assert commit(client, other, p).status_code == 404
    commit(client, career, p)
    commit(client, other, preview(client, other, csv()))
    first = dashboard(client, career)["items"][0]["id"]
    second = dashboard(client, other)["items"][0]["id"]
    assert first != second
    assert client.get(f"/api/v1/careers/{other}/players/{first}").status_code == 404
    assert client.get(f"/api/v1/careers/{other}/snapshots?save_id={save}").status_code == 404
    assert client.get(f"/api/v1/careers/{other}/dashboard?save_id={save}").status_code == 404
    ingest(app, snapshot())
    ingest(app, snapshot(apps=11, goals=6, day=2))
    delta_id = client.get(f"/api/v1/careers/{career}/changes").json()[0]["id"]
    assert (
        client.post(
            f"/api/v1/careers/{other}/notes", json={"text": "Wrong career", "interval_id": delta_id}
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/careers/{other}/sync/events").json() == []


def test_historical_total_and_live_overlap_no_double_count(app, client, career, save):
    commit(client, career, preview(client, career, csv(8)))
    ingest(app, snapshot(goals=4))
    assert dashboard(client, career)["kpis"]["goals"] == 8
    comp = client.get(f"/api/v1/careers/{career}/competitions").json()[0]["id"]
    assert dashboard(client, career, f"?competition_id={comp}")["kpis"]["goals"] == 4


def test_explicit_identity_and_source_reconciliation(app, client, career, save):
    commit(client, career, preview(client, career, csv(8)))
    ingest(app, snapshot(goals=4))
    pid = dashboard(client, career)["items"][0]["id"]
    response = client.post(
        f"/api/v1/careers/{career}/players/{pid}/identity",
        json={"external_player_id": 12345, "confirmed": True},
    )
    assert response.status_code == 200, response.text
    sid = client.get(f"/api/v1/careers/{career}/seasons").json()[0]["id"]
    client.post(
        f"/api/v1/careers/{career}/seasons/{sid}/policy", json={"source_policy": "live", "acknowledged": True}
    )
    player = dashboard(client, career)["items"][0]
    assert player["id"] == pid and player["name"] == "Hložek" and player["goals"] == 4


def test_validation_failure_does_not_create_preview_or_stats(client, career):
    p = preview(client, career, csv(-1))
    assert p["errors"] and p["preview_token"] is None
    assert dashboard(client, career)["players_count"] == 0


def test_unknown_game_fields_are_rejected(client, career):
    assert client.post(f"/api/v1/careers/{career}/notes", json={"text": "note", "xg": 3}).status_code == 422
    assert client.get(f"/api/v1/careers/{career}/players?sort=arbitrary_sql").status_code == 422


def test_local_origin_protection(client, career):
    assert (
        client.post(
            "/api/v1/careers", json={"name": "evil"}, headers={"Origin": "https://external.invalid"}
        ).status_code
        == 403
    )


def test_zero_appearances_counts_season_without_ratio(client, career):
    data = csv().decode().replace("10,8,3", "0,0,0").encode()
    commit(client, career, preview(client, career, data))
    player = dashboard(client, career)["items"][0]
    assert player["seasons_count"] == 1 and player["goals_per_appearance"] is None


def test_position_conflict_and_stale_preview_require_review(client, career):
    commit(client, career, preview(client, career, csv()))
    changed = csv().decode().replace("ФРВ", "ЦП").encode()
    p = preview(client, career, changed)
    assert p["conflicts"][0]["existing"]["position"] == "ФРВ"
    assert commit(client, career, p).status_code == 409
    another = preview(client, career, csv(9))
    commit(client, career, another, "replace")
    assert commit(client, career, p, "replace").json()["error"]["code"] == "PREVIEW_STALE"


def test_foreign_season_competition_and_compare_rejected(app, client, career, save):
    ingest(app, snapshot())
    other = client.post("/api/v1/careers", json={"name": "Other"}).json()["id"]
    foreign_season = client.get(f"/api/v1/careers/{other}/seasons").json()[0]["id"]
    assert client.get(f"/api/v1/careers/{career}/dashboard?season_id={foreign_season}").status_code == 404
    comp = client.get(f"/api/v1/careers/{career}/competitions").json()[0]["id"]
    assert client.get(f"/api/v1/careers/{other}/dashboard?competition_id={comp}").status_code == 404
    pid = dashboard(client, career)["items"][0]["id"]
    assert client.get(f"/api/v1/careers/{other}/compare?player_ids={pid},999").status_code == 404


def test_players_pagination_and_name_sort(client, career):
    for name in ["Alpha", "Bravo"]:
        commit(client, career, preview(client, career, csv(name=name)))
    response = client.get(f"/api/v1/careers/{career}/players?sort=name&descending=true&size=1&page=1").json()
    assert response["items"][0]["name"] == "Bravo" and response["total"] == 2
