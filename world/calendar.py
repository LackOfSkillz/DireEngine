"""
DireEngine game-time calendar.

Single source of truth for the game's notion of "what time is it"
and "what season is it." Exposes pure functions that other systems
(foraging, weather, NPC schedules, festivals) can call to gate
behavior on time of day or season.

Two clocks:
  - Time-of-day runs on Evennia's gametime (TIME_FACTOR = 4.0,
    so 4 game days per real day). Used for day/night cycles.
  - Season is anchored to real-world wall-clock time in a
    configured timezone. Used for festival alignment and any
    seasonal content. This means in-game spring/summer/autumn/
    winter match real-world spring/summer/autumn/winter so events
    like Hallows Eve fest hit when players actually experience
    real-world October.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from evennia.utils import gametime


SEASONS = ("spring", "summer", "autumn", "winter")
TIMES_OF_DAY = ("night", "morning", "afternoon", "evening")

_TIME_OF_DAY_SLOTS = (
    ("night", 0, 6),
    ("morning", 6, 12),
    ("afternoon", 12, 18),
    ("evening", 18, 24),
)

_SEASON_BY_MONTH = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}


def _calendar_tz() -> ZoneInfo:
    """Resolve the configured calendar timezone, defaulting to UTC."""
    name = getattr(settings, "CALENDAR_TIMEZONE", "UTC") or "UTC"
    return ZoneInfo(name)


def _absolute_game_datetime() -> datetime.datetime:
    """Return the current absolute game-time as a naive UTC datetime."""
    timestamp = gametime.gametime(absolute=True)
    return datetime.datetime.utcfromtimestamp(timestamp)


def _time_of_day_for_hour(hour: int) -> str:
    """Map a 24-hour clock hour onto a time-of-day slot."""
    for label, start, end in _TIME_OF_DAY_SLOTS:
        if start <= hour < end:
            return label
    return "night"


def _season_for_month(month: int) -> str:
    """Map a calendar month onto a season."""
    return _SEASON_BY_MONTH.get(month, "winter")


def get_current_time_of_day() -> str:
    """Return the current game-time time-of-day slot."""
    game_dt = _absolute_game_datetime()
    return _time_of_day_for_hour(game_dt.hour)


def get_current_season() -> str:
    """Return the current real-world-anchored season."""
    now = datetime.datetime.now(tz=_calendar_tz())
    return _season_for_month(now.month)


def get_calendar_state() -> dict:
    """Return a structured snapshot of the current calendar state."""
    tz = _calendar_tz()
    real_now = datetime.datetime.now(tz=tz)
    game_dt = _absolute_game_datetime()
    elapsed_seconds = gametime.gametime(absolute=False)
    elapsed_days, remainder = divmod(int(elapsed_seconds), 86400)
    elapsed_hours, remainder = divmod(remainder, 3600)
    elapsed_minutes = remainder // 60

    return {
        "real_world": {
            "iso": real_now.isoformat(timespec="seconds"),
            "timezone": str(tz),
            "season": _season_for_month(real_now.month),
        },
        "game_time": {
            "absolute_iso": game_dt.isoformat(timespec="seconds"),
            "elapsed_days": elapsed_days,
            "elapsed_hours": elapsed_hours,
            "elapsed_minutes": elapsed_minutes,
            "time_of_day": _time_of_day_for_hour(game_dt.hour),
        },
        "configuration": {
            "time_factor": float(getattr(settings, "TIME_FACTOR", 1.0)),
            "ignore_downtimes": bool(getattr(settings, "TIME_IGNORE_DOWNTIMES", False)),
            "epoch": getattr(settings, "TIME_GAME_EPOCH", None),
        },
    }