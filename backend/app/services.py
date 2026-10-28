import hashlib
import json
import unicodedata

from sqlalchemy import select

from .models import Career, Player, PlayerAlias, Season


class Problem(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def normalize(name):
    return " ".join(unicodedata.normalize("NFC", name).split()).casefold()


def career(session, career_id):
    result = session.get(Career, career_id)
    if not result:
        raise Problem(404, "NOT_FOUND", "Карьера не найдена")
    return result


def season(session, career_id, year):
    found = session.scalar(select(Season).where(Season.career_id == career_id, Season.start_year == year))
    if found:
        return found
    found = Season(career_id=career_id, start_year=year, end_year=year + 1)
    session.add(found)
    session.flush()
    return found


def historical_player(session, career_id, name):
    alias = session.scalar(
        select(PlayerAlias).where(PlayerAlias.career_id == career_id, PlayerAlias.alias == normalize(name))
    )
    if alias:
        return session.get(Player, alias.player_id)
    result = Player(career_id=career_id, display_name=name, normalized_name=normalize(name))
    session.add(result)
    session.flush()
    session.add(
        PlayerAlias(
            career_id=career_id, player_id=result.id, alias=normalize(name), source="exact_import_name"
        )
    )
    return result


def live_player(session, career_id, external_id, name=None):
    found = session.scalar(
        select(Player).where(Player.career_id == career_id, Player.external_player_id == external_id)
    )
    if found:
        return found
    # Names are display-only. Never merge historical players by surname or guessed abbreviation.
    label = name or f"Игрок #{external_id}"
    found = Player(
        career_id=career_id,
        external_player_id=external_id,
        display_name=label,
        normalized_name=normalize(label),
    )
    session.add(found)
    session.flush()
    return found
