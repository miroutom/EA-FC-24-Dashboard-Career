"""Build a review-only match draft from FC 24 Steam screenshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import Player, PlayerSeasonMetadata
from app.screenshot_capture import WindowsOcr, build_draft


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--career-id", type=int, required=True)
    parser.add_argument("--save-id", type=int, required=True)
    parser.add_argument("--season-id", type=int, required=True)
    parser.add_argument("--club-team-id", type=int, required=True)
    parser.add_argument("--club-name", default="RB Salzburg")
    parser.add_argument("--played-at")
    parser.add_argument("--competition-name")
    parser.add_argument("--competition-id", type=int)
    parser.add_argument("--opponent-name")
    return parser.parse_args()


def main():
    args = arguments()
    engine = create_engine(f"sqlite:///{args.data_dir / 'analytics.sqlite3'}")
    with Session(engine) as session:
        rows = session.execute(
            select(Player, PlayerSeasonMetadata)
            .outerjoin(
                PlayerSeasonMetadata,
                (PlayerSeasonMetadata.player_id == Player.id)
                & (PlayerSeasonMetadata.season_id == args.season_id),
            )
            .where(Player.career_id == args.career_id)
        ).all()
        roster = [
            {
                "name": player.display_name,
                "external_player_id": player.external_player_id,
                "position": metadata.position if metadata else None,
                "overall": metadata.overall if metadata else None,
            }
            for player, metadata in rows
        ]
    draft_path, draft = build_draft(
        source_dir=args.source,
        data_dir=args.data_dir,
        ocr=WindowsOcr(ROOT / "scripts" / "windows_ocr.ps1"),
        roster=roster,
        career_save_id=args.save_id,
        season_id=args.season_id,
        club_team_external_id=args.club_team_id,
        club_name=args.club_name,
        played_at=args.played_at,
        competition_name=args.competition_name,
        external_compobjid=args.competition_id,
        opponent_name=args.opponent_name,
    )
    summary = {
        "draft": str(draft_path),
        "status": draft["status"],
        "classification_counts": draft["classification_counts"],
        "confidence": draft["confidence"],
        "score": [draft["match"]["opponent_goals"], draft["match"]["club_goals"]],
        "players": len(draft["match"]["player_performances"]),
        "warnings": draft["warnings"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
