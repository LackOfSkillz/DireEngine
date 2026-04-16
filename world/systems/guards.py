import json
import random
import time
import warnings
from collections.abc import Mapping
from uuid import uuid4

from django.db import connection
from django.conf import settings
from evennia.objects.models import ObjectDB
from evennia.utils import logger
from evennia.utils.create import create_object, create_script

from world.systems.justice import begin_arrest, can_be_arrested, complete_arrest, get_wanted_tier


GUARD_TEMPLATE_CACHE = []
ACTIVE_GUARDS = []

GUARD_MOVE_COOLDOWN = 20.0
GUARD_DWELL_THRESHOLD = 20.0
GUARD_IDLE_MAX = 90.0
GUARD_CLUMP_EXIT_DELAY = 5.0
GUARD_RECENT_ROOM_LIMIT = 5
GUARD_DEFAULT_PATROL_RADIUS = 20
GUARD_PATROL_ZONE = "landing"
GUARD_TICK_INTERVAL = 20
GUARD_MOVE_CHANCE = 0.55
GUARD_MESSAGE_COOLDOWN = 7.5
GUARD_IDLE_MESSAGE_CHANCE = 0.25
GUARD_TARGET_MEMORY = 120.0
GUARD_WATCH_THRESHOLD = 2
GUARD_ARREST_THRESHOLD = 5
GUARD_WATCH_MESSAGE_COOLDOWN = 30.0
GUARD_SUSPICION_DECAY_INTERVAL = 30.0
GUARD_SHARED_SUSPICION_WATCH = 1
GUARD_SHARED_SUSPICION_ARREST = 2
GUARD_MAX_FOLLOW_STEPS = 2
GUARD_WARNING_COOLDOWN = 10.0
GUARD_CONFRONT_TIMEOUT = 30.0
REPEAT_OFFENDER_WARNING_THRESHOLD = 3
GUARD_DISPLAY_NAME = "Town Guard"
LAST_GUARD_TICK_TIME = 0.0
LAST_GUARD_TICK_SUMMARY = {}
GUARD_TICK_RUNNING = False
GUARD_BEHAVIOR_SCRIPT_KEY = "guard_behavior"
GUARD_BEHAVIOR_SCRIPT_PATH = "typeclasses.scripts.GuardBehaviorScript"
_VALID_GUARD_PATROL_MODES = {"global", "hybrid", "per_guard"}
LEGACY_GUARD_RUNTIME_BLOCK_MSG = "Legacy guard execution path blocked because DireSim owns scheduling."
LEGACY_GUARD_TRIPWIRE_MSG = "🚨 LEGACY GUARD PATH EXECUTED 🚨"
GUARD_TYPECLASS_PATHS = (
    "typeclasses.npcs.GuardNPC",
    "typeclasses.npcs.guard.GuardNPC",
    "typeclasses._guard_npc_impl.GuardNPC",
)

GUARD_DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
    "u": "up",
    "d": "down",
    "in": "in",
    "out": "out",
}

GUARD_DIRECTION_OPPOSITES = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}

GUARD_ARRIVAL_MESSAGES = [
    "A town guard strides in from the {direction}, posture alert.",
    "A town guard enters from the {direction}, eyes already scanning the area.",
    "A town guard steps in from the {direction}, pausing just inside the street.",
    "A town guard arrives from the {direction}, gaze steady and watchful.",
    "A town guard moves in from the {direction}, taking in the surroundings at a glance.",
    "A town guard enters from the {direction} with measured, deliberate steps.",
]

GUARD_IDLE_MESSAGES = [
    "A town guard surveys the area, watchful for trouble.",
    "A town guard pauses, eyes moving from one passerby to the next.",
    "A town guard shifts their weight, scanning the street with quiet focus.",
    "A town guard studies the surroundings as if expecting something to happen.",
    "A town guard keeps a steady watch over the area.",
    "A town guard glances down the street, then back again.",
]

GUARD_DEPARTURE_MESSAGES = [
    "A town guard gives the area one last look before heading {direction}.",
    "A town guard turns and resumes their patrol to the {direction}.",
    "A town guard nods faintly, then moves {direction}.",
    "A town guard sets off again, continuing their patrol {direction}.",
    "A town guard glances around once more and heads {direction}.",
    "A town guard pivots on their heel and patrols {direction}.",
]

GUARD_NONSTANDARD_ARRIVAL_MESSAGES = [
    "A town guard strides in from {direction}, posture alert.",
    "A town guard enters from {direction}, eyes already scanning the area.",
    "A town guard steps in from {direction}, pausing just inside the street.",
    "A town guard arrives from {direction}, gaze steady and watchful.",
    "A town guard moves in from {direction}, taking in the surroundings at a glance.",
    "A town guard enters from {direction} with measured, deliberate steps.",
]

GUARD_NONSTANDARD_DEPARTURE_MESSAGES = [
    "A town guard gives the area one last look before leaving through {direction}.",
    "A town guard turns and resumes their patrol through {direction}.",
    "A town guard nods faintly, then heads through {direction}.",
    "A town guard sets off again, continuing their patrol through {direction}.",
    "A town guard glances around once more and moves through {direction}.",
    "A town guard pivots on their heel and patrols through {direction}.",
]

GUARD_MESSAGE_POOLS = {
    "arrival": GUARD_ARRIVAL_MESSAGES,
    "idle": GUARD_IDLE_MESSAGES,
    "departure": GUARD_DEPARTURE_MESSAGES,
}


def _guard_patrol_debug_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_PATROL_DEBUG", False))


def _log_guard_patrol_debug(message):
    if _guard_patrol_debug_enabled():
        logger.log_info(f"[Guards] {message}")


def _normalize_guard_direction_label(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    compact = raw.replace("_", " ").replace("-", " ")
    token = compact.split()[0]
    alias = GUARD_DIRECTION_ALIASES.get(token, "")
    if alias:
        return alias
    merged = compact.replace(" ", "")
    if merged in GUARD_DIRECTION_OPPOSITES:
        return merged
    return token


def _is_standard_guard_direction(value):
    normalized = _normalize_guard_direction_label(value)
    return normalized in GUARD_DIRECTION_OPPOSITES


def get_exit_label(exit_obj):
    if exit_obj is None:
        return ""
    raw_values = []
    raw_direction = getattr(getattr(exit_obj, "db", None), "direction", None)
    if raw_direction:
        raw_values.append(str(raw_direction))
    raw_values.append(str(getattr(exit_obj, "key", "") or ""))
    aliases = getattr(exit_obj, "aliases", None)
    if aliases is not None and hasattr(aliases, "all"):
        try:
            raw_values.extend(str(alias) for alias in list(aliases.all()) if str(alias or "").strip())
        except Exception:
            pass
    for candidate in raw_values:
        normalized = _normalize_guard_direction_label(candidate)
        if not normalized:
            continue
        if _is_standard_guard_direction(normalized):
            return normalized
        cleaned = str(candidate or "").strip().lower().replace("_", " ").replace("-", " ")
        cleaned = " ".join(part for part in cleaned.split() if part)
        if not cleaned:
            continue
        if cleaned.startswith("the "):
            return cleaned
        return f"the {cleaned}"
    return ""


def _get_guard_direction_label_for_exit(exit_obj):
    return get_exit_label(exit_obj)


def _get_guard_arrival_exit(room, source_location):
    if room is None or source_location is None:
        return None
    for obj in list(getattr(room, "contents", None) or []):
        if getattr(obj, "destination", None) == source_location:
            return obj
    return None


def _get_guard_arrival_direction_label(room, source_location):
    return _get_guard_direction_label_for_exit(_get_guard_arrival_exit(room, source_location))


def _format_guard_direction_for_message(direction, fallback="nearby"):
    raw = str(direction or "").strip().lower()
    if not raw:
        return str(fallback or "nearby")
    if raw.startswith("the "):
        return raw
    normalized = _normalize_guard_direction_label(raw)
    if _is_standard_guard_direction(normalized):
        return normalized
    return raw.replace("_", " ").replace("-", " ") or str(fallback or "nearby")


def _select_guard_message(guard, message_type, templates=None):
    messages = list(templates if templates is not None else GUARD_MESSAGE_POOLS.get(str(message_type or ""), []) or [])
    if not messages:
        return None, None
    last_type = str(getattr(getattr(guard, "db", None), "last_message_type", "") or "")
    last_id = getattr(getattr(guard, "db", None), "last_message_index", None)
    available = list(enumerate(messages))
    if len(available) > 1 and last_type == str(message_type or ""):
        try:
            last_index = int(last_id)
        except (TypeError, ValueError):
            last_index = -1
        available = [(index, text) for index, text in available if index != last_index]
    if not available:
        available = list(enumerate(messages))
    return random.choice(available)


def _emit_guard_patrol_message(guard, message_type, room=None, direction="", stats=None, probability=1.0, bypass_cooldown=False, templates=None):
    room = room or getattr(guard, "location", None)
    if room is None or not hasattr(room, "msg_contents"):
        return None
    now = time.time()
    last_message_time = float(getattr(getattr(guard, "db", None), "last_message_time", 0.0) or 0.0)
    if not bypass_cooldown and last_message_time and (now - last_message_time) < GUARD_MESSAGE_COOLDOWN:
        return None
    if probability < 1.0 and random.random() > float(probability):
        return None
    message_id, template = _select_guard_message(guard, message_type, templates=templates)
    if template is None:
        return None
    payload = template.format(
        guard=str(getattr(guard, "key", GUARD_DISPLAY_NAME) or GUARD_DISPLAY_NAME),
        direction=_format_guard_direction_for_message(direction),
    )
    try:
        room.msg_contents(payload, exclude=[guard])
    except Exception as error:
        logger.log_trace(
            f"guards._emit_guard_patrol_message failed for guard #{getattr(guard, 'id', '?')} type={message_type}: {error}"
        )
        return None
    guard.db.last_message_type = str(message_type or "")
    guard.db.last_message_index = int(message_id)
    guard.db.last_message_id = int(message_id)
    guard.db.last_message_time = now
    if stats is not None:
        stats["message_count"] = int(stats.get("message_count", 0) or 0) + 1
    return payload


def _emit_guard_departure_message(guard, selected_exit, stats=None):
    direction = _get_guard_direction_label_for_exit(selected_exit)
    room = getattr(guard, "location", None)
    templates = None
    if direction and not _is_standard_guard_direction(direction):
        templates = GUARD_NONSTANDARD_DEPARTURE_MESSAGES
    return _emit_guard_patrol_message(
        guard,
        "departure",
        room=room,
        direction=direction,
        stats=stats,
        templates=templates,
    )


def _emit_guard_entry_message(guard, source_location=None):
    room = getattr(guard, "location", None)
    if room is None:
        return None
    arrival_exit = _get_guard_arrival_exit(room, source_location)
    direction = _get_guard_direction_label_for_exit(arrival_exit)
    stats = getattr(getattr(guard, "ndb", None), "guard_tick_stats", None)
    templates = None
    formatted_direction = str(direction or "")
    if direction and not _is_standard_guard_direction(direction):
        templates = GUARD_NONSTANDARD_ARRIVAL_MESSAGES
    emitted = _emit_guard_patrol_message(
        guard,
        "arrival",
        room=room,
        direction=formatted_direction,
        stats=stats,
        bypass_cooldown=True,
        templates=templates,
    )
    if emitted:
        room.db.last_guard_entry_time = time.time()
        room.db.last_guard_entry_message = str(emitted)
    return emitted


def _maybe_emit_guard_idle_look(guard, stats=None):
    room = getattr(guard, "location", None)
    return _emit_guard_patrol_message(
        guard,
        "idle",
        room=room,
        stats=stats,
        probability=GUARD_IDLE_MESSAGE_CHANCE,
    )


def _handle_guard_idle_cycle(guard, now, stats=None, reason="idle"):
    guard.db.last_idle_time = float(now or time.time())
    _maybe_emit_guard_idle_look(guard, stats=stats)
    _log_guard_patrol_debug(
        f"Guard {getattr(guard, 'key', GUARD_DISPLAY_NAME)}(#{int(getattr(guard, 'id', 0) or 0)}) idle reason={reason}"
    )
    return False


def _ensure_guard_patrol_state_defaults(guard):
    if guard is None or not hasattr(guard, "db"):
        return
    last_room_id = getattr(guard.db, "last_room_id", None)
    if last_room_id in (None, "", 0, "0"):
        previous_room_id = int(getattr(guard.db, "previous_room_id", 0) or 0)
        guard.db.last_room_id = previous_room_id or None
    if getattr(guard.db, "last_message_type", None) is None:
        guard.db.last_message_type = None
    if getattr(guard.db, "last_message_id", None) is None:
        guard.db.last_message_id = None
    if getattr(guard.db, "last_message_index", None) is None:
        guard.db.last_message_index = getattr(guard.db, "last_message_id", None)
    if getattr(guard.db, "last_message_time", None) is None:
        guard.db.last_message_time = 0.0


def _guard_script_diagnostics_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_SCRIPT_DIAGNOSTICS", False))


def _get_guard_script_diagnostic_guard_id():
    return max(0, int(getattr(settings, "GUARD_SCRIPT_DIAGNOSTIC_GUARD_ID", 0) or 0))


def _guard_script_force_move_enabled():
    return bool(getattr(settings, "GUARD_SCRIPT_FORCE_MOVE_DIAGNOSTIC", False))


def is_diresim_enabled():
    return bool(getattr(settings, "ENABLE_DIRESIM_KERNEL", False))


def _legacy_guard_test_adapter_enabled():
    return bool(getattr(settings, "ENABLE_LEGACY_GUARD_TEST_ADAPTER", False))


def _legacy_guard_tripwire_enabled():
    return bool(getattr(settings, "ENABLE_LEGACY_GUARD_TRIPWIRE", True))


def log_legacy_guard_runtime_block(surface, level="warn"):
    message = f"[DireSim] {LEGACY_GUARD_RUNTIME_BLOCK_MSG} surface={surface}"
    if str(level or "warn").strip().lower() == "error":
        logger.log_err(message)
        return message
    logger.log_warn(message)
    return message


def emit_legacy_guard_tripwire(surface):
    message = f"{LEGACY_GUARD_TRIPWIRE_MSG} surface={surface}"
    if _legacy_guard_tripwire_enabled():
        logger.log_err(message)
    return message


def _legacy_guard_source_allowed(source):
    return str(source or "").startswith("legacy_test_adapter")


def _per_guard_guard_behavior_enabled():
    if is_diresim_enabled():
        return False
    return bool(getattr(settings, "ENABLE_PER_GUARD_GUARD_BEHAVIOR", True))


def _guard_startup_trace_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_STARTUP_TRACE", False))


def _guard_behavior_timing_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_BEHAVIOR_TIMING", True))


def _get_guard_behavior_warn_seconds():
    return float(getattr(settings, "GUARD_BEHAVIOR_WARN_SECONDS", 0.05) or 0.05)


def _get_guard_timing_bucket(stats):
    if stats is None:
        return None
    bucket = stats.get("timings")
    if isinstance(bucket, dict):
        return bucket
    bucket = {}
    stats["timings"] = bucket
    return bucket


def _record_guard_timing(stats, key, duration_ms):
    bucket = _get_guard_timing_bucket(stats)
    if bucket is None:
        return
    bucket[key] = round(float(bucket.get(key, 0.0) or 0.0) + float(duration_ms or 0.0), 3)


def _timed_guard_call(stats, timing_key, func, *args, **kwargs):
    started_perf = time.perf_counter()
    result = func(*args, **kwargs)
    duration_ms = round((time.perf_counter() - started_perf) * 1000.0, 3)
    _record_guard_timing(stats, timing_key, duration_ms)
    return result, duration_ms


def _timed_guard_phase(phase_timings, phase_name, func, *args, **kwargs):
    started_perf = time.perf_counter()
    result = func(*args, **kwargs)
    phase_timings[phase_name] = round((time.perf_counter() - started_perf) * 1000.0, 3)
    return result


def _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, result, stats=None):
    duration_ms = round((time.perf_counter() - started_perf) * 1000.0, 3)
    for phase_name, phase_duration in phase_timings.items():
        _record_guard_timing(stats, f"behavior.{phase_name}", phase_duration)
    _record_guard_timing(stats, "behavior.total", duration_ms)
    if is_guard_script_diagnostic_target(guard):
        _update_guard_script_diagnostic_state(
            guard,
            last_behavior_duration_ms=duration_ms,
            last_behavior_phase_timings=dict(phase_timings),
            last_behavior_source=str(source),
            last_behavior_result=str(result),
        )
    if _guard_behavior_timing_enabled() and duration_ms >= (_get_guard_behavior_warn_seconds() * 1000.0):
        logger.log_warn(
            "[Guards] Slow guard behavior tick "
            f"guard={getattr(guard, 'key', GUARD_DISPLAY_NAME)}(#{int(getattr(guard, 'id', 0) or 0)}) "
            f"source={source} result={result} duration_ms={duration_ms} phases={dict(phase_timings)}"
        )


def _get_script_start_count(script):
    if script is None:
        return 0
    return int(getattr(getattr(script, "db", None), "start_count", 0) or 0)


def _guard_behavior_script_is_zombie(script):
    if script is None:
        return False
    try:
        return bool(getattr(script, "is_active", False)) and script.time_until_next_repeat() is None
    except Exception:
        return bool(getattr(script, "is_active", False))


def _get_default_guard_script_diagnostic_guard_id():
    candidate_ids = []
    for guard in sorted(iter_active_guards(), key=lambda entry: int(getattr(entry, "id", 0) or 0)):
        if has_guard_behavior_script(guard):
            candidate_ids.append(int(getattr(guard, "id", 0) or 0))
    return candidate_ids[0] if candidate_ids else 0


def is_guard_script_diagnostic_target(guard):
    if not _guard_script_diagnostics_enabled() or not _is_active_guard(guard):
        return False
    configured_guard_id = _get_guard_script_diagnostic_guard_id()
    target_guard_id = configured_guard_id if configured_guard_id > 0 else _get_default_guard_script_diagnostic_guard_id()
    return int(getattr(guard, "id", 0) or 0) == int(target_guard_id or 0)


def _update_guard_script_diagnostic_state(guard, **fields):
    if not is_guard_script_diagnostic_target(guard):
        return {}
    state = dict(getattr(getattr(guard, "db", None), "guard_behavior_diagnostic", None) or {})
    state.update(fields)
    guard.db.guard_behavior_diagnostic = state
    return state


def _increment_guard_script_diagnostic_counter(guard, key, delta=1):
    if not is_guard_script_diagnostic_target(guard):
        return 0
    state = dict(getattr(getattr(guard, "db", None), "guard_behavior_diagnostic", None) or {})
    state[key] = int(state.get(key, 0) or 0) + int(delta or 0)
    guard.db.guard_behavior_diagnostic = state
    return int(state[key] or 0)


def get_guard_patrol_mode():
    mode = str(getattr(settings, "GUARD_PATROL_MODE", "global") or "global").strip().lower()
    if mode not in _VALID_GUARD_PATROL_MODES:
        logger.log_warn(f"[Guards] Invalid GUARD_PATROL_MODE={mode!r}; defaulting to 'global'.")
        return "global"
    return mode


def get_guard_per_guard_rollout_count():
    return max(0, int(getattr(settings, "GUARD_PER_GUARD_ROLLOUT_COUNT", 0) or 0))


def _iter_guard_behavior_scripts(guard):
    if guard is None or not hasattr(guard, "scripts"):
        return []
    scripts = []
    for script in list(guard.scripts.all() or []):
        if getattr(script, "typeclass_path", "") == GUARD_BEHAVIOR_SCRIPT_PATH:
            scripts.append(script)
    return scripts


def has_guard_behavior_script(guard):
    return bool(_iter_guard_behavior_scripts(guard))


def _cleanup_guard_behavior_script_duplicates(guard):
    scripts = _iter_guard_behavior_scripts(guard)
    keeper = scripts[0] if scripts else None
    for duplicate in scripts[1:]:
        try:
            duplicate.delete()
        except Exception:
            pass
    return keeper


def _ensure_guard_behavior_script_started(guard, script, source="unknown"):
    if guard is None or script is None:
        return None
    try:
        was_zombie = _guard_behavior_script_is_zombie(script)
        if was_zombie:
            logger.log_info(
                f"[Guards] Resetting broken per-guard script for {getattr(guard, 'key', 'Unknown')}(#{int(getattr(guard, 'id', 0) or 0)}) source={source}"
            )
            interval, start_delay_seconds = script.roll_timing() if hasattr(script, "roll_timing") else (float(getattr(script, "interval", 25.0) or 25.0), 0.0)
            script.stop()
            script.start(interval=interval, start_delay=start_delay_seconds)
        if is_guard_script_diagnostic_target(guard):
            _update_guard_script_diagnostic_state(
                guard,
                last_start_ensured_at=time.time(),
                last_start_ensured_source=str(source),
                last_start_ensured_script_id=int(getattr(script, "id", 0) or 0),
                last_start_was_zombie=bool(was_zombie),
                last_start_ensured_interval=float(getattr(script, "interval", 0.0) or 0.0),
                last_start_ensured_delay_seconds=float(getattr(getattr(script, "db", None), "start_delay_seconds", 0.0) or 0.0),
            )
            logger.log_info(
                f"[Guards][Diag] Ensured GuardBehaviorScript started for guard {int(getattr(guard, 'id', 0) or 0)} source={source} script_id={int(getattr(script, 'id', 0) or 0)} zombie_reset={was_zombie}"
            )
    except Exception as error:
        logger.log_trace(
            f"guards._ensure_guard_behavior_script_started failed for guard #{getattr(guard, 'id', '?')} source={source}: {error}"
        )
    return script


def _get_hybrid_rollout_guard_ids():
    rollout_count = get_guard_per_guard_rollout_count()
    if rollout_count <= 0:
        return set()
    guard_ids = []
    for guard in sorted(iter_active_guards(), key=lambda entry: int(getattr(entry, "id", 0) or 0)):
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id > 0:
            guard_ids.append(guard_id)
        if len(guard_ids) >= rollout_count:
            break
    return set(guard_ids)


def should_guard_use_per_guard_execution(guard):
    if not _is_active_guard(guard):
        return False
    if not _per_guard_guard_behavior_enabled():
        return False

    mode = get_guard_patrol_mode()
    if mode == "global":
        return False
    if mode == "per_guard":
        return True

    guard_id = int(getattr(guard, "id", 0) or 0)
    return guard_id > 0 and guard_id in _get_hybrid_rollout_guard_ids()


def ensure_guard_behavior_script(guard):
    if not _is_active_guard(guard):
        return None

    if is_diresim_enabled():
        log_legacy_guard_runtime_block("ensure_guard_behavior_script")
        remove_guard_behavior_script(guard)
        return None

    existing = _cleanup_guard_behavior_script_duplicates(guard)
    if existing is not None:
        return _ensure_guard_behavior_script_started(guard, existing, source="existing")

    script = create_script(GUARD_BEHAVIOR_SCRIPT_PATH, key=GUARD_BEHAVIOR_SCRIPT_KEY, obj=guard, autostart=False)
    if hasattr(script, "roll_timing"):
        interval, start_delay_seconds = script.roll_timing()
        script.start(interval=interval, start_delay=start_delay_seconds)
    script = _ensure_guard_behavior_script_started(guard, script, source="created")
    logger.log_info(
        f"[Guards] Attached per-guard behavior script to {getattr(guard, 'key', 'Unknown')}(#{int(getattr(guard, 'id', 0) or 0)}) mode={get_guard_patrol_mode()}"
    )
    return script


def remove_guard_behavior_script(guard):
    removed = 0
    for script in _iter_guard_behavior_scripts(guard):
        try:
            script.delete()
            removed += 1
        except Exception:
            continue
    if removed > 0:
        logger.log_info(
            f"[Guards] Removed per-guard behavior script from {getattr(guard, 'key', 'Unknown')}(#{int(getattr(guard, 'id', 0) or 0)}) mode={get_guard_patrol_mode()}"
        )
    return removed


def guard_has_per_guard_ownership(guard):
    return bool(has_guard_behavior_script(guard) and should_guard_use_per_guard_execution(guard))


def sync_guard_execution_mode(guard):
    if not _is_active_guard(guard):
        remove_guard_behavior_script(guard)
        return None

    if is_diresim_enabled():
        remove_guard_behavior_script(guard)
        return None

    if should_guard_use_per_guard_execution(guard):
        return ensure_guard_behavior_script(guard)

    remove_guard_behavior_script(guard)
    return None


def sync_all_guard_behavior_scripts():
    synced = {
        "attached": 0,
        "removed": 0,
        "started": 0,
        "reset": 0,
        "eligible_count": 0,
        "ineligible_count": 0,
        "existing_script_count": 0,
        "mode": get_guard_patrol_mode(),
        "guard_count": 0,
    }

    if is_diresim_enabled():
        cleanup = cleanup_legacy_guard_behavior_scripts()
        synced.update(
            {
                "removed": int(cleanup.get("removed_script_count", 0) or 0),
                "existing_script_count": int(cleanup.get("scripted_guard_count_before", 0) or 0),
                "guard_count": int(cleanup.get("guard_count", 0) or 0),
                "blocked_by_diresim": True,
            }
        )
        log_legacy_guard_runtime_block("sync_all_guard_behavior_scripts")
        return synced

    for guard in iter_active_guards():
        synced["guard_count"] += 1
        if should_guard_use_per_guard_execution(guard):
            synced["eligible_count"] += 1
        else:
            synced["ineligible_count"] += 1
        had_script = has_guard_behavior_script(guard)
        if had_script:
            synced["existing_script_count"] += 1
        before_script = _cleanup_guard_behavior_script_duplicates(guard)
        before_start_count = _get_script_start_count(before_script)
        was_zombie = _guard_behavior_script_is_zombie(before_script)
        result = sync_guard_execution_mode(guard)
        has_script_now = result is not None or has_guard_behavior_script(guard)
        after_start_count = _get_script_start_count(result if result is not None else _cleanup_guard_behavior_script_duplicates(guard))
        if not had_script and has_script_now:
            synced["attached"] += 1
        elif had_script and not has_script_now:
            synced["removed"] += 1
        if after_start_count > before_start_count:
            synced["started"] += 1
        if was_zombie:
            synced["reset"] += 1
    if _guard_startup_trace_enabled():
        logger.log_info(
            "[Guards][StartupDiag] sync_all_guard_behavior_scripts "
            f"mode={synced['mode']} guard_count={synced['guard_count']} eligible={synced['eligible_count']} "
            f"ineligible={synced['ineligible_count']} existing={synced['existing_script_count']} "
            f"attached={synced['attached']} started={synced['started']} reset={synced['reset']} removed={synced['removed']}"
        )
    return synced


def cleanup_legacy_guard_behavior_scripts():
    summary = {
        "guard_count": 0,
        "scripted_guard_count_before": 0,
        "removed_script_count": 0,
        "scripted_guard_count_after": 0,
    }
    for guard in iter_active_guards():
        summary["guard_count"] += 1
        if has_guard_behavior_script(guard):
            summary["scripted_guard_count_before"] += 1
        summary["removed_script_count"] += int(remove_guard_behavior_script(guard) or 0)
        if has_guard_behavior_script(guard):
            summary["scripted_guard_count_after"] += 1
    return summary


def get_valid_guard_templates(limit=15, refresh=False):
    global GUARD_TEMPLATE_CACHE

    if refresh or not GUARD_TEMPLATE_CACHE:
        GUARD_TEMPLATE_CACHE = _load_valid_guard_templates()

    requested = max(0, int(limit or 0))
    templates = []
    if GUARD_TEMPLATE_CACHE and requested > 0:
        for index in range(requested):
            templates.append(dict(GUARD_TEMPLATE_CACHE[index % len(GUARD_TEMPLATE_CACHE)]))
    if not GUARD_TEMPLATE_CACHE and requested > 0:
        warnings.warn(
            "No validated guard templates were available; guard spawning will not substitute other NPC types.",
            RuntimeWarning,
        )
    return templates


def spawn_guards_in_landing(count=15):
    templates = get_valid_guard_templates(limit=count)
    candidate_rooms = _get_patrol_rooms_for_zone(GUARD_PATROL_ZONE)
    if not candidate_rooms:
        warnings.warn("No lawful landing rooms were available for guard patrols.", RuntimeWarning)
        return []

    shuffled_rooms = list(candidate_rooms)
    random.shuffle(shuffled_rooms)
    used_room_ids = set()
    spawned = []

    room_iter = iter(shuffled_rooms)
    for template in templates:
        room = None
        for candidate_room in room_iter:
            candidate_room_id = int(getattr(candidate_room, "id", 0) or 0)
            if candidate_room_id in used_room_ids:
                continue
            if bool(getattr(getattr(candidate_room, "db", None), "no_guard", False)):
                continue
            if _count_guards_in_room(candidate_room) > 0:
                continue
            room = candidate_room
            break
        if room is None:
            break
        if int(getattr(room, "id", 0) or 0) in used_room_ids:
            continue
        if bool(getattr(getattr(room, "db", None), "no_guard", False)):
            continue
        if _count_guards_in_room(room) > 0:
            continue
        guard = create_object(
            "typeclasses.npcs.GuardNPC",
            key=GUARD_DISPLAY_NAME,
            location=room,
            home=room,
        )
        _assign_template_to_guard(guard, template, room)
        spawned.append(guard)
        used_room_ids.add(int(getattr(room, "id", 0) or 0))
        ACTIVE_GUARDS.append(guard)
        if len(spawned) >= int(count or 0):
            break

    return list(spawned)


def ensure_landing_guards(count=15):
    desired_count = max(0, int(count or 0))
    if desired_count <= 0:
        return []

    candidate_rooms = {
        int(getattr(room, "id", 0) or 0)
        for room in _get_patrol_rooms_for_zone(GUARD_PATROL_ZONE)
        if getattr(room, "id", None)
    }
    if not candidate_rooms:
        warnings.warn("No lawful landing patrol rooms were available for guard bootstrap.", RuntimeWarning)
        return []

    existing_guards = []
    seen_ids = set()
    for guard in iter_active_guards():
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id <= 0 or guard_id in seen_ids:
            continue
        guard_room = getattr(guard, "location", None)
        guard_room_id = int(getattr(guard_room, "id", 0) or 0)
        guard_zone = str(getattr(getattr(guard, "db", None), "zone", "") or "").strip().lower()
        if guard_zone == GUARD_PATROL_ZONE or guard_room_id in candidate_rooms:
            _normalize_guard_identity(guard)
            existing_guards.append(guard)
            seen_ids.add(guard_id)
            if guard not in ACTIVE_GUARDS:
                ACTIVE_GUARDS.append(guard)

    if len(existing_guards) >= desired_count:
        for guard in existing_guards:
            sync_guard_execution_mode(guard)
        return list(existing_guards)

    spawned = spawn_guards_in_landing(count=desired_count - len(existing_guards))
    combined = list(existing_guards) + list(spawned)
    for guard in combined:
        sync_guard_execution_mode(guard)
    return combined


def guard_movement_tick(guard, stats=None, force_move_override=False, source="unknown"):
    _ensure_guard_patrol_state_defaults(guard)
    if stats is not None:
        stats["patrol_reached_count"] += 1
    if is_guard_script_diagnostic_target(guard):
        _increment_guard_script_diagnostic_counter(guard, "movement_attempt_count")
        _update_guard_script_diagnostic_state(
            guard,
            last_movement_attempt_at=time.time(),
            last_movement_source=str(source),
            force_move_override=bool(force_move_override),
            last_movement_stage="entered_guard_movement_tick",
        )

    if not _is_active_guard(guard):
        if stats is not None:
            stats["failed_preconditions_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="inactive_guard", last_movement_stage="precondition_failed")
        return False

    now = time.time()
    last_move_time = float(getattr(getattr(guard, "db", None), "last_move_time", 0.0) or 0.0)
    last_idle_time = float(getattr(getattr(guard, "db", None), "last_idle_time", 0.0) or 0.0)
    force_move = bool(force_move_override or (now - last_idle_time) > GUARD_IDLE_MAX)
    if not force_move and (now - last_move_time) < GUARD_DWELL_THRESHOLD:
        if stats is not None:
            stats["failed_preconditions_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="dwell_threshold", last_movement_stage="cooldown_blocked")
        _log_guard_patrol_debug(
            f"Guard {getattr(guard, 'key', GUARD_DISPLAY_NAME)}(#{int(getattr(guard, 'id', 0) or 0)}) skipped movement: dwell"
        )
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="dwell")

    current_room = getattr(guard, "location", None)
    if current_room is None:
        if stats is not None:
            stats["failed_preconditions_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="no_current_room", last_movement_stage="precondition_failed")
        return False

    _remember_recent_room(guard, current_room)
    current_guard_count, current_guard_count_ms = _timed_guard_call(stats, "movement.current_guard_count", _count_guards_in_room, current_room)
    exits, valid_exit_ms = _timed_guard_call(stats, "movement.valid_exit_gathering", _get_valid_guard_exits, guard, current_room)
    if not exits:
        if stats is not None:
            stats["no_exit_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="no_valid_exits", last_movement_stage="exit_selection")
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="no_valid_exits")

    selected_exit, targeted_exit_ms = _timed_guard_call(stats, "movement.targeted_exit_selection", _select_targeted_exit, guard, exits)
    used_targeted_follow = selected_exit is not None
    used_backtrack_fallback = False
    if selected_exit is None:
        exit_selection_result, selector_weighting_ms = _timed_guard_call(stats, "movement.selector_weighting", _select_guard_exit, guard, exits, force_move=force_move)
        selected_exit, used_backtrack_fallback = exit_selection_result
    else:
        selector_weighting_ms = 0.0
    if selected_exit is None:
        if stats is not None:
            stats["no_exit_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="no_selected_exit", last_movement_stage="exit_selection")
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="no_selected_exit")

    destination = getattr(selected_exit, "destination", None)
    if destination is None:
        if stats is not None:
            stats["failed_preconditions_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="selected_exit_without_destination", last_movement_stage="exit_selection")
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="exit_without_destination")

    move_chance = float(GUARD_MOVE_CHANCE)
    if current_guard_count > 1:
        move_chance = min(0.9, move_chance + (0.15 * (current_guard_count - 1)))

    if not force_move and not used_targeted_follow and random.random() > move_chance:
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(guard, last_movement_reason="random_gate", last_movement_stage="random_skip")
        _log_guard_patrol_debug(
            f"Guard {getattr(guard, 'key', GUARD_DISPLAY_NAME)}(#{int(getattr(guard, 'id', 0) or 0)}) skipped movement: random gate move_chance={move_chance:.2f} current_guard_count={current_guard_count}"
        )
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="random_gate")

    prior_room_id = int(getattr(current_room, "id", 0) or 0)
    guard.db.previous_room_id = prior_room_id
    if hasattr(getattr(guard, "ndb", None), "__dict__"):
        guard.ndb.guard_tick_stats = stats
    _, departure_message_ms = _timed_guard_call(stats, "movement.msg_contents_departure", _emit_guard_departure_message, guard, selected_exit, stats=stats)
    moved = _guard_patrol_move_to(guard, destination)
    if hasattr(getattr(guard, "ndb", None), "guard_tick_stats"):
        guard.ndb.guard_tick_stats = None
    if not moved:
        if stats is not None:
            stats["failed_move_helper_count"] += 1
        _increment_guard_script_diagnostic_counter(guard, "movement_skipped_count")
        _update_guard_script_diagnostic_state(
            guard,
            last_movement_reason="guard_patrol_move_to_failed",
            last_movement_stage="move_helper_failed",
            last_selected_destination_id=int(getattr(destination, "id", 0) or 0),
        )
        return _handle_guard_idle_cycle(guard, now, stats=stats, reason="move_helper_failed")

    if stats is not None:
        stats["completed_move_count"] += 1
    _increment_guard_script_diagnostic_counter(guard, "movement_success_count")
    _update_guard_script_diagnostic_state(
        guard,
        last_movement_reason="moved",
        last_movement_stage="move_completed",
        last_selected_destination_id=int(getattr(destination, "id", 0) or 0),
        last_moved_at=now,
    )

    _remember_recent_room(guard, destination)
    guard.db.last_room_id = prior_room_id
    guard.db.previous_room_id = prior_room_id
    guard.db.last_move_time = now
    guard.db.last_idle_time = now
    direction = _get_guard_direction_label_for_exit(selected_exit)
    debug_reason = "fallback_backtrack" if used_backtrack_fallback else "moved"
    _log_guard_patrol_debug(
        f"Guard {getattr(guard, 'key', GUARD_DISPLAY_NAME)}(#{int(getattr(guard, 'id', 0) or 0)}) {debug_reason} direction={direction or 'unknown'}"
    )
    if used_targeted_follow:
        remaining = max(0, int(getattr(getattr(guard, "db", None), "follow_steps_remaining", 0) or 0) - 1)
        guard.db.follow_steps_remaining = remaining
        if remaining <= 0:
            _clear_guard_target_state(guard)

    other_guard_count, destination_guard_count_ms = _timed_guard_call(stats, "movement.destination_guard_count", _count_other_guards_in_room, guard, destination)
    if is_guard_script_diagnostic_target(guard):
        _update_guard_script_diagnostic_state(
            guard,
            last_movement_hotpath={
                "current_guard_count_ms": current_guard_count_ms,
                "valid_exit_gathering_ms": valid_exit_ms,
                "targeted_exit_selection_ms": targeted_exit_ms,
                "selector_weighting_ms": selector_weighting_ms,
                "msg_contents_departure_ms": departure_message_ms,
                "destination_guard_count_ms": destination_guard_count_ms,
                "current_guard_count": int(current_guard_count or 0),
                "other_guard_count": int(other_guard_count or 0),
                "exit_count": len(exits),
            },
        )
    if other_guard_count > 0:
        _mark_clump_exit(guard, destination)
    return True


def _guard_patrol_move_to(guard, destination):
    source_location = getattr(guard, "location", None)
    if source_location is None or destination is None or destination == source_location:
        return False
    try:
        if hasattr(source_location, "at_pre_object_leave") and source_location.at_pre_object_leave(guard, destination, move_type="patrol") is False:
            return False
        if hasattr(destination, "at_pre_object_receive") and destination.at_pre_object_receive(guard, source_location, move_type="patrol") is False:
            return False
        if hasattr(guard, "at_pre_move") and guard.at_pre_move(destination, move_type="patrol") is False:
            return False
        moved = guard.move_to(destination, quiet=True, move_type="patrol", move_hooks=False)
        if not moved:
            return False
        if hasattr(source_location, "at_object_leave"):
            source_location.at_object_leave(guard, destination, move_type="patrol")
        if hasattr(destination, "at_object_receive"):
            destination.at_object_receive(guard, source_location, move_type="patrol")
        if hasattr(guard, "at_after_move"):
            guard.at_after_move(source_location, move_type="patrol")
        if hasattr(guard, "at_post_move"):
            guard.at_post_move(source_location, move_type="patrol")
        return True
    except Exception as error:
        logger.log_trace(f"guards._guard_patrol_move_to failed for guard #{getattr(guard, 'id', '?')}: {error}")
        return False


def handle_guard_room_entry(guard, source_location=None):
    if not _is_active_guard(guard):
        return
    _ensure_guard_patrol_state_defaults(guard)
    _emit_guard_entry_message(guard, source_location=source_location)
    scan_room_for_suspicion(guard)
    current_room = getattr(guard, "location", None)
    if current_room and _count_guards_in_room(current_room) > 1:
        _mark_clump_exit(guard, current_room)


def scan_room_for_suspicion(guard):
    if not _is_active_guard(guard):
        return {}

    room = getattr(guard, "location", None)
    if room is None:
        return {}

    now = time.time()
    room_id = int(getattr(room, "id", 0) or 0)
    updated = {
        str(key): _normalize_suspicion_state(value)
        for key, value in dict(getattr(getattr(guard, "db", None), "suspicion_targets", None) or {}).items()
    }
    updated = decay_suspicion(guard, suspicion_targets=updated, now=now, persist=False)
    strongest_target = None
    for occupant in list(getattr(room, "contents", None) or []):
        try:
            if occupant == guard:
                continue
            if bool(getattr(getattr(occupant, "db", None), "is_guard", False)):
                continue
            if bool(getattr(getattr(occupant, "db", None), "is_npc", False)):
                continue
            if not getattr(occupant, "id", None):
                continue

            key = str(occupant.id)
            suspicion_state = _normalize_suspicion_state(updated.get(key))
            suspicion = int(suspicion_state.get("score", 0) or 0)
            repeat_pressure = _get_repeat_offender_pressure(occupant)
            hidden_detected = False
            evidence = 0
            if hasattr(occupant, "is_hidden") and occupant.is_hidden():
                hidden_detected = bool(hasattr(guard, "can_perceive") and guard.can_perceive(occupant))
                if hidden_detected:
                    evidence += 1
            wanted_tier = get_wanted_tier(occupant)
            if bool(getattr(getattr(occupant, "db", None), "crime_flag", False)):
                evidence += 1
            if wanted_tier == "watched":
                evidence += 1
            elif wanted_tier == "wanted":
                evidence += 2
            elif wanted_tier == "arrest_eligible":
                evidence += 3

            if evidence > 0:
                evidence += repeat_pressure
            elif hidden_detected and repeat_pressure > 0:
                evidence += repeat_pressure

            if evidence > 0:
                if (now - float(suspicion_state.get("last_seen_time", 0.0) or 0.0)) <= GUARD_TARGET_MEMORY:
                    evidence += 1
                suspicion += evidence
                suspicion_state["score"] = max(0, suspicion)
                suspicion_state["sightings"] = int(suspicion_state.get("sightings", 0) or 0) + 1
                suspicion_state["last_seen_time"] = now
                suspicion_state["last_decay_time"] = now
                suspicion_state["last_room_id"] = room_id
                suspicion_state["wanted_tier"] = wanted_tier
                suspicion_state["repeat_pressure"] = repeat_pressure
                updated[key] = suspicion_state
            elif key in updated:
                suspicion_state["wanted_tier"] = wanted_tier
                suspicion_state["repeat_pressure"] = repeat_pressure
                updated[key] = suspicion_state

            response = _get_suspicion_response(wanted_tier, int(suspicion_state.get("score", 0) or 0))
            if strongest_target is None or _is_stronger_target(suspicion_state, strongest_target["state"]):
                strongest_target = {"occupant": occupant, "state": dict(suspicion_state), "response": response}

            if response in {"watch", "arrest"}:
                _share_suspicion_with_nearby_guards(
                    guard,
                    occupant,
                    suspicion_state,
                    GUARD_SHARED_SUSPICION_ARREST if response == "arrest" else GUARD_SHARED_SUSPICION_WATCH,
                    now,
                )

            if not _guard_has_authority(guard, occupant):
                continue

            if _should_start_confrontation(wanted_tier, suspicion_state):
                begin_guard_confrontation(guard, occupant)
            elif response == "watch":
                if not _guard_owns_actor(guard, occupant):
                    guard.db.enforcement_state = "watching"
                _emit_guard_watch_message(guard, occupant, suspicion_state)
        except Exception as error:
            logger.log_trace(
                f"guards.scan_room_for_suspicion skipped occupant #{getattr(occupant, 'id', '?')} for guard #{getattr(guard, 'id', '?')}: {error}"
            )
            continue

    updated = _prune_suspicion_targets(updated, now)
    _sync_guard_target_state(guard, updated, strongest_target)
    guard.db.suspicion_targets = updated
    return updated


def _process_guard_behavior_tick_legacy(guard, stats=None, source="unknown"):
    started_perf = time.perf_counter()
    phase_timings = {}
    if is_guard_script_diagnostic_target(guard):
        _increment_guard_script_diagnostic_counter(guard, "behavior_call_count")
        _update_guard_script_diagnostic_state(
            guard,
            last_behavior_source=str(source),
            last_behavior_started_at=time.time(),
            force_move_diagnostic=bool(_guard_script_force_move_enabled()),
        )
    try:
        if not _is_active_guard(guard):
            if stats is not None:
                stats["inactive_during_tick_count"] += 1
            _update_guard_script_diagnostic_state(guard, last_behavior_result="inactive")
            _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, "inactive", stats=stats)
            return "inactive"

        _timed_guard_phase(phase_timings, "decay_suspicion_initial", decay_suspicion, guard)
        current_target = _timed_guard_phase(phase_timings, "resolve_target_initial", _resolve_guard_target_object, guard)
        if current_target is not None and _guard_owns_actor(guard, current_target):
            result = _timed_guard_phase(phase_timings, "enforcement_initial", _process_guard_enforcement, guard, current_target)
            if result in {"holding", "moving", "arrested", "released"}:
                if stats is not None:
                    stats["enforcement_count"] += 1
                _update_guard_script_diagnostic_state(guard, last_behavior_result=f"enforcement:{result}")
                _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, f"enforcement:{result}", stats=stats)
                return f"enforcement:{result}"

        if getattr(guard, "location", None) is not None:
            _timed_guard_phase(phase_timings, "scan_room_for_suspicion", scan_room_for_suspicion, guard)
            current_target = _timed_guard_phase(phase_timings, "resolve_target_post_scan", _resolve_guard_target_object, guard)
            if current_target is not None and _guard_owns_actor(guard, current_target):
                result = _timed_guard_phase(phase_timings, "enforcement_post_scan", _process_guard_enforcement, guard, current_target)
                if result in {"holding", "moving", "arrested", "released"}:
                    if stats is not None:
                        stats["enforcement_count"] += 1
                    _update_guard_script_diagnostic_state(guard, last_behavior_result=f"enforcement:{result}")
                    _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, f"enforcement:{result}", stats=stats)
                    return f"enforcement:{result}"

        moved = _timed_guard_phase(
            phase_timings,
            "movement_tick",
            guard_movement_tick,
            guard,
            stats=stats,
            force_move_override=bool(is_guard_script_diagnostic_target(guard) and _guard_script_force_move_enabled()),
            source=source,
        )
        if moved:
            if stats is not None:
                stats["moved_count"] += 1
            _update_guard_script_diagnostic_state(guard, last_behavior_result="moved")
            _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, "moved", stats=stats)
            return "moved"

        if stats is not None:
            stats["idle_count"] += 1
        _update_guard_script_diagnostic_state(guard, last_behavior_result="idle")
        _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, "idle", stats=stats)
        return "idle"
    except Exception as error:
        if stats is not None:
            stats["exception_count"] += 1
        _update_guard_script_diagnostic_state(guard, last_behavior_result="exception", last_behavior_error=str(error))
        _finalize_guard_behavior_timing(guard, source, started_perf, phase_timings, "exception", stats=stats)
        logger.log_trace(f"guards.process_guard_tick skipped guard #{getattr(guard, 'id', '?')} source={source}: {error}")
        return "exception"


# LEGACY PATH ONLY.
# Not allowed for production scheduling under DireSim.
# Only callable through explicit migration/test adapter surfaces.
def process_guard_behavior_tick(guard, stats=None, source="unknown"):
    if is_diresim_enabled() and not (_legacy_guard_test_adapter_enabled() and _legacy_guard_source_allowed(source)):
        emit_legacy_guard_tripwire(f"process_guard_behavior_tick:{source}")
        log_legacy_guard_runtime_block(f"process_guard_behavior_tick:{source}", level="error")
        return "blocked_by_diresim"
    return _process_guard_behavior_tick_legacy(guard, stats=stats, source=source)


def _run_legacy_guard_tick_loop(source="unknown"):
    global LAST_GUARD_TICK_TIME, LAST_GUARD_TICK_SUMMARY, GUARD_TICK_RUNNING

    if GUARD_TICK_RUNNING:
        summary = {
            "ok": False,
            "source": str(source),
            "skipped": "reentrant",
            "started_at": time.time(),
        }
        if _guard_patrol_debug_enabled():
            logger.log_info(f"[Guards] Re-entrant patrol tick skipped source={source}")
        LAST_GUARD_TICK_SUMMARY = summary
        return summary

    GUARD_TICK_RUNNING = True
    started_at = time.time()
    started_perf = time.perf_counter()
    LAST_GUARD_TICK_TIME = started_at
    guards, iteration_stats = _collect_active_guards_with_stats()
    summary = {
        "ok": True,
        "source": str(source),
        "started_at": started_at,
        "candidate_guard_count": int(iteration_stats["candidate_count"]),
        "active_guard_count": int(iteration_stats["active_count"]),
        "skipped_inactive_count": int(iteration_stats["skipped_inactive_count"]),
        "skipped_duplicate_count": int(iteration_stats["skipped_duplicate_count"]),
        "inactive_during_tick_count": 0,
        "enforcement_count": 0,
        "patrol_reached_count": 0,
        "idle_count": 0,
        "moved_count": 0,
        "message_count": 0,
        "no_exit_count": 0,
        "failed_preconditions_count": 0,
        "failed_move_helper_count": 0,
        "completed_move_count": 0,
        "exception_count": 0,
        "global_owned_count": 0,
        "per_guard_owned_count": 0,
        "skipped_per_guard_owned_count": 0,
    }

    _log_guard_patrol_debug(
        "Tick start "
        f"source={summary['source']} active_guards={summary['active_guard_count']} "
        f"candidate_guards={summary['candidate_guard_count']} skipped_inactive={summary['skipped_inactive_count']} "
        f"skipped_duplicate={summary['skipped_duplicate_count']}"
    )

    try:
        for guard in guards:
            if guard_has_per_guard_ownership(guard):
                summary["per_guard_owned_count"] += 1
                if source in {"global_script", "ticker", "status_fallback", "reactor_fallback"}:
                    summary["skipped_per_guard_owned_count"] += 1
                    continue
            else:
                summary["global_owned_count"] += 1
            process_guard_behavior_tick(guard, stats=summary, source=source)
    finally:
        summary["ended_at"] = time.time()
        summary["duration_ms"] = round((time.perf_counter() - started_perf) * 1000.0, 3)
        LAST_GUARD_TICK_SUMMARY = summary
        GUARD_TICK_RUNNING = False

    summary["moves_per_minute_estimate"] = round(float(summary["moved_count"]) * 60.0 / max(float(GUARD_TICK_INTERVAL), 1.0), 2)
    summary["idle_cycles_per_minute_estimate"] = round(float(summary["idle_count"]) * 60.0 / max(float(GUARD_TICK_INTERVAL), 1.0), 2)
    summary["messages_per_minute_estimate"] = round(float(summary.get("message_count", 0) or 0) * 60.0 / max(float(GUARD_TICK_INTERVAL), 1.0), 2)

    if _guard_patrol_debug_enabled():
        logger.log_info(
            "[Guards] Tick end "
            f"source={summary['source']} duration_ms={summary['duration_ms']} active_guards={summary['active_guard_count']} "
            f"global_owned={summary['global_owned_count']} per_guard_owned={summary['per_guard_owned_count']} skipped_per_guard={summary['skipped_per_guard_owned_count']} "
            f"enforcement={summary['enforcement_count']} patrol_reached={summary['patrol_reached_count']} "
            f"idle={summary['idle_count']} moved={summary['moved_count']} no_exit={summary['no_exit_count']} "
            f"messages={summary.get('message_count', 0)} move_rate={summary['moves_per_minute_estimate']} idle_rate={summary['idle_cycles_per_minute_estimate']} message_rate={summary['messages_per_minute_estimate']} "
            f"failed_preconditions={summary['failed_preconditions_count']} failed_move_helper={summary['failed_move_helper_count']} "
            f"completed_move={summary['completed_move_count']} exceptions={summary['exception_count']}"
        )

    warn_seconds = float(getattr(settings, "GUARD_TICK_WARN_SECONDS", 0.10) or 0.10)
    if summary["duration_ms"] >= (warn_seconds * 1000.0):
        logger.log_warn(
            "[Guards] Slow patrol tick "
            f"source={summary['source']} duration_ms={summary['duration_ms']} active_guards={summary['active_guard_count']} "
            f"moved={summary['moved_count']} enforcement={summary['enforcement_count']} patrol_reached={summary['patrol_reached_count']}"
        )

    return summary


def process_guard_tick(source="unknown"):
    global LAST_GUARD_TICK_SUMMARY

    if is_diresim_enabled():
        emit_legacy_guard_tripwire(f"process_guard_tick:{source}")
        summary = {
            "ok": False,
            "source": str(source),
            "skipped": "blocked_by_diresim",
            "started_at": time.time(),
            "message": LEGACY_GUARD_RUNTIME_BLOCK_MSG,
        }
        LAST_GUARD_TICK_SUMMARY = summary
        log_legacy_guard_runtime_block(f"process_guard_tick:{source}")
        return summary

    return _run_legacy_guard_tick_loop(source=source)


def run_legacy_guard_tick_for_test(source="legacy_test_adapter"):
    global LAST_GUARD_TICK_SUMMARY

    if not _legacy_guard_test_adapter_enabled():
        summary = {
            "ok": False,
            "source": str(source),
            "skipped": "legacy_test_adapter_disabled",
            "started_at": time.time(),
            "message": LEGACY_GUARD_RUNTIME_BLOCK_MSG,
        }
        LAST_GUARD_TICK_SUMMARY = summary
        if is_diresim_enabled():
            log_legacy_guard_runtime_block("run_legacy_guard_tick_for_test", level="error")
        return summary

    return _run_legacy_guard_tick_loop(source=f"legacy_test_adapter:{source}")


def get_last_guard_tick_time():
    return float(LAST_GUARD_TICK_TIME or 0.0)


def get_last_guard_tick_summary():
    return dict(LAST_GUARD_TICK_SUMMARY or {})


def _collect_active_guards_with_stats():
    seen_ids = set()
    guards = []
    stats = {
        "candidate_count": 0,
        "active_count": 0,
        "skipped_inactive_count": 0,
        "skipped_duplicate_count": 0,
    }

    def _consider_guard(guard):
        stats["candidate_count"] += 1
        guard_id = int(getattr(guard, "id", 0) or 0)
        if guard_id <= 0 or guard_id in seen_ids:
            stats["skipped_duplicate_count"] += 1
            return
        if not _is_active_guard(guard):
            stats["skipped_inactive_count"] += 1
            return
        guards.append(guard)
        seen_ids.add(guard_id)

    for guard in list(ACTIVE_GUARDS):
        _consider_guard(guard)

    for guard in ObjectDB.objects.filter(db_typeclass_path__in=GUARD_TYPECLASS_PATHS):
        _consider_guard(guard)

    stats["active_count"] = len(guards)
    return guards, stats


def iter_active_guards():
    guards, _ = _collect_active_guards_with_stats()
    return guards


def get_guard_by_id(guard_id):
    guard_id = int(guard_id or 0)
    if guard_id <= 0:
        return None
    for guard in iter_active_guards():
        if int(getattr(guard, "id", 0) or 0) == guard_id:
            return guard
    return ObjectDB.objects.filter(id=guard_id).first()


def begin_guard_confrontation(guard, actor):
    if not _is_active_guard(guard) or actor is None or not getattr(actor, "id", None):
        return False
    if not _guard_has_authority(guard, actor):
        return False
    if _guard_owns_actor(guard, actor) and str(getattr(getattr(guard, "db", None), "enforcement_state", "idle") or "idle") in {
        "confronting",
        "warning",
        "arresting",
    }:
        return True

    now = time.time()
    actor.db.active_guard_id = int(getattr(guard, "id", 0) or 0)
    actor.db.pending_arrest = True
    actor.db.justice_confrontation_started_at = now
    guard.db.current_target_id = int(getattr(actor, "id", 0) or 0)
    guard.db.current_target_name = str(getattr(actor, "key", "") or "")
    guard.db.current_target_room_id = int(getattr(getattr(actor, "location", None), "id", 0) or 0)
    guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS
    guard.db.enforcement_state = "confronting"
    guard.db.warning_count = 0
    guard.db.last_warning_time = 0.0
    guard.db.enforcement_started_at = now

    if _is_repeat_offender(actor):
        guard.db.warning_count = 2
        actor.db.justice_warning_level = max(2, int(getattr(getattr(actor, "db", None), "justice_warning_level", 0) or 0))
        actor.msg(f"{guard.key} narrows his eyes. 'You again...' ")

    actor.msg(f"{guard.key} steps in front of you. 'Hold there.'")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} steps toward {actor.key} and blocks their path.", exclude=[guard, actor])

    _advance_guard_warning(guard, actor, now=now, force=True)
    return True


def attempt_visible_arrest(guard, actor):
    if not _is_active_guard(guard) or actor is None or not _guard_owns_actor(guard, actor):
        return {"started": False, "reason": "guard does not own target"}
    allowed, reason = can_be_arrested(actor)
    if not allowed:
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=False)
        return {"started": False, "reason": str(reason or "arrest unavailable")}
    if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3 and not bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False)):
        return {"started": False, "reason": "warning ladder incomplete"}

    guard.db.enforcement_state = "arresting"
    actor.db.pending_arrest = True
    actor.msg(f"{guard.key} grabs you.")
    actor.msg("You are seized by the town watch.")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} seizes {actor.key} and takes them into custody.", exclude=[guard, actor])
    begin_arrest(actor, source=f"{guard.key} arrest", quiet=True)
    result = complete_arrest(actor, source=f"{guard.key} arrest", voluntary=False)
    release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=True, clear_flee=True)
    return {"started": True, **result}


def release_guard_enforcement(guard=None, actor=None, clear_actor=True, clear_attention=False, clear_flee=False):
    if actor is None and guard is not None:
        actor = _resolve_guard_target_object(guard)

    if guard is not None and _is_active_guard(guard):
        _clear_guard_target_state(guard)
        guard.db.enforcement_state = "idle"
        guard.db.warning_count = 0
        guard.db.last_warning_time = 0.0
        guard.db.enforcement_started_at = 0.0

    if actor is not None and clear_actor:
        owner_id = int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0)
        guard_id = int(getattr(guard, "id", 0) or 0) if guard is not None else 0
        if guard is None or owner_id in {0, guard_id}:
            actor.db.active_guard_id = None
            actor.db.pending_arrest = False
            actor.db.justice_warning_level = 0
            actor.db.justice_confrontation_started_at = 0
            if clear_attention:
                actor.db.guard_attention = False
            if clear_flee:
                actor.db.justice_flee_flag = False
    return True


def reset_guard_runtime(delete_spawned=False, refresh_templates=False):
    global GUARD_TEMPLATE_CACHE
    if delete_spawned:
        for guard in list(ACTIVE_GUARDS):
            try:
                if getattr(guard, "pk", None):
                    guard.delete()
            except Exception:
                continue
    ACTIVE_GUARDS.clear()
    if refresh_templates:
        GUARD_TEMPLATE_CACHE = []


def decay_suspicion(guard, suspicion_targets=None, now=None, persist=True):
    if not _is_active_guard(guard):
        return {}

    now = float(now or time.time())
    updated = {
        str(key): _normalize_suspicion_state(value)
        for key, value in dict(suspicion_targets or getattr(getattr(guard, "db", None), "suspicion_targets", None) or {}).items()
    }
    for key, state in list(updated.items()):
        last_decay_time = float(state.get("last_decay_time", state.get("last_seen_time", 0.0)) or 0.0)
        if last_decay_time <= 0:
            continue
        decay_steps = int(max(0.0, now - last_decay_time) // GUARD_SUSPICION_DECAY_INTERVAL)
        if decay_steps <= 0:
            continue
        state["score"] = max(0, int(state.get("score", 0) or 0) - decay_steps)
        state["last_decay_time"] = last_decay_time + (decay_steps * GUARD_SUSPICION_DECAY_INTERVAL)
        updated[str(key)] = state

    updated = _prune_suspicion_targets(updated, now)
    if persist:
        guard.db.suspicion_targets = updated
        _sync_guard_target_state(guard, updated, None)
    return updated


def _load_valid_guard_templates():
    templates = []
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT canonical_key, name, actor_type, base_health, tags_json, normalized_fields_json, source_id
            FROM canon_actors
            WHERE role = %s
            ORDER BY name
            """,
            ["guard"],
        )
        rows = cursor.fetchall()

    for canonical_key, name, actor_type, base_health, tags_json, normalized_json, source_id in rows:
        normalized_fields = _parse_json(normalized_json, {})
        tags = _parse_json(tags_json, [])
        normalized_actor_type = str(normalized_fields.get("actor_type") or actor_type or "").strip().lower()
        aggression_type = str(normalized_fields.get("aggression_type") or "").strip().lower()
        if not str(name or "").strip():
            continue
        if normalized_actor_type != "social":
            continue
        if aggression_type != "defensive":
            continue
        template_tags = list(dict.fromkeys(list(tags or []) + ["guard_validated"]))
        if "guard" not in template_tags:
            template_tags.append("guard")
        normalized_copy = dict(normalized_fields)
        normalized_copy["actor_type"] = "social"
        normalized_copy["aggression_type"] = "defensive"
        normalized_copy["tags"] = list(dict.fromkeys(list(normalized_copy.get("tags") or []) + ["guard_validated", "guard"]))
        templates.append(
            {
                "canonical_key": canonical_key,
                "template_id": str(source_id),
                "name": str(name),
                "actor_type": "social",
                "base_health": base_health,
                "tags": template_tags,
                "normalized_fields": normalized_copy,
            }
        )
    return templates


def _assign_template_to_guard(guard, template, start_room):
    _normalize_guard_identity(guard)
    guard.db.template_id = str(template.get("template_id") or template.get("canonical_key") or "")
    guard.db.template_key = str(template.get("canonical_key") or "")
    guard.db.template_name = str(template.get("name") or "")
    guard.db.is_guard = True
    guard.db.is_npc = True
    guard.db.patrol_anchor = start_room
    guard.db.patrol_radius = GUARD_DEFAULT_PATROL_RADIUS
    guard.db.last_move_time = 0.0
    guard.db.last_idle_time = time.time()
    guard.db.recent_rooms = [int(getattr(start_room, "id", 0) or 0)]
    guard.db.suspicion_targets = {}
    guard.db.guard_id = str(uuid4())
    guard_zone_id = _get_room_zone_id(start_room, fallback=GUARD_PATROL_ZONE)
    guard.db.zone = guard_zone_id
    guard.db.zone_id = guard_zone_id
    guard.db.current_target_id = None
    guard.db.current_target_name = None
    guard.db.current_target_score = 0
    guard.db.last_seen_time = 0.0
    guard.db.current_target_room_id = None
    guard.db.follow_steps_remaining = 0
    guard.db.previous_room_id = int(getattr(start_room, "id", 0) or 0)
    guard.db.last_room_id = None
    guard.db.last_message_type = None
    guard.db.last_message_id = None
    guard.db.last_message_index = None
    guard.db.last_message_time = 0.0
    guard.db.enforcement_state = "idle"
    guard.db.warning_count = 0
    guard.db.last_warning_time = 0.0
    guard.db.enforcement_started_at = 0.0
    guard.db.guard_template = {
        "canonical_key": template.get("canonical_key"),
        "name": template.get("name"),
        "base_health": template.get("base_health"),
        "tags": list(template.get("tags") or []),
    }
    if template.get("base_health"):
        guard.db.max_hp = int(template.get("base_health") or 1)
        guard.db.hp = int(template.get("base_health") or 1)


def _normalize_guard_identity(guard):
    guard.key = GUARD_DISPLAY_NAME
    guard.db.name = GUARD_DISPLAY_NAME


def _get_patrol_rooms_for_zone(zone_name):
    rooms = []
    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room").order_by("id"):
        if _allows_guard_patrol_room(room, zone_name=zone_name):
            rooms.append(room)
    return rooms


def _is_active_guard(guard):
    return bool(guard and getattr(guard, "pk", None) and bool(getattr(getattr(guard, "db", None), "is_guard", False)))


def _normalize_zone_id(value, fallback=""):
    normalized = str(value or "").strip().lower()
    if normalized:
        return normalized
    return str(fallback or "").strip().lower()


def _get_room_zone_id(room, fallback=""):
    if room is None:
        return _normalize_zone_id(fallback)
    room_db = getattr(room, "db", None)
    return _normalize_zone_id(
        getattr(room_db, "zone_id", None)
        or getattr(room_db, "zone", None)
        or getattr(room_db, "guard_zone", None)
        or getattr(room_db, "area_id", None)
        or getattr(room_db, "region", None),
        fallback=fallback,
    )


def _get_guard_zone_id(guard, fallback=GUARD_PATROL_ZONE):
    if guard is None:
        return _normalize_zone_id(fallback)
    guard_db = getattr(guard, "db", None)
    return _normalize_zone_id(
        getattr(guard_db, "zone_id", None)
        or getattr(guard_db, "zone", None)
        or _get_room_zone_id(getattr(guard, "location", None), fallback=fallback),
        fallback=fallback,
    )


def _is_guard_restricted_room(room):
    if room is None:
        return True
    room_db = getattr(room, "db", None)
    return bool(getattr(room_db, "no_npc_wander", False) or getattr(room_db, "guild_area", False))


def _is_guard_boundary_room(room):
    if room is None:
        return False
    return bool(getattr(getattr(room, "db", None), "npc_boundary", False))


def _is_guard_traversable_exit(guard, exit_obj):
    if exit_obj is None:
        return False
    destination = getattr(exit_obj, "destination", None)
    if destination is None or not getattr(destination, "pk", None):
        return False
    if bool(getattr(getattr(exit_obj, "db", None), "no_guard", False)):
        return False
    if hasattr(exit_obj, "access"):
        try:
            if exit_obj.access(guard, "traverse") is False:
                return False
        except Exception:
            return False
    return True


def _allows_guard_patrol_transition(guard, source_room, exit_obj):
    if not _is_guard_traversable_exit(guard, exit_obj):
        return False
    destination = getattr(exit_obj, "destination", None)
    guard_zone_id = _get_guard_zone_id(guard, fallback=GUARD_PATROL_ZONE)
    if not _allows_guard_patrol_room(destination, zone_name=guard_zone_id):
        return False
    if _is_guard_boundary_room(source_room):
        destination_zone_id = _get_room_zone_id(destination, fallback=guard_zone_id)
        if destination_zone_id != guard_zone_id:
            return False
        if _is_guard_restricted_room(destination):
            return False
    return True


def _is_lawful_room(room):
    if room is None:
        return False
    explicit = getattr(getattr(room, "db", None), "is_lawful", None)
    if explicit is not None:
        return bool(explicit)
    law_type = str(getattr(getattr(room, "db", None), "law_type", "standard") or "standard").strip().lower()
    return law_type != "none"


def _remember_recent_room(guard, room):
    recent = list(getattr(getattr(guard, "db", None), "recent_rooms", None) or [])
    room_id = int(getattr(room, "id", 0) or 0)
    recent = [int(entry or 0) for entry in recent if int(entry or 0) != room_id]
    recent.append(room_id)
    guard.db.recent_rooms = recent[-GUARD_RECENT_ROOM_LIMIT:]


def _split_guard_exits_by_last_room(guard, exits):
    last_room_id = int(getattr(getattr(guard, "db", None), "last_room_id", 0) or 0)
    if last_room_id <= 0:
        return list(exits), []
    preferred = []
    fallback = []
    for exit_obj in list(exits or []):
        destination = getattr(exit_obj, "destination", None)
        destination_id = int(getattr(destination, "id", 0) or 0)
        if destination_id and destination_id == last_room_id:
            fallback.append(exit_obj)
        else:
            preferred.append(exit_obj)
    return preferred, fallback


def _get_valid_guard_exits(guard, room):
    exits = []
    for obj in list(getattr(room, "contents", None) or []):
        destination = getattr(obj, "destination", None)
        if destination is None:
            continue
        if not _allows_guard_patrol_transition(guard, room, obj):
            continue
        if not _within_patrol_radius(guard, destination):
            continue
        exits.append(obj)
    return exits


def _within_patrol_radius(guard, destination):
    anchor = getattr(getattr(guard, "db", None), "patrol_anchor", None)
    radius = int(getattr(getattr(guard, "db", None), "patrol_radius", GUARD_DEFAULT_PATROL_RADIUS) or GUARD_DEFAULT_PATROL_RADIUS)
    if anchor is None or destination is None:
        return True
    return _room_distance(anchor, destination, max_depth=radius) <= radius


def _room_distance(anchor, target, max_depth=5):
    if anchor == target:
        return 0
    visited = {int(getattr(anchor, "id", 0) or 0)}
    frontier = [(anchor, 0)]
    while frontier:
        room, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for obj in list(getattr(room, "contents", None) or []):
            destination = getattr(obj, "destination", None)
            if destination is None:
                continue
            destination_id = int(getattr(destination, "id", 0) or 0)
            if destination_id in visited:
                continue
            if destination == target:
                return depth + 1
            visited.add(destination_id)
            frontier.append((destination, depth + 1))
    return max_depth + 1


def _select_guard_exit(guard, exits, force_move=False):
    if not exits:
        return None, False
    preferred_exits, fallback_exits = _split_guard_exits_by_last_room(guard, exits)
    candidate_exits = preferred_exits if preferred_exits else fallback_exits
    used_backtrack_fallback = bool(candidate_exits and not preferred_exits and fallback_exits)
    recent_history = [int(entry or 0) for entry in list(getattr(getattr(guard, "db", None), "recent_rooms", None) or [])]
    recent_rooms = set(recent_history)
    recent_recency = {room_id: index for index, room_id in enumerate(recent_history)}
    previous_room_id = int(getattr(getattr(guard, "db", None), "previous_room_id", 0) or 0)
    current_room = getattr(guard, "location", None)
    current_guard_count = _count_guards_in_room(current_room) if current_room is not None else 0
    current_room_is_boundary = _is_guard_boundary_room(current_room)
    scored = []
    non_recent = []
    for exit_obj in candidate_exits:
        destination = getattr(exit_obj, "destination", None)
        destination_id = int(getattr(destination, "id", 0) or 0)
        guard_count = _count_guards_in_room(destination)
        crowd_count = _count_non_guard_occupants(destination)
        weight = 10
        if _is_lawful_room(destination):
            weight += 5
        if destination_id not in recent_rooms:
            weight += 10
            non_recent.append(exit_obj)
        else:
            recency_index = int(recent_recency.get(destination_id, 0) or 0)
            recency_penalty = max(3, (len(recent_history) - recency_index) * 2)
            weight = max(1, weight - recency_penalty)
        if previous_room_id and destination_id == previous_room_id:
            weight = max(1, weight - 9)
        weight = max(1, weight - min(6, crowd_count))
        if guard_count > 0:
            weight = max(1, weight - (8 * guard_count))
        if current_guard_count > 1 and guard_count == 0:
            weight += min(8, 2 * (current_guard_count - 1))
        if current_room_is_boundary and _is_guard_boundary_room(destination):
            weight += 3
        scored.append((exit_obj, weight))

    pool = non_recent if non_recent else [entry[0] for entry in scored]
    weighted_pool = [(exit_obj, weight) for exit_obj, weight in scored if exit_obj in pool]
    if not weighted_pool:
        return None, used_backtrack_fallback
    if force_move:
        weighted_pool.sort(key=lambda entry: entry[1], reverse=True)
        return weighted_pool[0][0], used_backtrack_fallback

    total_weight = sum(weight for _, weight in weighted_pool)
    roll = random.uniform(0.0, float(total_weight))
    running = 0.0
    for exit_obj, weight in weighted_pool:
        running += float(weight)
        if roll <= running:
            return exit_obj, used_backtrack_fallback
    return weighted_pool[-1][0], used_backtrack_fallback


def _select_targeted_exit(guard, exits):
    target = _resolve_guard_target_object(guard)
    if target is None:
        return None

    current_room = getattr(guard, "location", None)
    target_room = getattr(target, "location", None)
    if current_room is None or target_room is None or target_room == current_room:
        return None

    for exit_obj in exits:
        if getattr(exit_obj, "destination", None) == target_room:
            return exit_obj

    viable = []
    for exit_obj in exits:
        destination = getattr(exit_obj, "destination", None)
        if destination is None:
            continue
        distance = _room_distance(destination, target_room, max_depth=2)
        if distance <= 2:
            viable.append((exit_obj, distance, _count_guards_in_room(destination)))
    if not viable:
        return None
    viable.sort(key=lambda entry: (entry[1], entry[2]))
    return viable[0][0]


def _mark_clump_exit(guard, room):
    from world.systems.scheduler import schedule_event

    now = time.time()
    guard.db.pending_clump_exit_at = now + GUARD_CLUMP_EXIT_DELAY
    guard.db.last_idle_time = min(float(getattr(guard.db, "last_idle_time", now) or now), now - GUARD_IDLE_MAX)
    schedule_event(
        key="guard_clump_exit",
        owner=guard,
        delay=GUARD_CLUMP_EXIT_DELAY,
        callback=guard_movement_tick,
        payload={"args": [guard]},
        metadata={"system": "guards", "type": "delayed_effect"},
    )


def _count_guards_in_room(room):
    return sum(1 for obj in list(getattr(room, "contents", None) or []) if bool(getattr(getattr(obj, "db", None), "is_guard", False)))


def _count_other_guards_in_room(guard, room):
    return sum(
        1
        for obj in list(getattr(room, "contents", None) or [])
        if obj != guard and bool(getattr(getattr(obj, "db", None), "is_guard", False))
    )


def _count_non_guard_occupants(room):
    return sum(
        1
        for obj in list(getattr(room, "contents", None) or [])
        if getattr(obj, "destination", None) is None and not bool(getattr(getattr(obj, "db", None), "is_guard", False))
    )


def _parse_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _allows_guard_patrol_room(room, zone_name=None):
    if room is None:
        return False
    if bool(getattr(getattr(room, "db", None), "no_guard", False)):
        return False
    if _is_guard_restricted_room(room):
        return False
    room_zone = _get_room_zone_id(room)
    guard_zone = _normalize_zone_id(getattr(getattr(room, "db", None), "guard_zone", None))
    normalized_zone_name = _normalize_zone_id(zone_name)
    if normalized_zone_name and room_zone != normalized_zone_name and guard_zone != normalized_zone_name:
        return False
    if not _is_lawful_room(room):
        return False
    patrol_flag = getattr(getattr(room, "db", None), "guard_patrol", None)
    if bool(_zone_uses_explicit_patrol(normalized_zone_name)):
        return patrol_flag is True
    return patrol_flag is not False


def _zone_uses_explicit_patrol(zone_name):
    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room"):
        room_zone = _get_room_zone_id(room)
        guard_zone = _normalize_zone_id(getattr(getattr(room, "db", None), "guard_zone", None))
        normalized_zone_name = _normalize_zone_id(zone_name)
        if normalized_zone_name and room_zone != normalized_zone_name and guard_zone != normalized_zone_name:
            continue
        if bool(getattr(getattr(room, "db", None), "guard_patrol", False)) and _is_lawful_room(room):
            return True
    return False


def _normalize_suspicion_state(value):
    if isinstance(value, Mapping):
        return {
            "score": int(value.get("score", 0) or 0),
            "sightings": int(value.get("sightings", 0) or 0),
            "last_seen_time": float(value.get("last_seen_time", 0.0) or 0.0),
            "last_decay_time": float(value.get("last_decay_time", value.get("last_seen_time", 0.0)) or 0.0),
            "last_room_id": int(value.get("last_room_id", 0) or 0),
            "wanted_tier": str(value.get("wanted_tier", "clear") or "clear"),
            "warned_at": float(value.get("warned_at", 0.0) or 0.0),
            "repeat_pressure": int(value.get("repeat_pressure", 0) or 0),
        }
    return {
        "score": int(value or 0),
        "sightings": 0,
        "last_seen_time": 0.0,
        "last_decay_time": 0.0,
        "last_room_id": 0,
        "wanted_tier": "clear",
        "warned_at": 0.0,
        "repeat_pressure": 0,
    }


def _get_repeat_offender_pressure(actor):
    crime_count = int(getattr(getattr(actor, "db", None), "crime_count", 0) or 0)
    law_reputation = int(getattr(getattr(actor, "db", None), "law_reputation", 0) or 0)
    pressure = 0
    if crime_count >= REPEAT_OFFENDER_WARNING_THRESHOLD:
        pressure += 1
    if crime_count >= 5:
        pressure += 1
    if law_reputation <= -3:
        pressure += 1
    if law_reputation <= -6:
        pressure += 1
    if law_reputation >= 3:
        pressure -= 1
    return max(0, pressure)


def _is_repeat_offender(actor):
    return _get_repeat_offender_pressure(actor) > 0


def _get_suspicion_response(wanted_tier, suspicion_score):
    tier = str(wanted_tier or "clear").strip().lower()
    score = int(suspicion_score or 0)
    if tier == "arrest_eligible":
        return "arrest"
    if tier == "wanted" and score >= (GUARD_ARREST_THRESHOLD - 1):
        return "arrest"
    if score >= GUARD_ARREST_THRESHOLD:
        return "arrest"
    if tier in {"watched", "wanted"} or score >= GUARD_WATCH_THRESHOLD:
        return "watch"
    return "ignore"


def _is_stronger_target(candidate, current):
    if current is None:
        return True
    candidate_score = int(candidate.get("score", 0) or 0)
    current_score = int(current.get("score", 0) or 0)
    if candidate_score != current_score:
        return candidate_score > current_score
    return float(candidate.get("last_seen_time", 0.0) or 0.0) > float(current.get("last_seen_time", 0.0) or 0.0)


def _prune_suspicion_targets(updated, now):
    pruned = {}
    for key, value in updated.items():
        state = _normalize_suspicion_state(value)
        age = now - float(state.get("last_seen_time", 0.0) or 0.0)
        if age > GUARD_TARGET_MEMORY:
            continue
        if int(state.get("score", 0) or 0) <= 0:
            continue
        pruned[str(key)] = state
    return pruned


def _sync_guard_target_state(guard, updated, strongest_target):
    if strongest_target is not None:
        occupant = strongest_target.get("occupant")
        state = _normalize_suspicion_state(strongest_target.get("state"))
        response = _get_suspicion_response(state.get("wanted_tier"), int(state.get("score", 0) or 0))
        guard.db.current_target_id = int(getattr(occupant, "id", 0) or 0)
        guard.db.current_target_name = str(getattr(occupant, "key", "") or "")
        guard.db.current_target_score = int(state.get("score", 0) or 0)
        guard.db.last_seen_time = float(state.get("last_seen_time", 0.0) or 0.0)
        guard.db.current_target_room_id = int(state.get("last_room_id", 0) or 0)
        if not _guard_owns_actor(guard, occupant):
            guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS if response in {"watch", "arrest"} else 0
        return

    best_key = None
    best_state = None
    for key, state in updated.items():
        normalized = _normalize_suspicion_state(state)
        if _is_stronger_target(normalized, best_state):
            best_key = str(key)
            best_state = normalized

    if best_key is None or best_state is None:
        _clear_guard_target_state(guard)
        return

    target = ObjectDB.objects.filter(id=int(best_key or 0)).first()
    guard.db.current_target_id = int(best_key or 0)
    guard.db.current_target_name = str(getattr(target, "key", "") or guard.db.current_target_name or "")
    guard.db.current_target_score = int(best_state.get("score", 0) or 0)
    guard.db.last_seen_time = float(best_state.get("last_seen_time", 0.0) or 0.0)
    guard.db.current_target_room_id = int(best_state.get("last_room_id", 0) or 0)
    if not _guard_owns_actor(guard, target):
        guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS if _get_suspicion_response(best_state.get("wanted_tier"), int(best_state.get("score", 0) or 0)) in {"watch", "arrest"} else 0


def _get_current_guard_target(guard):
    target = _resolve_guard_target_object(guard)
    if target is None:
        return None
    score = int(getattr(getattr(guard, "db", None), "current_target_score", 0) or 0)
    wanted_tier = get_wanted_tier(target)
    return {
        "target": target,
        "score": score,
        "response": _get_suspicion_response(wanted_tier, score),
        "wanted_tier": wanted_tier,
    }


def _resolve_guard_target_object(guard):
    target_id = int(getattr(getattr(guard, "db", None), "current_target_id", 0) or 0)
    last_seen = float(getattr(getattr(guard, "db", None), "last_seen_time", 0.0) or 0.0)
    if target_id <= 0:
        return None
    if last_seen > 0 and (time.time() - last_seen) > GUARD_TARGET_MEMORY:
        _clear_guard_target_state(guard)
        return None
    return ObjectDB.objects.filter(id=target_id).first()


def _emit_guard_watch_message(guard, target, suspicion_state):
    if not _guard_has_authority(guard, target):
        return
    now = time.time()
    last_message = float(getattr(getattr(target, "db", None), "last_guard_watch_message_at", 0.0) or 0.0)
    if last_message and (now - last_message) < GUARD_WATCH_MESSAGE_COOLDOWN:
        return
    target.db.last_guard_watch_message_at = now
    target.msg(f"{guard.key} watches you closely.")
    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(
            f"{guard.key} slows and keeps a close eye on {target.key}.",
            exclude=[guard, target],
        )


def _share_suspicion_with_nearby_guards(guard, target, suspicion_state, amount, now):
    for other_guard in _iter_nearby_guards(guard):
        if other_guard == guard or not _is_active_guard(other_guard):
            continue
        other_targets = {
            str(key): _normalize_suspicion_state(value)
            for key, value in dict(getattr(getattr(other_guard, "db", None), "suspicion_targets", None) or {}).items()
        }
        key = str(getattr(target, "id", 0) or 0)
        if not key:
            continue
        other_state = _normalize_suspicion_state(other_targets.get(key))
        other_state["score"] = max(int(other_state.get("score", 0) or 0), int(suspicion_state.get("score", 0) or 0) - 1)
        other_state["score"] = max(0, int(other_state.get("score", 0) or 0) + int(amount or 0))
        other_state["sightings"] = max(int(other_state.get("sightings", 0) or 0), 1)
        other_state["last_seen_time"] = now
        other_state["last_decay_time"] = now
        other_state["last_room_id"] = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
        other_state["wanted_tier"] = str(suspicion_state.get("wanted_tier", "clear") or "clear")
        if float(other_state.get("warned_at", 0.0) or 0.0) <= 0 and float(suspicion_state.get("warned_at", 0.0) or 0.0) > 0:
            other_state["warned_at"] = float(suspicion_state.get("warned_at", 0.0) or 0.0)
        other_targets[key] = other_state
        other_targets = _prune_suspicion_targets(other_targets, now)
        other_guard.db.suspicion_targets = other_targets
        _sync_guard_target_state(other_guard, other_targets, None)


def _iter_nearby_guards(guard):
    current_room = getattr(guard, "location", None)
    if current_room is None:
        return []
    seen_ids = set()
    nearby = []
    for obj in list(getattr(current_room, "contents", None) or []):
        if obj != guard and _is_active_guard(obj):
            nearby.append(obj)
            seen_ids.add(int(getattr(obj, "id", 0) or 0))
    for exit_obj in list(getattr(current_room, "contents", None) or []):
        destination = getattr(exit_obj, "destination", None)
        if destination is None:
            continue
        for obj in list(getattr(destination, "contents", None) or []):
            obj_id = int(getattr(obj, "id", 0) or 0)
            if obj != guard and obj_id not in seen_ids and _is_active_guard(obj):
                nearby.append(obj)
                seen_ids.add(obj_id)
    return nearby


def _clear_guard_target_state(guard):
    guard.db.current_target_id = None
    guard.db.current_target_name = None
    guard.db.current_target_score = 0
    guard.db.last_seen_time = 0.0
    guard.db.current_target_room_id = None
    guard.db.follow_steps_remaining = 0


def _guard_has_authority(guard, actor):
    owner_id = int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0)
    guard_id = int(getattr(guard, "id", 0) or 0)
    return owner_id in {0, guard_id}


def _guard_owns_actor(guard, actor):
    return int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0) == int(getattr(guard, "id", 0) or 0)


def _should_start_confrontation(wanted_tier, suspicion_state):
    score = int((suspicion_state or {}).get("score", 0) or 0)
    tier = str(wanted_tier or "clear").strip().lower()
    repeat_pressure = int((suspicion_state or {}).get("repeat_pressure", 0) or 0)
    threshold = max(1, GUARD_ARREST_THRESHOLD - min(2, repeat_pressure))
    return score >= threshold or tier in {"wanted", "arrest_eligible"}


def _process_guard_enforcement(guard, actor):
    if actor is None:
        release_guard_enforcement(guard=guard, clear_actor=False)
        return "released"
    if bool(getattr(getattr(actor, "db", None), "detained", False)):
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=True, clear_flee=True)
        return "arrested"
    if not _guard_owns_actor(guard, actor):
        release_guard_enforcement(guard=guard, clear_actor=False)
        return "released"

    target_room = getattr(actor, "location", None)
    guard_room = getattr(guard, "location", None)
    if not _allows_guard_patrol_room(target_room, zone_name=_get_guard_zone_id(guard, fallback=GUARD_PATROL_ZONE)):
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"
    if target_room is None or guard_room is None:
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"

    if target_room != guard_room:
        if int(getattr(getattr(guard, "db", None), "follow_steps_remaining", 0) or 0) > 0:
            moved = guard_movement_tick(guard)
            return "moving" if moved else "holding"
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True)
        return "released"

    now = time.time()
    guard.db.last_idle_time = now
    if str(getattr(getattr(guard, "db", None), "enforcement_state", "idle") or "idle") == "watching":
        begin_guard_confrontation(guard, actor)
        return "holding"

    if bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False)):
        if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3:
            guard.db.warning_count = 2
            guard.db.last_warning_time = 0.0
        if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
            if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 3:
                attempt_visible_arrest(guard, actor)
            else:
                _advance_guard_warning(guard, actor, now=now, force=True)
        return "holding"

    elapsed = now - float(getattr(getattr(actor, "db", None), "justice_confrontation_started_at", 0.0) or now)
    if _is_repeat_offender(actor) and int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 2:
        if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
            attempt_visible_arrest(guard, actor)
        return "holding"
    if elapsed >= GUARD_CONFRONT_TIMEOUT and int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) < 3:
        _advance_guard_warning(guard, actor, now=now, force=True)
        return "holding"

    if (now - float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)) >= GUARD_WARNING_COOLDOWN:
        if int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) >= 3:
            attempt_visible_arrest(guard, actor)
        else:
            _advance_guard_warning(guard, actor, now=now, force=True)
    return "holding"


def _advance_guard_warning(guard, actor, now=None, force=False):
    if not _guard_owns_actor(guard, actor):
        return False
    now = float(now or time.time())
    last_warning_time = float(getattr(getattr(guard, "db", None), "last_warning_time", 0.0) or 0.0)
    if not force and (now - last_warning_time) < GUARD_WARNING_COOLDOWN:
        return False

    next_stage = min(4, int(getattr(getattr(guard, "db", None), "warning_count", 0) or 0) + 1)
    guard.db.warning_count = next_stage
    guard.db.last_warning_time = now
    guard.db.enforcement_state = "warning"
    actor.db.justice_warning_level = min(3, next_stage)
    actor.db.pending_arrest = True
    guard.db.follow_steps_remaining = GUARD_MAX_FOLLOW_STEPS

    if next_stage == 1:
        actor.msg(f"{guard.key} eyes you suspiciously.")
    elif next_stage == 2:
        actor.msg(f"{guard.key} says, 'You are being watched.'")
    elif next_stage == 3:
        actor.msg(f"{guard.key} says, 'Surrender now or face arrest.'")
    else:
        return attempt_visible_arrest(guard, actor)

    room = getattr(guard, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"{guard.key} keeps {actor.key} under open scrutiny.", exclude=[guard, actor])
    return True


