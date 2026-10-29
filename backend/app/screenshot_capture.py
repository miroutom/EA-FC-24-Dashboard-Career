"""Safe, read-only FC 24 post-match screenshot recognition.

The module deliberately has no connection to FC 24 or Live Editor.  It only
opens image files which already exist on disk and produces a reviewable draft.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select

from .models import Player, PlayerSeasonMetadata

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
TEAM_STATS = (
    "possession",
    "xg",
    "shots",
    "shots_on_target",
    "shots_off_target",
    "blocked_shots",
    "shot_accuracy",
    "passes",
    "completed_passes",
    "pass_accuracy",
    "tackles",
    "tackles_won",
    "interceptions",
    "saves",
    "fouls",
    "offsides",
    "dribbles",
    "successful_dribbles",
    "dribble_success",
    "ball_recovery_seconds",
    "penalties",
    "yellow_cards",
    "red_cards",
    "injuries",
)


@dataclass(frozen=True)
class Word:
    text: str
    x: float
    y: float
    width: float
    height: float


class WindowsOcr:
    """Bridge to the built-in Windows.Media.Ocr engine."""

    def __init__(self, script: Path):
        self.script = script.resolve()

    def recognize(
        self,
        image: Path,
        language: str = "ru",
        crop: tuple[int, int, int, int] | None = None,
        scale: int = 1,
    ) -> dict[str, Any]:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.script),
            "-ImagePath",
            str(image.resolve()),
            "-Language",
            language,
            "-Scale",
            str(scale),
        ]
        if crop:
            x, y, width, height = crop
            command += [
                "-CropX",
                str(x),
                "-CropY",
                str(y),
                "-CropWidth",
                str(width),
                "-CropHeight",
                str(height),
            ]
        result = subprocess.run(command, check=True, capture_output=True)
        for encoding in ("utf-8-sig", "utf-16", "cp1251"):
            try:
                return json.loads(result.stdout.decode(encoding))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        raise ValueError("Windows OCR returned unreadable JSON")


def words(result: dict[str, Any]) -> list[Word]:
    return [
        Word(
            text=item["text"],
            x=float(item["x"]),
            y=float(item["y"]),
            width=float(item["width"]),
            height=float(item["height"]),
        )
        for line in result.get("lines", [])
        for item in line.get("words", [])
    ]


def compact(value: str) -> str:
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return "".join(character.lower() for character in value if character.isalnum())


def number(value: str) -> float | None:
    cleaned = value.strip().replace(" ", "").replace("%", "")
    cleaned = cleaned.translate(str.maketrans({"о": "0", "О": "0", "з": "3", "З": "3"}))
    if cleaned.endswith("0/0"):
        cleaned = cleaned[:-3] or "0"
    cleaned = cleaned.rstrip("|Iil")
    match = re.fullmatch(r"-?\d+(?:[,.]\d+)?", cleaned)
    if not match:
        return None
    return float(cleaned.replace(",", "."))


def value_at(
    items: Iterable[Word], y: float, x_min: float, x_max: float, tolerance: float = 9
) -> float | None:
    all_items = list(items)
    candidates = []
    for item in all_items:
        parsed = number(item.text)
        if parsed is not None and x_min <= item.x <= x_max and abs(item.y - y) <= tolerance:
            # FC UI separators are occasionally recognized as a trailing 1.
            if parsed >= 100 and parsed.is_integer() and str(int(parsed)).endswith("1"):
                parsed = float(str(int(parsed))[:-1])
            elif (
                parsed >= 10
                and parsed.is_integer()
                and str(int(parsed)).endswith("1")
                and item.x + item.width >= 839
                and not any(
                    other.text == "|"
                    and 0 <= other.x - (item.x + item.width) <= 8
                    and abs(other.y - item.y) <= 8
                    for other in all_items
                )
            ):
                parsed = float(str(int(parsed))[:-1])
            candidates.append((abs(item.y - y), abs(item.x - ((x_min + x_max) / 2)), parsed))
    return min(candidates)[2] if candidates else None


def classify(result: dict[str, Any]) -> str:
    text = compact(result.get("text", ""))
    if "эффективностьигрока" in text:
        return "player"
    if "ожидаемыеголы" in text and "владениемячом" in text:
        return "summary"
    if "ударыобщее" in text:
        return "shots"
    if "передачиобщее" in text:
        return "passing"
    if "защитаобщее" in text:
        return "defending"
    if "общеевладение" in text:
        return "possession"
    if "события" in text:
        return "events"
    return "unknown"


def empty_stats() -> dict[str, float | int | None]:
    return {name: None for name in TEAM_STATS}


def parse_scoreboard(result: dict[str, Any], club_name: str) -> dict[str, Any]:
    items = words(result)
    time_word = next((item.text for item in items if re.fullmatch(r"\d{1,3}:\d{2}", item.text)), None)
    numeric = [
        item for item in items if 500 <= item.x <= 720 and item.y < 70 and number(item.text) is not None
    ]
    numeric.sort(key=lambda item: item.x)
    left_goals = int(number(numeric[0].text)) if numeric else None
    right_goals = int(number(numeric[-1].text)) if len(numeric) >= 2 else None
    left = " ".join(item.text for item in items if item.x < 560 and item.y < 70 and number(item.text) is None)
    right = " ".join(
        item.text for item in items if item.x > 730 and item.y < 70 and number(item.text) is None
    )
    club_key = compact(club_name)
    club_was_home = (
        SequenceMatcher(None, compact(left), club_key).ratio()
        > SequenceMatcher(None, compact(right), club_key).ratio()
    )
    minute = None
    if time_word:
        match = re.fullmatch(r"(\d+):(\d+)", time_word)
        minute = round(int(match.group(1)) + int(match.group(2)) / 100, 2) if match else None
    return {
        "left_name_ocr": left or None,
        "right_name_ocr": right or None,
        "left_goals": left_goals,
        "right_goals": right_goals,
        "club_was_home": club_was_home,
        "club_goals": left_goals if club_was_home else right_goals,
        "opponent_goals": right_goals if club_was_home else left_goals,
        "opponent_name_ocr": right if club_was_home else left,
        "duration_minutes": minute,
    }


def parse_summary(result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    items = words(result)
    opponent, club = empty_stats(), empty_stats()
    rows = {
        "possession": 175,
        "ball_recovery_seconds": 208,
        "shots": 240,
        "xg": 273,
        "passes": 306,
        "tackles": 338,
        "tackles_won": 371,
        "interceptions": 404,
        "saves": 436,
        "fouls": 469,
        "offsides": 501,
        "penalties": 600,
        "yellow_cards": 632,
    }
    for field, y in rows.items():
        opponent[field] = value_at(items, y, 420, 485)
        club[field] = value_at(items, y, 790, 845)
    opponent["dribble_success"] = value_at(items, 207, 120, 350, 22)
    club["dribble_success"] = value_at(items, 207, 940, 1165, 22)
    opponent["shot_accuracy"] = value_at(items, 381, 120, 350, 25)
    club["shot_accuracy"] = value_at(items, 381, 940, 1165, 25)
    opponent["pass_accuracy"] = value_at(items, 554, 120, 350, 25)
    club["pass_accuracy"] = value_at(items, 554, 940, 1165, 25)
    return opponent, club


def supplement_stats(
    kind: str, result: dict[str, Any], opponent: dict[str, Any], club: dict[str, Any]
) -> None:
    items = words(result)
    if kind == "shots":
        rows = {
            "shots": 194,
            "shots_on_target": 219,
            "shots_off_target": 245,
            "blocked_shots": 270,
        }
    elif kind == "passing":
        rows = {"passes": 194, "completed_passes": 219, "offsides": 270}
    elif kind == "defending":
        rows = {
            "tackles": 196,
            "tackles_won": 223,
            "interceptions": 303,
            "saves": 356,
            "fouls": 542,
            "penalties": 569,
            "yellow_cards": 596,
            "red_cards": 623,
        }
    else:
        return
    for field, y in rows.items():
        left = value_at(items, y, 420, 485)
        right = value_at(items, y, 790, 845)
        if left is not None and opponent[field] is None:
            opponent[field] = left
        if right is not None and club[field] is None:
            club[field] = right


def match_roster(header: str, roster: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    header_key = compact(header)
    visual_translation = str.maketrans(
        {"а": "a", "в": "b", "е": "e", "и": "u", "к": "k", "о": "o", "р": "p", "с": "c", "у": "y", "ц": "l"}
    )
    header_tokens = [compact(token) for token in re.findall(r"\w+", header)]
    header_tokens += [token.translate(visual_translation) for token in header_tokens]
    best, best_score = None, 0.0
    for player in roster:
        full = compact(player["name"])
        first_name = compact(player["name"].split()[0])
        surname = compact(player["name"].split()[-1])
        surname_score = max(
            (SequenceMatcher(None, token, surname).ratio() for token in header_tokens), default=0.0
        )
        first_name_score = max(
            (SequenceMatcher(None, token, first_name).ratio() for token in header_tokens), default=0.0
        )
        score = max(
            SequenceMatcher(None, header_key, full).ratio(),
            SequenceMatcher(None, header_key, surname).ratio(),
            surname_score,
            (first_name_score + surname_score) / 2,
            1.0 if surname and surname in header_key else 0.0,
        )
        if score > best_score:
            best, best_score = player, score
    return (best if best_score >= 0.58 else None), best_score


def parse_player(
    full: dict[str, Any], details: dict[str, Any], roster: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, float]:
    full_words = words(full)
    header = " ".join(item.text for item in full_words if 115 <= item.x <= 340 and 125 <= item.y <= 190)
    player, confidence = match_roster(header, roster)
    if not player:
        return None, confidence
    detail_words = words(details)
    overall = value_at(full_words, 143, 45, 105, 20)
    rating = value_at(full_words, 150, 335, 430, 20)
    surname = compact(player["name"].split()[-1])
    table_name = max(
        (
            item
            for item in full_words
            if 110 <= item.x <= 260
            and item.y >= 220
            and SequenceMatcher(None, compact(item.text), surname).ratio() >= 0.58
        ),
        key=lambda item: SequenceMatcher(None, compact(item.text), surname).ratio(),
        default=None,
    )
    position = player.get("position")
    if table_name:
        if rating is None:
            rating = value_at(full_words, table_name.y, 260, 335, 9)
        position_word = next(
            (item.text for item in full_words if 45 <= item.x <= 110 and abs(item.y - table_name.y) <= 7),
            None,
        )
        if position_word:
            position_key = compact(position_word)
            position_map = {
                "лфд": "LF",
                "пфд": "RF",
                "цап": "CAM",
                "лцп": "LCM",
                "пцп": "RCM",
                "цоп": "CDM",
                "лз": "LB",
                "лцз": "LCB",
                "пцз": "RCB",
                "пз": "RB",
                "врт": "GK",
            }
            best_position = max(
                position_map,
                key=lambda key: SequenceMatcher(None, position_key, key).ratio(),
            )
            if SequenceMatcher(None, position_key, best_position).ratio() >= 0.55:
                position = position_map[best_position]
    goals = value_at(detail_words, 199, 1120, 1182, 12)
    assists = value_at(detail_words, 225, 1120, 1182, 12)
    return (
        {
            "external_player_id": player.get("external_player_id"),
            "name": player["name"],
            "position": position,
            "overall": int(overall) if overall is not None else player.get("overall"),
            "rating": rating,
            "goals": int(goals) if goals is not None else None,
            "assists": int(assists) if assists is not None else None,
            "started": None,
            "substitute": None,
            "motm": None,
        },
        confidence,
    )


def build_draft(
    *,
    source_dir: Path | None = None,
    image_paths: list[Path] | None = None,
    data_dir: Path,
    ocr: WindowsOcr,
    roster: list[dict[str, Any]],
    career_save_id: int,
    season_id: int,
    club_team_external_id: int,
    club_name: str,
    played_at: str | None = None,
    competition_name: str | None = None,
    external_compobjid: int | None = None,
    opponent_name: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    if image_paths is not None:
        images = sorted(path for path in image_paths if path.suffix.lower() in IMAGE_SUFFIXES)
    elif source_dir is not None:
        images = sorted(path for path in source_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    else:
        raise ValueError("source_dir or image_paths is required")
    if not images:
        raise ValueError("No JPG/PNG screenshots found")
    batch_hash = hashlib.sha256("\n".join(path.name for path in images).encode()).hexdigest()[:12]
    draft_id = f"{images[0].stem}-{batch_hash}"
    image_dir = data_dir / "screenshots" / "drafts" / draft_id
    ocr_dir = data_dir / "screenshot_drafts" / draft_id / "ocr"
    image_dir.mkdir(parents=True, exist_ok=True)
    ocr_dir.mkdir(parents=True, exist_ok=True)

    recognized = []
    for source in images:
        target = image_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)
        full = ocr.recognize(source)
        kind = classify(full)
        if kind in {"summary", "shots", "passing", "defending"}:
            detail = ocr.recognize(source, "ru", (400, 155, 480, 500), 3)
            full = {
                **full,
                "text": f"{full.get('text', '')}\n{detail.get('text', '')}",
                "lines": [*full.get("lines", []), *detail.get("lines", [])],
            }
        if kind == "summary":
            for crop in ((100, 160, 260, 460), (930, 160, 260, 460)):
                side = ocr.recognize(source, "ru", crop, 3)
                full["text"] += f"\n{side.get('text', '')}"
                full["lines"] += side.get("lines", [])
        (ocr_dir / f"{source.stem}.json").write_text(
            json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        recognized.append((source, kind, full))

    scoreboard_source = next((row[0] for row in recognized if row[1] == "summary"), images[0])
    scoreboard_ocr = ocr.recognize(scoreboard_source, "en-US", (350, 20, 580, 100), 3)
    scoreboard = parse_scoreboard(scoreboard_ocr, club_name)
    summary = next((row[2] for row in recognized if row[1] == "summary"), None)
    opponent_stats, team_stats = parse_summary(summary) if summary else (empty_stats(), empty_stats())
    for _, kind, result in recognized:
        supplement_stats(kind, result, opponent_stats, team_stats)

    # Derive reliable values from totals when OCR missed a small number.
    for stats in (opponent_stats, team_stats):
        if (
            stats["shots_on_target"] is None
            and stats["shots"] is not None
            and stats["shot_accuracy"] is not None
        ):
            stats["shots_on_target"] = round(stats["shots"] * stats["shot_accuracy"] / 100)
        if (
            stats["completed_passes"] is None
            and stats["passes"] is not None
            and stats["pass_accuracy"] is not None
        ):
            stats["completed_passes"] = round(stats["passes"] * stats["pass_accuracy"] / 100)
        if (
            stats["shots_off_target"] is None
            and stats["shots"] is not None
            and stats["shots_on_target"] is not None
            and stats["blocked_shots"] is not None
        ):
            stats["shots_off_target"] = max(
                0, round(stats["shots"] - stats["shots_on_target"] - stats["blocked_shots"])
            )

    performances, roster_confidence = [], []
    for source, kind, full in recognized:
        if kind != "player":
            continue
        header = ocr.recognize(source, "ru", (35, 120, 410, 80), 3)
        full = {
            **full,
            "text": f"{full.get('text', '')}\n{header.get('text', '')}",
            "lines": [*full.get("lines", []), *header.get("lines", [])],
        }
        details = ocr.recognize(source, "ru", (830, 180, 400, 460), 3)
        parsed, confidence = parse_player(full, details, roster)
        if not parsed:
            latin_header = ocr.recognize(source, "en-US", (110, 125, 250, 70), 4)
            full["text"] += f"\n{latin_header.get('text', '')}"
            full["lines"] += latin_header.get("lines", [])
            parsed, confidence = parse_player(full, details, roster)
        roster_confidence.append(confidence)
        if parsed and not any(item["name"] == parsed["name"] for item in performances):
            performances.append(parsed)
        if team_stats["dribbles"] is None:
            detail_words = words(details)
            team_stats["dribbles"] = value_at(detail_words, 354, 1180, 1225, 12)
            if team_stats["dribbles"] is not None and team_stats["dribble_success"] is not None:
                team_stats["successful_dribbles"] = round(
                    team_stats["dribbles"] * team_stats["dribble_success"] / 100
                )

    detected_opponent = scoreboard["opponent_name_ocr"] or "Не распознано"
    match = {
        "career_save_id": career_save_id,
        "season_id": season_id,
        "source_external_match_id": f"ocr-{draft_id}",
        "played_at": played_at,
        "external_compobjid": external_compobjid,
        "competition_name": competition_name,
        "club_team_external_id": club_team_external_id,
        "opponent_name": opponent_name or detected_opponent,
        "club_was_home": scoreboard["club_was_home"],
        "club_goals": scoreboard["club_goals"],
        "opponent_goals": scoreboard["opponent_goals"],
        "duration_minutes": scoreboard["duration_minutes"],
        "team_stats": team_stats,
        "opponent_stats": opponent_stats,
        "timeline": [],
        "player_performances": performances,
        "screenshot_paths": [f"screenshots/drafts/{draft_id}/{path.name}" for path in images],
        "evidence_note": "Черновик Windows OCR: требуется подтверждение пользователя.",
    }
    warnings = []
    if not played_at:
        warnings.append("Дата матча не видна на стандартных послематчевых экранах.")
    if not competition_name:
        warnings.append("Турнир нужно выбрать перед подтверждением.")
    warnings.append(
        "Минуты событий на тёмном фоне распознаются нестабильно; хронология оставлена на проверку."
    )
    warnings.append("Старт/замена и MOTM требуют проверки по визуальным значкам.")
    draft = {
        "draft_version": 1,
        "id": draft_id,
        "status": "NEEDS_REVIEW",
        "source": "windows_media_ocr",
        "classification_counts": {
            kind: sum(1 for _, current, _ in recognized if current == kind)
            for kind in sorted({current for _, current, _ in recognized})
        },
        "scoreboard_ocr": scoreboard,
        "confidence": {
            "score": "high" if scoreboard["club_goals"] is not None else "low",
            "team_stats": "high" if team_stats["xg"] is not None else "medium",
            "players": "medium" if performances else "low",
            "player_roster_match_min": round(min(roster_confidence), 3) if roster_confidence else None,
            "timeline": "manual_review",
        },
        "warnings": warnings,
        "match": match,
    }
    draft_path = data_dir / "screenshot_drafts" / draft_id / "draft.json"
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path, draft


class ScreenshotWatcher:
    """Poll a Steam screenshot folder and create review-only match drafts."""

    def __init__(self, factory, settings, ocr: WindowsOcr):
        self.factory = factory
        self.settings = settings
        self.ocr = ocr
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.seen: set[tuple[str, int, int]] = set()
        self.pending: list[Path] = []
        self.last_new_at: float | None = None
        self.last_scan: str | None = None
        self.last_draft: str | None = None
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        required = (
            self.settings.screenshot_watch_dir,
            self.settings.screenshot_career_id,
            self.settings.screenshot_save_id,
            self.settings.screenshot_season_id,
            self.settings.screenshot_club_team_id,
        )
        return self.settings.screenshot_watcher_enabled and all(value is not None for value in required)

    def _files(self) -> list[Path]:
        folder = Path(self.settings.screenshot_watch_dir)
        if not folder.is_dir():
            raise FileNotFoundError(f"Screenshot folder does not exist: {folder}")
        return sorted(path for path in folder.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)

    @staticmethod
    def _fingerprint(path: Path) -> tuple[str, int, int]:
        stat = path.stat()
        return path.name, stat.st_size, stat.st_mtime_ns

    def start(self):
        if not self.configured or self.thread:
            return
        # Baseline existing files: only screenshots created after startup are observed.
        self.seen = {self._fingerprint(path) for path in self._files()}
        self.thread = threading.Thread(target=self._run, name="fc24-screenshot-watcher", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None

    def _roster(self) -> list[dict[str, Any]]:
        with self.factory() as session:
            rows = session.execute(
                select(Player, PlayerSeasonMetadata)
                .outerjoin(
                    PlayerSeasonMetadata,
                    (PlayerSeasonMetadata.player_id == Player.id)
                    & (PlayerSeasonMetadata.season_id == self.settings.screenshot_season_id),
                )
                .where(Player.career_id == self.settings.screenshot_career_id)
            ).all()
            return [
                {
                    "name": player.display_name,
                    "external_player_id": player.external_player_id,
                    "position": metadata.position if metadata else None,
                    "overall": metadata.overall if metadata else None,
                }
                for player, metadata in rows
            ]

    def _process_pending(self):
        paths, self.pending = self.pending, []
        draft_path, _ = build_draft(
            image_paths=paths,
            data_dir=self.settings.data_dir,
            ocr=self.ocr,
            roster=self._roster(),
            career_save_id=self.settings.screenshot_save_id,
            season_id=self.settings.screenshot_season_id,
            club_team_external_id=self.settings.screenshot_club_team_id,
            club_name=self.settings.screenshot_club_name,
        )
        self.last_draft = str(draft_path)
        self.last_error = None

    def _run(self):
        while not self.stop_event.wait(2):
            try:
                now = time.time()
                for path in self._files():
                    fingerprint = self._fingerprint(path)
                    if fingerprint in self.seen or now - path.stat().st_mtime < 2:
                        continue
                    self.seen.add(fingerprint)
                    self.pending.append(path)
                    self.last_new_at = now
                self.last_scan = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                if (
                    self.pending
                    and self.last_new_at is not None
                    and now - self.last_new_at >= self.settings.screenshot_quiet_seconds
                ):
                    self._process_pending()
            except Exception as error:  # keep the backend alive if OCR or the folder fails
                self.last_error = f"{type(error).__name__}: {error}"
                self.pending = []
