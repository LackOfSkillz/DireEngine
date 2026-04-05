"""
Global EXP pulse system (Evennia ticker-based)
"""

import time
from weakref import WeakSet

from evennia import TICKER_HANDLER
from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.systems.metrics import increment_counter, record_event
from world.systems.skills import SKILL_GROUPS, is_active, pulse
from world.systems.timing_audit import register_ticker_metadata


PULSE_TICK = 20
FULL_CYCLE = 200
GLOBAL_TICK = 0
EXP_TICKER_IDSTRING = "global_exp_pulse_tick"
MAX_SKILLS_PER_TICK = 10
_ACTIVE_EXP_CHARACTERS = WeakSet()

SKILL_GROUP_OFFSETS = {
    100: 0,
    120: 20,
    140: 40,
    160: 60,
    180: 80,
}


def get_active_characters():
    active = []
    seen_ids = set()
    for char in list(_ACTIVE_EXP_CHARACTERS):
        object_id = int(getattr(char, "id", 0) or 0)
        if object_id <= 0 or object_id in seen_ids:
            continue
        seen_ids.add(object_id)
        active.append(char)
    if active:
        return active
    return list(ObjectDB.objects.filter(db_typeclass_path__icontains="characters.Character").order_by("id"))


def register_exp_character(character):
    if character is None or not getattr(character, "pk", None):
        return character
    try:
        _ACTIVE_EXP_CHARACTERS.add(character)
    except TypeError:
        pass
    return character


def _log_exp_tick(started_at, threshold):
    duration = time.perf_counter() - started_at
    from tools.diretest.core.runtime import record_script_delay

    increment_counter("ticker.execute")
    increment_counter("ticker.execute.exp_pulse_tick")
    record_event("ticker.execute", duration * 1000.0, metadata={"ticker": "exp_pulse_tick"})
    record_script_delay(duration * 1000.0, source="ticker:exp_pulse_tick")
    if duration > threshold:
        logger.log_warn(f"exp_pulse_tick slow: {duration:.4f}s")


def _ticker_registered():
    entries = dict(TICKER_HANDLER.all(PULSE_TICK) or {})
    callbacks = dict(entries.get(PULSE_TICK, {}) or {})
    for store_key, payload in callbacks.items():
        key_tuple = tuple(store_key or ())
        callback = (payload or {}).get("_callback")
        idstring = key_tuple[4] if len(key_tuple) >= 5 else ""
        persistent = bool(key_tuple[5]) if len(key_tuple) >= 6 else False
        if callback is exp_pulse_tick and idstring == EXP_TICKER_IDSTRING and persistent:
            return True
    return False


def exp_pulse_tick():
    global GLOBAL_TICK

    started_at = time.perf_counter()
    GLOBAL_TICK = (GLOBAL_TICK + PULSE_TICK) % FULL_CYCLE

    try:
        for char in get_active_characters():
            if not hasattr(char, "exp_skills"):
                continue

            processed = 0
            for skill_name, skill in char.exp_skills.skills.items():
                if processed >= MAX_SKILLS_PER_TICK:
                    break
                if not is_active(skill):
                    continue
                group = SKILL_GROUPS.get(skill_name, 100)
                offset = SKILL_GROUP_OFFSETS.get(group, 0)
                if GLOBAL_TICK != offset:
                    continue
                pulse(skill)
                processed += 1
    finally:
        _log_exp_tick(started_at, 0.25)

    return GLOBAL_TICK


def start_exp_ticker():
    if not _ticker_registered():
        TICKER_HANDLER.add(PULSE_TICK, exp_pulse_tick, idstring=EXP_TICKER_IDSTRING, persistent=True)
    register_ticker_metadata(
        PULSE_TICK,
        exp_pulse_tick,
        idstring=EXP_TICKER_IDSTRING,
        persistent=True,
        system="world.exp_pulse",
        reason="Ticker-driven staggered EXP pool draining and rank progression across character skill groups.",
    )


__all__ = [
    "EXP_TICKER_IDSTRING",
    "FULL_CYCLE",
    "GLOBAL_TICK",
    "MAX_SKILLS_PER_TICK",
    "PULSE_TICK",
    "SKILL_GROUP_OFFSETS",
    "exp_pulse_tick",
    "get_active_characters",
    "register_exp_character",
    "start_exp_ticker",
]