"""
DireEngine weather system (Layer 1: ambient state).

Per-zone weather state with climate-driven plausibility and
season-aware Markov transitions. Reads season from world.calendar;
weather progresses on its own tick independent of the calendar.

Public API:
  get_current_weather(zone_id) -> str
  set_current_weather(zone_id, value, *, source="admin")
  get_weather_state() -> dict
  is_weather_plausible_for_climate(weather, climate) -> bool
  resolve_climate(freeform_value) -> str
  tick_weather()  # called by scheduler
    run_weather_cycle()  # tick + live broadcast side effects

Storage: WeatherScript singleton Evennia global script with
per-zone state in attributes. Survives restarts.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import datetime
import random

import yaml
from django.conf import settings
from evennia.scripts.models import ScriptDB
from evennia import search_script
from evennia.utils import logger
from zoneinfo import ZoneInfo

from typeclasses.scripts import Script
from world.builder.prompting.room_description_prompt import _THRESHOLD_STRUCTURES, determine_applicable_state_groups
from world.builder.schemas.room_tag_schema import normalize_room_tags
from world.builder.services.map_exporter import _rooms_for_zone as _query_rooms_for_zone
from world.calendar import get_current_season


CLIMATES = (
    "temperate",
    "coastal",
    "tropical",
    "arid",
    "boreal",
    "alpine",
    "subarctic",
    "continental",
)

WEATHER_STATES = (
    "clear",
    "cloudy",
    "light_rain",
    "heavy_rain",
    "storm",
    "fog",
    "light_snow",
    "heavy_snow",
    "blizzard",
    "sandstorm",
)

DEFAULT_WEATHER = "clear"
WEATHER_SCRIPT_KEY = "global_weather"
WEATHER_SCRIPT_PATH = "world.weather.WeatherScript"
_WEATHER_STATE_PREFIX = "weather_state__"
_WEATHER_META_PREFIX = "weather_meta__"
_CONTENT_DIR = Path(__file__).resolve().parent / "content"
_COMPATIBILITY_PATH = _CONTENT_DIR / "climate_weather_compatibility.yaml"
_KEYWORDS_PATH = _CONTENT_DIR / "climate_keywords.yaml"
_TRANSITIONS_PATH = _CONTENT_DIR / "weather_transitions.yaml"
_TRANSITION_MESSAGES_PATH = _CONTENT_DIR / "weather_transition_messages.yaml"
_LIGHTNING_MESSAGES_PATH = _CONTENT_DIR / "weather_lightning_messages.yaml"
_AMBIENT_MESSAGES_PATH = _CONTENT_DIR / "weather_ambient_messages.yaml"
_ZONE_DIR = Path(__file__).resolve().parents[1] / "worlddata" / "zones"
_FALLBACK_WARNED_VALUES: set[str] = set()
_ZONE_ROOM_CACHE: dict[str, list[object]] = {}
_ZONE_ELIGIBLE_CACHE: dict[str, list[tuple[object, bool]]] = {}
_ZONE_PAYLOAD_CACHE: dict[str, dict] = {}
_ZONE_PAYLOAD_LIST_CACHE: list[dict] | None = None


def invalidate_zone_caches(zone_id: str | None = None) -> None:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        _ZONE_ROOM_CACHE.clear()
        _ZONE_ELIGIBLE_CACHE.clear()
        _ZONE_PAYLOAD_CACHE.clear()
        global _ZONE_PAYLOAD_LIST_CACHE
        _ZONE_PAYLOAD_LIST_CACHE = None
        return
    _ZONE_ROOM_CACHE.pop(normalized_zone_id, None)
    _ZONE_ELIGIBLE_CACHE.pop(normalized_zone_id, None)
    _ZONE_PAYLOAD_CACHE.pop(normalized_zone_id, None)
    _ZONE_PAYLOAD_LIST_CACHE = None


def _calendar_tz() -> ZoneInfo:
    name = str(getattr(settings, "CALENDAR_TIMEZONE", "UTC") or "UTC").strip() or "UTC"
    return ZoneInfo(name)


def _now() -> datetime.datetime:
    return datetime.datetime.now(tz=_calendar_tz())


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_climate_compatibility() -> dict[str, frozenset[str]]:
    payload = _load_yaml(_COMPATIBILITY_PATH)
    if not isinstance(payload, dict):
        raise ValueError("climate weather compatibility must be a mapping.")
    compatibility: dict[str, frozenset[str]] = {}
    for climate in CLIMATES:
        values = payload.get(climate) or []
        normalized = [str(value or "").strip().lower() for value in values if str(value or "").strip()]
        compatibility[climate] = frozenset(normalized)
    return compatibility


def _load_climate_keywords() -> list[tuple[str, str]]:
    payload = _load_yaml(_KEYWORDS_PATH)
    if not isinstance(payload, dict):
        raise ValueError("climate keywords must be a mapping.")
    keywords: list[tuple[str, str]] = []
    for bucket, values in payload.items():
        climate = str(bucket or "").strip().lower()
        if climate not in CLIMATES:
            continue
        for value in values or []:
            keyword = str(value or "").strip().lower()
            if keyword:
                keywords.append((keyword, climate))
    return keywords


def _load_transition_matrices() -> dict[str, dict[str, dict[str, float]]]:
    payload = _load_yaml(_TRANSITIONS_PATH)
    if not isinstance(payload, dict):
        raise ValueError("weather transitions must be a mapping.")
    matrices: dict[str, dict[str, dict[str, float]]] = {}
    for matrix_key, matrix_payload in payload.items():
        rows_payload = dict(matrix_payload or {}) if isinstance(matrix_payload, dict) else {}
        rows: dict[str, dict[str, float]] = {}
        for current_state, targets_payload in rows_payload.items():
            targets = dict(targets_payload or {}) if isinstance(targets_payload, dict) else {}
            normalized_targets: dict[str, float] = {}
            for target_state, weight in targets.items():
                target = str(target_state or "").strip().lower()
                if not target:
                    continue
                try:
                    normalized_targets[target] = float(weight)
                except (TypeError, ValueError):
                    continue
            current = str(current_state or "").strip().lower()
            if current:
                rows[current] = normalized_targets
        matrices[str(matrix_key or "").strip().lower()] = rows
    return matrices


def _load_transition_messages() -> dict[str, dict[str, str]]:
    payload = _load_yaml(_TRANSITION_MESSAGES_PATH)
    if not isinstance(payload, dict):
        raise ValueError("weather transition messages must be a mapping.")
    messages: dict[str, dict[str, str]] = {}
    for key, variants in payload.items():
        variant_payload = dict(variants or {}) if isinstance(variants, dict) else {}
        messages[str(key or "").strip().lower()] = {
            "outdoor": str(variant_payload.get("outdoor") or "").strip(),
            "threshold": str(variant_payload.get("threshold") or "").strip(),
        }
    return messages


def _load_lightning_messages() -> dict[str, list[str]]:
    payload = _load_yaml(_LIGHTNING_MESSAGES_PATH)
    if not isinstance(payload, dict):
        raise ValueError("weather lightning messages must be a mapping.")
    messages: dict[str, list[str]] = {}
    for key, values in payload.items():
        messages[str(key or "").strip().lower()] = [
            str(value or "").strip() for value in list(values or []) if str(value or "").strip()
        ]
    return messages


def _load_ambient_messages() -> dict[str, dict[str, list[str]]]:
    payload = _load_yaml(_AMBIENT_MESSAGES_PATH)
    if not isinstance(payload, dict):
        raise ValueError("weather ambient messages must be a mapping.")
    messages: dict[str, dict[str, list[str]]] = {}
    for raw_climate, raw_states in payload.items():
        climate = str(raw_climate or "").strip().lower()
        if climate not in CLIMATES:
            continue
        state_payload = dict(raw_states or {}) if isinstance(raw_states, dict) else {}
        normalized_states: dict[str, list[str]] = {}
        for raw_state, raw_messages in state_payload.items():
            state = str(raw_state or "").strip().lower()
            if state not in WEATHER_STATES:
                continue
            normalized_states[state] = [
                str(value or "").strip() for value in list(raw_messages or []) if str(value or "").strip()
            ]
        messages[climate] = normalized_states
    return messages


_CLIMATE_COMPATIBILITY = _load_climate_compatibility()
_CLIMATE_KEYWORDS = _load_climate_keywords()
_TRANSITION_MATRICES = _load_transition_matrices()
_TRANSITION_MESSAGES = _load_transition_messages()
_LIGHTNING_MESSAGES = _load_lightning_messages()
_AMBIENT_MESSAGES = _load_ambient_messages()


def _atmospheric_tick_interval_seconds() -> float:
    return max(1.0, float(getattr(settings, "WEATHER_ATMOSPHERIC_TICK_INTERVAL_SECONDS", 240) or 240))


def _weather_state_tick_ratio() -> int:
    try:
        ratio = int(getattr(settings, "WEATHER_STATE_TICK_RATIO", 5) or 5)
    except (TypeError, ValueError):
        ratio = 5
    return max(1, ratio)


def _ambient_broadcast_probability() -> float:
    try:
        value = float(getattr(settings, "WEATHER_AMBIENT_BROADCAST_PROBABILITY", 0.4) or 0.4)
    except (TypeError, ValueError):
        value = 0.4
    return max(0.0, min(1.0, value))


def _state_tick_interval_game_seconds() -> int:
    time_factor = max(0.0001, float(getattr(settings, "TIME_FACTOR", 1.0) or 1.0))
    return int(round(_atmospheric_tick_interval_seconds() * _weather_state_tick_ratio() * time_factor))


def resolve_climate(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        fallback_key = "(missing climate)"
        if fallback_key not in _FALLBACK_WARNED_VALUES:
            _FALLBACK_WARNED_VALUES.add(fallback_key)
            logger.log_warn("[Weather] Missing climate value; defaulting to temperate.")
        return "temperate"
    if text in CLIMATES:
        return text
    for keyword, bucket in _CLIMATE_KEYWORDS:
        if keyword in text:
            return bucket
    if text not in _FALLBACK_WARNED_VALUES:
        _FALLBACK_WARNED_VALUES.add(text)
        logger.log_warn(f"[Weather] Unresolvable climate '{text}', defaulting to temperate.")
    return "temperate"


def is_weather_plausible_for_climate(weather: str, climate: str) -> bool:
    normalized_weather = str(weather or "").strip().lower()
    normalized_climate = resolve_climate(climate)
    return normalized_weather in _CLIMATE_COMPATIBILITY.get(normalized_climate, frozenset())


def _normalized_transition_row(matrix: dict[str, dict[str, float]], current_state: str, climate: str) -> dict[str, float]:
    current = str(current_state or DEFAULT_WEATHER).strip().lower() or DEFAULT_WEATHER
    normalized_climate = resolve_climate(climate)
    row = dict(matrix.get(current) or {})
    plausible_targets = _CLIMATE_COMPATIBILITY.get(normalized_climate, frozenset({DEFAULT_WEATHER}))
    filtered = {
        target: max(0.0, float(weight or 0.0))
        for target, weight in row.items()
        if target in plausible_targets and float(weight or 0.0) > 0.0
    }
    if not filtered:
        fallback_state = current if current in plausible_targets else DEFAULT_WEATHER
        return {fallback_state: 1.0}
    total = sum(filtered.values())
    if total <= 0:
        fallback_state = current if current in plausible_targets else DEFAULT_WEATHER
        return {fallback_state: 1.0}
    return {target: weight / total for target, weight in filtered.items()}


def _pick_next_state(current: str, climate: str, season: str, *, rng=None) -> str:
    random_source = rng or random.Random()
    normalized_climate = resolve_climate(climate)
    normalized_season = str(season or "").strip().lower()
    matrix_key = f"{normalized_climate}__{normalized_season}"
    matrix = _TRANSITION_MATRICES.get(matrix_key, {})
    probabilities = _normalized_transition_row(matrix, current, normalized_climate)
    roll = random_source.random()
    running = 0.0
    last_state = DEFAULT_WEATHER
    for target, probability in probabilities.items():
        last_state = target
        running += probability
        if roll <= running:
            return target
    return last_state


def _iter_zone_payloads() -> list[dict]:
    global _ZONE_PAYLOAD_LIST_CACHE
    if _ZONE_PAYLOAD_LIST_CACHE is not None:
        return list(_ZONE_PAYLOAD_LIST_CACHE)

    payloads: list[dict] = []
    payload_map: dict[str, dict] = {}
    for file_path in sorted(_ZONE_DIR.glob("*.yaml")):
        try:
            payload = _load_yaml(file_path)
        except Exception as error:
            logger.log_warn(f"[Weather] Failed to load zone YAML {file_path.name}: {error}")
            continue
        if not isinstance(payload, dict):
            continue
        zone_id = str(payload.get("zone_id") or file_path.stem).strip()
        if not zone_id:
            continue
        normalized_payload = {**payload, "zone_id": zone_id}
        payloads.append(normalized_payload)
        payload_map[zone_id] = normalized_payload
    _ZONE_PAYLOAD_LIST_CACHE = payloads
    _ZONE_PAYLOAD_CACHE.clear()
    _ZONE_PAYLOAD_CACHE.update(payload_map)
    return list(payloads)


def _get_zone_payload(zone_id: str) -> dict | None:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return None
    cached = _ZONE_PAYLOAD_CACHE.get(normalized_zone_id)
    if cached is not None:
        return cached
    _iter_zone_payloads()
    return _ZONE_PAYLOAD_CACHE.get(normalized_zone_id)


def _zone_climate_text(zone_payload: dict | None) -> str | None:
    payload = dict(zone_payload or {})
    generation_context = dict(payload.get("generation_context") or {})
    raw = generation_context.get("climate")
    text = str(raw or "").strip()
    return text or None


def _zone_climate(zone_id: str) -> str:
    return resolve_climate(_zone_climate_text(_get_zone_payload(zone_id)))


def _find_scripts_by_key(script_key: str) -> list:
    if callable(search_script):
        try:
            return list(search_script(script_key) or [])
        except Exception:
            pass
    try:
        return list(ScriptDB.objects.filter(db_key=script_key))
    except Exception:
        return []


def _get_weather_script() -> WeatherScript | None:
    existing = []
    for script in _find_scripts_by_key(WEATHER_SCRIPT_KEY):
        if getattr(script, "typeclass_path", "") == WEATHER_SCRIPT_PATH:
            existing.append(script)

    keeper = existing[0] if existing else None
    for duplicate in existing[1:]:
        try:
            duplicate.delete()
        except Exception:
            pass

    if keeper is not None:
        try:
            if not bool(getattr(keeper, "is_active", False)):
                keeper.start()
        except Exception as error:
            logger.log_trace(f"[Weather] Failed to start existing WeatherScript: {error}")
        return keeper
    return None


def _recorded_weather_states(script) -> dict[str, str]:
    _ensure_state_cache_loaded(script)
    return dict(getattr(script, "_weather_state_cache", {}))


def _state_key(zone_id: str) -> str:
    return f"{_WEATHER_STATE_PREFIX}{str(zone_id or '').strip()}"


def _meta_key(zone_id: str) -> str:
    return f"{_WEATHER_META_PREFIX}{str(zone_id or '').strip()}"


def _load_script_attribute_map(script, prefix: str) -> dict[str, object]:
    values: dict[str, object] = {}
    rows = list(script.db_attributes.filter(db_key__startswith=prefix).order_by("db_key"))
    for attr in rows:
        key = str(getattr(attr, "key", "") or getattr(attr, "db_key", "") or "")
        zone_id = key[len(prefix):].strip()
        if not zone_id:
            continue
        values[zone_id] = getattr(attr, "value", None)
    return values


def _reset_state_cache(script) -> None:
    setattr(script, "_weather_state_cache", {})
    setattr(script, "_weather_meta_cache", {})
    setattr(script, "_weather_state_cache_loaded", False)


def _ensure_state_cache_loaded(script) -> None:
    if bool(getattr(script, "_weather_state_cache_loaded", False)):
        return

    state_cache: dict[str, str] = {}
    for zone_id, value in _load_script_attribute_map(script, _WEATHER_STATE_PREFIX).items():
        normalized_value = str(value or DEFAULT_WEATHER).strip().lower() or DEFAULT_WEATHER
        state_cache[zone_id] = normalized_value if normalized_value in WEATHER_STATES else DEFAULT_WEATHER

    meta_cache: dict[str, dict] = {}
    for zone_id, value in _load_script_attribute_map(script, _WEATHER_META_PREFIX).items():
        meta_cache[zone_id] = dict(value) if isinstance(value, dict) else {}

    setattr(script, "_weather_state_cache", state_cache)
    setattr(script, "_weather_meta_cache", meta_cache)
    setattr(script, "_weather_state_cache_loaded", True)


def get_current_weather(zone_id: str) -> str:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return DEFAULT_WEATHER
    script = _get_weather_script()
    if script is None:
        return DEFAULT_WEATHER
    _ensure_state_cache_loaded(script)
    value = str(getattr(script, "_weather_state_cache", {}).get(normalized_zone_id, DEFAULT_WEATHER) or DEFAULT_WEATHER).strip().lower()
    return value if value in WEATHER_STATES else DEFAULT_WEATHER


def get_ambient_message(climate: str, weather_state: str, *, rng=None) -> str:
    normalized_climate = str(climate or "").strip().lower()
    normalized_state = str(weather_state or "").strip().lower()
    if normalized_climate not in CLIMATES:
        return ""
    messages = _AMBIENT_MESSAGES.get(normalized_climate, {}).get(normalized_state, [])
    if not messages:
        return ""
    random_source = rng or random
    return str(random_source.choice(messages) or "").strip()


def set_current_weather(zone_id: str, value: str, *, source: str = "admin") -> None:
    normalized_zone_id = str(zone_id or "").strip()
    normalized_value = str(value or "").strip().lower()
    if not normalized_zone_id:
        raise ValueError("zone_id is required.")
    if normalized_value not in WEATHER_STATES:
        raise ValueError(f"Unknown weather state: {value}")
    script = _get_weather_script()
    if script is None:
        return
    _ensure_state_cache_loaded(script)
    getattr(script, "_weather_state_cache", {})[normalized_zone_id] = normalized_value
    getattr(script, "_weather_meta_cache", {})[normalized_zone_id] = {
        "source": str(source or "admin"),
        "updated_at": _now_iso(),
    }
    script.attributes.add(_state_key(normalized_zone_id), normalized_value)
    script.attributes.add(_meta_key(normalized_zone_id), getattr(script, "_weather_meta_cache", {})[normalized_zone_id])


def get_weather_state() -> dict:
    script = _get_weather_script()
    if script is None:
        return {
            "zones": [],
            "counts": {},
            "tick_interval_game_seconds": _state_tick_interval_game_seconds(),
            "lightning_probability": float(getattr(settings, "WEATHER_LIGHTNING_PROBABILITY_PER_TICK", 0.5) or 0.5),
            "last_tick": None,
            "next_tick": None,
            "season": get_current_season(),
            "climate_fallback_zones": [],
        }
    _ensure_state_cache_loaded(script)
    recorded_states = _recorded_weather_states(script)
    payloads = {str(payload.get("zone_id") or "").strip(): payload for payload in _iter_zone_payloads()}
    zone_ids = sorted({zone_id for zone_id in payloads.keys() if zone_id} | set(recorded_states.keys()))
    zones = []
    counts = Counter()
    fallback_zones = []
    current_season = get_current_season()
    for zone_id in zone_ids:
        payload = payloads.get(zone_id)
        climate_text = _zone_climate_text(payload)
        resolved_climate = resolve_climate(climate_text)
        state = recorded_states.get(zone_id, DEFAULT_WEATHER)
        counts[state] += 1
        if (climate_text is None or resolved_climate == "temperate") and str(climate_text or "").strip().lower() not in {"temperate"}:
            fallback_zones.append({"zone_id": zone_id, "climate": climate_text})
        zones.append(
            {
                "zone_id": zone_id,
                "name": str((payload or {}).get("name") or zone_id),
                "weather": state,
                "climate": resolved_climate,
                "raw_climate": climate_text,
                "plausible": is_weather_plausible_for_climate(state, resolved_climate),
                "season": current_season,
            }
        )
    next_tick_seconds = None
    try:
        next_tick_seconds = float(script.time_until_next_repeat())
    except Exception:
        next_tick_seconds = None
    next_tick_iso = None
    if next_tick_seconds is not None:
        next_tick_iso = (_now() + datetime.timedelta(seconds=max(0.0, next_tick_seconds))).isoformat(timespec="seconds")
    result = {
        "zones": zones,
        "counts": dict(sorted(counts.items())),
        "tick_interval_game_seconds": _state_tick_interval_game_seconds(),
        "lightning_probability": float(getattr(settings, "WEATHER_LIGHTNING_PROBABILITY_PER_TICK", 0.5) or 0.5),
        "last_tick": getattr(script.db, "last_tick_iso", None),
        "next_tick": next_tick_iso,
        "season": current_season,
        "climate_fallback_zones": fallback_zones,
    }
    return result


def tick_weather() -> dict[str, tuple[str, str]]:
    script = _get_weather_script()
    if script is None:
        return {}
    season = get_current_season()
    transitions: dict[str, tuple[str, str]] = {}
    _ensure_state_cache_loaded(script)
    payloads = {str(payload.get("zone_id") or "").strip(): payload for payload in _iter_zone_payloads()}
    recorded_zone_ids = set(_recorded_weather_states(script).keys())
    zone_ids = sorted({zone_id for zone_id in payloads.keys() if zone_id} | recorded_zone_ids)
    for zone_id in zone_ids:
        payload = payloads.get(zone_id)
        climate = resolve_climate(_zone_climate_text(payload))
        current = get_current_weather(zone_id)
        next_state = _pick_next_state(current, climate, season)
        if next_state != current:
            set_current_weather(zone_id, next_state, source="tick")
            transitions[zone_id] = (current, next_state)
    script.db.last_tick_iso = _now_iso()
    return transitions


def run_weather_cycle(*, rng=None) -> dict[str, tuple[str, str]]:
    transitions = tick_weather()

    for zone_id, (old, new) in transitions.items():
        _broadcast_weather_transition(zone_id, old, new)

    probability = float(getattr(settings, "WEATHER_LIGHTNING_PROBABILITY_PER_TICK", 0.5) or 0.5)
    random_source = rng or random
    for zone in get_weather_state().get("zones", []):
        if str(zone.get("weather") or "") != "storm":
            continue
        if random_source.random() <= probability:
            _broadcast_storm_lightning(str(zone.get("zone_id") or ""), rng=rng)
    return transitions


def _broadcast_weather_ambient(zone_id: str, message: str) -> bool:
    sent = False
    for room, _is_threshold in list(_eligible_rooms_for_zone(zone_id)):
        _broadcast_message(room, message)
        sent = True
    return sent


def run_atmospheric_tick(*, rng=None, skip_zone_ids: set[str] | None = None) -> list[str]:
    script = _get_weather_script()
    if script is None:
        return []

    _ensure_state_cache_loaded(script)
    random_source = rng or random
    skip = {str(zone_id or "").strip() for zone_id in (skip_zone_ids or set()) if str(zone_id or "").strip()}
    ambient_probability = _ambient_broadcast_probability()
    recorded_states = _recorded_weather_states(script)
    payloads = {str(payload.get("zone_id") or "").strip(): payload for payload in _iter_zone_payloads()}
    zone_ids = sorted({zone_id for zone_id in payloads.keys() if zone_id} | set(recorded_states.keys()))

    broadcasted: list[str] = []
    for zone_id in zone_ids:
        if zone_id in skip:
            continue
        current_state = recorded_states.get(zone_id, DEFAULT_WEATHER)
        message = get_ambient_message(_zone_climate(zone_id), current_state, rng=random_source)
        if not message:
            continue
        if random_source.random() > ambient_probability:
            continue
        if _broadcast_weather_ambient(zone_id, message):
            broadcasted.append(zone_id)
    return broadcasted


def _room_environment(room) -> str:
    terrain = str(getattr(getattr(room, "db", None), "terrain_type", "") or "").strip().lower()
    if terrain == "swamp":
        return "swamp"
    key_text = str(getattr(room, "key", "") or "").strip().lower()
    desc_text = str(getattr(getattr(room, "db", None), "desc", "") or "").strip().lower()
    if any(token in f"{key_text} {desc_text}" for token in ("tavern", "inn", "alehouse", "taproom")):
        return "tavern"
    if hasattr(room, "get_environment_type"):
        environment_type = str(room.get_environment_type() or "urban").strip().lower() or "urban"
    else:
        environment_type = str(getattr(getattr(room, "db", None), "environment_type", "urban") or "urban").strip().lower() or "urban"
    if environment_type == "wilderness":
        return "forest"
    return "city"


def _room_payload_from_live_room(room) -> dict:
    return {
        "id": str(getattr(getattr(room, "db", None), "world_id", "") or getattr(room, "key", "") or getattr(room, "id", "")),
        "environment": _room_environment(room),
        "tags": normalize_room_tags(getattr(getattr(room, "db", None), "room_tags", None)),
    }


def _rooms_for_zone(zone_id: str) -> list[object]:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return []
    cached = _ZONE_ROOM_CACHE.get(normalized_zone_id)
    if cached is not None:
        return cached
    rooms = list(_query_rooms_for_zone(normalized_zone_id))
    _ZONE_ROOM_CACHE[normalized_zone_id] = rooms
    return rooms


def _eligible_rooms_for_zone(zone_id: str) -> list[tuple[object, bool]]:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return []
    cached = _ZONE_ELIGIBLE_CACHE.get(normalized_zone_id)
    if cached is not None:
        return cached

    zone_payload = _get_zone_payload(normalized_zone_id)
    eligible: list[tuple[object, bool]] = []
    for room in _rooms_for_zone(normalized_zone_id):
        room_payload = _room_payload_from_live_room(room)
        structure = str(((room_payload.get("tags") or {}).get("structure") or "")).strip().lower()
        is_threshold = structure in _THRESHOLD_STRUCTURES
        groups = determine_applicable_state_groups(room_payload, zone_payload)
        if "weather" in groups or is_threshold:
            eligible.append((room, is_threshold))

    _ZONE_ELIGIBLE_CACHE[normalized_zone_id] = eligible
    return eligible


def _broadcast_message(room, message: str) -> None:
    if not str(message or "").strip():
        return
    if hasattr(room, "msg_contents"):
        room.msg_contents(message)


def _transition_message(old: str, new: str, *, threshold: bool) -> str:
    key = f"{old}__{new}"
    entry = _TRANSITION_MESSAGES.get(key, {})
    variant = "threshold" if threshold else "outdoor"
    message = str(entry.get(variant) or "").strip()
    if message:
        return message
    logger.log_warn(f"[Weather] Missing transition message for {key}; using generic fallback.")
    return "The weather shifts."


def _broadcast_weather_transition(zone_id: str, old: str, new: str) -> None:
    rooms = list(_eligible_rooms_for_zone(zone_id))
    for room, is_threshold in rooms:
        _broadcast_message(room, _transition_message(old, new, threshold=is_threshold))


def _pick_lightning_message(*, rng=None) -> str:
    random_source = rng or random.Random()
    roll = random_source.random()
    if roll < 0.4:
        bucket = "flashes"
    elif roll < 0.8:
        bucket = "thunderclaps"
    else:
        bucket = "flash_then_thunder"
    options = _LIGHTNING_MESSAGES.get(bucket, [])
    if not options:
        return "Lightning flashes in the storm overhead."
    return random_source.choice(options)


def _broadcast_storm_lightning(zone_id: str, *, rng=None) -> bool:
    if get_current_weather(zone_id) != "storm":
        return False
    message = _pick_lightning_message(rng=rng)
    sent = False
    rooms = list(_eligible_rooms_for_zone(zone_id))
    for room, _is_threshold in rooms:
        _broadcast_message(room, message)
        sent = True
    return sent


class WeatherScript(Script):
    def at_script_creation(self):
        self.key = WEATHER_SCRIPT_KEY
        self.interval = _atmospheric_tick_interval_seconds()
        self.start_delay = True
        self.repeats = 0
        self.persistent = True
        self.db.atmospheric_tick_counter = 0

    def at_start(self):
        _reset_state_cache(self)
        invalidate_zone_caches()
        self.interval = _atmospheric_tick_interval_seconds()
        if not isinstance(getattr(self.db, "atmospheric_tick_counter", None), int):
            self.db.atmospheric_tick_counter = 0
        self.db.last_started_iso = _now_iso()

    def at_repeat(self):
        if not getattr(settings, "WEATHER_AUTOTICK_ENABLED", True):
            return
        counter = int(getattr(self.db, "atmospheric_tick_counter", 0) or 0) + 1
        ratio = _weather_state_tick_ratio()
        transitioned_zones: set[str] = set()
        if counter >= ratio:
            self.db.atmospheric_tick_counter = 0
            transitioned_zones = set(run_weather_cycle().keys())
        else:
            self.db.atmospheric_tick_counter = counter
        run_atmospheric_tick(skip_zone_ids=transitioned_zones)