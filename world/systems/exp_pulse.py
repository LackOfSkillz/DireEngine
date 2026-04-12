"""Global EXP pulse system driven by the scheduler."""

import time
from weakref import WeakSet

from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.systems.metrics import increment_counter, record_event
from world.systems.time_model import SHARED_TICKER


PULSE_TICK = 20
FULL_CYCLE = 200
GLOBAL_TICK = 0
EXP_TICKER_IDSTRING = "global_exp_pulse_tick"
EXP_PULSE_OWNER = "global-exp-pulse"
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


def exp_pulse_tick():
    global GLOBAL_TICK

    from engine.services.pulse_service import PulseService

    started_at = time.perf_counter()
    GLOBAL_TICK = (GLOBAL_TICK + PULSE_TICK) % FULL_CYCLE

    try:
        for char in get_active_characters():
            PulseService.process_skill_pulse(
                char,
                global_tick=GLOBAL_TICK,
                max_skills=MAX_SKILLS_PER_TICK,
                skill_group_offsets=SKILL_GROUP_OFFSETS,
            )
    finally:
        _log_exp_tick(started_at, 0.25)

    return GLOBAL_TICK


def process_scheduled_pulse(owner=None, payload=None):
    result = exp_pulse_tick()
    start_exp_ticker()
    return result


def start_exp_ticker():
    from world.systems.scheduler import schedule_event

    schedule_event(
        key=EXP_TICKER_IDSTRING,
        owner=EXP_PULSE_OWNER,
        delay=PULSE_TICK,
        callback="skills:process_pulse",
        payload={"tick_seconds": PULSE_TICK},
        metadata={"system": "skills", "type": "pulse", "timing_mode": SHARED_TICKER},
    )


__all__ = [
    "EXP_TICKER_IDSTRING",
    "EXP_PULSE_OWNER",
    "FULL_CYCLE",
    "GLOBAL_TICK",
    "MAX_SKILLS_PER_TICK",
    "PULSE_TICK",
    "SKILL_GROUP_OFFSETS",
    "exp_pulse_tick",
    "get_active_characters",
    "process_scheduled_pulse",
    "register_exp_character",
    "start_exp_ticker",
]