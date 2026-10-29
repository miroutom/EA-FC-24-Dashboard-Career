from app.screenshot_capture import (
    classify,
    match_roster,
    number,
    parse_scoreboard,
    parse_summary,
    value_at,
    words,
)


def ocr(*entries, text=""):
    return {
        "text": text,
        "lines": [
            {
                "text": " ".join(item[0] for item in entries),
                "words": [
                    {"text": value, "x": x, "y": y, "width": width, "height": 14}
                    for value, x, y, width in entries
                ],
            }
        ],
    }


def test_ocr_number_repairs_common_fc_ui_glyphs():
    assert number("о") == 0
    assert number("9,6") == 9.6
    assert number("920/0") == 92
    assert number("330/0") == 33


def test_value_at_removes_graphical_bar_merged_as_one():
    result = ocr(("61", 825, 303, 19), ("21", 820, 338, 14), ("|", 839, 333, 5))
    items = words(result)
    assert value_at(items, 303, 790, 845) == 6
    assert value_at(items, 338, 790, 845) == 21


def test_classifies_summary_and_player_screens():
    assert classify(ocr(text="Владение мячом % Ожидаемые голы")) == "summary"
    assert classify(ocr(text="Эффективность игрока")) == "player"


def test_scoreboard_detects_away_club_and_score():
    result = ocr(
        ("SKSTURMGRAZ", 388, 43, 120),
        ("0", 595, 37, 10),
        ("13", 661, 37, 18),
        ("SALZBURG", 796, 43, 85),
        ("92:24", 619, 79, 45),
    )
    parsed = parse_scoreboard(result, "RB Salzburg")
    assert parsed["club_was_home"] is False
    assert parsed["club_goals"] == 13
    assert parsed["opponent_goals"] == 0
    assert parsed["duration_minutes"] == 92.24


def test_summary_uses_screen_coordinates_for_both_teams():
    result = ocr(
        ("41", 445, 175, 15),
        ("59", 817, 175, 15),
        ("0,0", 445, 273, 24),
        ("9,6", 812, 273, 22),
        ("330/0", 214, 207, 40),
        ("920/0", 1020, 207, 42),
    )
    opponent, club = parse_summary(result)
    assert opponent["possession"] == 41
    assert club["possession"] == 59
    assert opponent["xg"] == 0
    assert club["xg"] == 9.6
    assert opponent["dribble_success"] == 33
    assert club["dribble_success"] == 92


def test_roster_matching_tolerates_fc_font_ocr_errors():
    roster = [{"name": "Roko Šimić"}, {"name": "Luka Sučić"}]
    assert match_roster("Boko Simié", roster)[0]["name"] == "Roko Šimić"
    assert match_roster("ЦИКа SuEi6 Suiié", roster)[0]["name"] == "Luka Sučić"
