import json
from pathlib import Path


def evidence_payload(save_id, season_id):
    return {
        "career_save_id": save_id,
        "season_id": season_id,
        "source_external_match_id": "screenshots-2024-08-17-sturm-0-13-salzburg",
        "played_at": "2024-08-17",
        "external_compobjid": 364,
        "competition_name": "Austrian Bundesliga",
        "club_team_external_id": 191,
        "opponent_name": "SK Sturm Graz",
        "club_was_home": False,
        "club_goals": 13,
        "opponent_goals": 0,
        "duration_minutes": 92.4,
        "team_stats": {
            "possession": 59,
            "xg": 9.6,
            "shots": 22,
            "shots_on_target": 16,
            "passes": 49,
            "completed_passes": 46,
            "pass_accuracy": 94,
            "tackles": 21,
            "tackles_won": 14,
            "saves": 0,
        },
        "opponent_stats": {
            "possession": 41,
            "xg": 0,
            "shots": 0,
            "shots_on_target": 0,
            "passes": 45,
            "completed_passes": 38,
            "pass_accuracy": 84,
            "tackles": 0,
            "tackles_won": 0,
            "saves": 3,
        },
        "timeline": [
            {"minute": 3, "kind": "goal", "team": "club", "player": "Roko Simic"},
            {"minute": 8, "kind": "goal", "team": "club", "player": "Karim Konate"},
        ],
        "player_performances": [
            {
                "external_player_id": 246762,
                "name": "Sekou Koita",
                "position": "ST",
                "overall": 75,
                "rating": 10,
                "goals": 4,
                "assists": 1,
                "substitute": True,
            }
        ],
        "screenshot_paths": ["preflight/test/screenshots/match.jpg"],
        "evidence_note": "Synthetic API regression based on the verified field shape.",
    }


def test_match_evidence_is_idempotent_and_filterable(client, career, save):
    season_id = client.get(f"/api/v1/careers/{career}/seasons").json()[0]["id"]
    payload = evidence_payload(save, season_id)
    first = client.post(f"/api/v1/careers/{career}/matches/evidence", json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["result"] == "W"
    assert first.json()["home_goals"] == 0
    assert first.json()["away_goals"] == 13
    assert first.json()["team_stats"]["xg"] == 9.6
    assert first.json()["screenshot_urls"][0].endswith("/screenshots/0")

    repeated = client.post(f"/api/v1/careers/{career}/matches/evidence", json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]

    rows = client.get(f"/api/v1/careers/{career}/matches?season_id={season_id}").json()
    assert len(rows) == 1
    assert rows[0]["opponent_name"] == "SK Sturm Graz"
    assert rows[0]["player_performances"][0]["goals"] == 4
    dashboard = client.get(f"/api/v1/careers/{career}/dashboard?season_id={season_id}").json()
    assert dashboard["team_matches"]["matches"] == 1
    assert dashboard["team_matches"]["wins"] == 1
    assert dashboard["team_matches"]["goals_for"] == 13
    assert dashboard["team_matches"]["avg_xg"] == 9.6


def test_match_evidence_rejects_unsafe_screenshot_path(client, career, save):
    season_id = client.get(f"/api/v1/careers/{career}/seasons").json()[0]["id"]
    payload = evidence_payload(save, season_id)
    payload["screenshot_paths"] = ["../outside.jpg"]
    response = client.post(f"/api/v1/careers/{career}/matches/evidence", json=payload)
    assert response.status_code == 422


def test_match_drafts_are_scoped_to_career_and_serve_copied_screenshots(client, app, career, save):
    data_dir = Path(app.state.factory.kw["bind"].url.database).parent
    screenshot = data_dir / "screenshots" / "drafts" / "draft-1" / "frame.jpg"
    screenshot.parent.mkdir(parents=True)
    screenshot.write_bytes(b"jpeg-test")
    draft_file = data_dir / "screenshot_drafts" / "draft-1" / "draft.json"
    draft_file.parent.mkdir(parents=True)
    draft_file.write_text(
        json.dumps(
            {
                "draft_version": 1,
                "id": "draft-1",
                "status": "NEEDS_REVIEW",
                "match": {
                    "career_save_id": save,
                    "screenshot_paths": ["screenshots/drafts/draft-1/frame.jpg"],
                },
            }
        ),
        encoding="utf-8",
    )

    response = client.get(f"/api/v1/careers/{career}/match-drafts")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "draft-1"
    image_url = response.json()[0]["screenshot_urls"][0]
    image = client.get(image_url)
    assert image.status_code == 200
    assert image.content == b"jpeg-test"
