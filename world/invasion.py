"""Per-zone invasion runtime state.

Invasions are admin-set persistent state read by other systems.
This module ships state only: no auto-progression, no broadcasting,
and no NPC spawning.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import datetime

import yaml
from evennia import search_script
from evennia.scripts.models import ScriptDB
from evennia.utils import logger

from typeclasses.scripts import Script


DEFAULT_INVASION = "none"
INVASION_SCRIPT_KEY = "global_invasion"
INVASION_SCRIPT_PATH = "world.invasion.InvasionScript"
INVASION_TYPES = (
    "none",
    "goblin_raid",
    "bandit_incursion",
    "monster_horde",
    "siege",
    "infestation",
)

_INVASION_STATE_PREFIX = "invasion_state__"
_INVASION_META_PREFIX = "invasion_meta__"
_ZONE_DIR = Path(__file__).resolve().parents[1] / "worlddata" / "zones"
_ZONE_PAYLOAD_CACHE: dict[str, dict] = {}
_ZONE_PAYLOAD_LIST_CACHE: list[dict] | None = None


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load_yaml(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def invalidate_zone_caches(zone_id: str | None = None) -> None:
    normalized_zone_id = str(zone_id or "").strip()
    if normalized_zone_id:
        _ZONE_PAYLOAD_CACHE.pop(normalized_zone_id, None)
    else:
        _ZONE_PAYLOAD_CACHE.clear()
    global _ZONE_PAYLOAD_LIST_CACHE
    _ZONE_PAYLOAD_LIST_CACHE = None


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
            logger.log_warn(f"[Invasion] Failed to load zone YAML {file_path.name}: {error}")
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
    setattr(script, "_invasion_state_cache", {})
    setattr(script, "_invasion_meta_cache", {})
    setattr(script, "_invasion_state_cache_loaded", False)


def _ensure_state_cache_loaded(script) -> None:
    if bool(getattr(script, "_invasion_state_cache_loaded", False)):
        return

    state_cache: dict[str, str] = {}
    for zone_id, value in _load_script_attribute_map(script, _INVASION_STATE_PREFIX).items():
        normalized_value = str(value or DEFAULT_INVASION).strip().lower() or DEFAULT_INVASION
        state_cache[zone_id] = normalized_value if normalized_value in INVASION_TYPES else DEFAULT_INVASION

    meta_cache: dict[str, dict] = {}
    for zone_id, value in _load_script_attribute_map(script, _INVASION_META_PREFIX).items():
        meta_cache[zone_id] = dict(value) if isinstance(value, dict) else {}

    setattr(script, "_invasion_state_cache", state_cache)
    setattr(script, "_invasion_meta_cache", meta_cache)
    setattr(script, "_invasion_state_cache_loaded", True)


def _recorded_invasion_states(script) -> dict[str, str]:
    _ensure_state_cache_loaded(script)
    return dict(getattr(script, "_invasion_state_cache", {}))


def _state_key(zone_id: str) -> str:
    return f"{_INVASION_STATE_PREFIX}{str(zone_id or '').strip()}"


def _meta_key(zone_id: str) -> str:
    return f"{_INVASION_META_PREFIX}{str(zone_id or '').strip()}"


def _get_invasion_script() -> InvasionScript | None:
    existing = []
    for script in _find_scripts_by_key(INVASION_SCRIPT_KEY):
        if getattr(script, "typeclass_path", "") == INVASION_SCRIPT_PATH:
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
            logger.log_trace(f"[Invasion] Failed to start existing InvasionScript: {error}")
        return keeper
    return None


def get_current_invasion(zone_id: str) -> str:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return DEFAULT_INVASION
    script = _get_invasion_script()
    if script is None:
        return DEFAULT_INVASION
    _ensure_state_cache_loaded(script)
    value = str(getattr(script, "_invasion_state_cache", {}).get(normalized_zone_id, DEFAULT_INVASION) or DEFAULT_INVASION).strip().lower()
    return value if value in INVASION_TYPES else DEFAULT_INVASION


def set_current_invasion(zone_id: str, value: str, *, source: str = "admin") -> None:
    normalized_zone_id = str(zone_id or "").strip()
    normalized_value = str(value or "").strip().lower()
    if not normalized_zone_id:
        raise ValueError("zone_id is required.")
    if normalized_value not in INVASION_TYPES:
        raise ValueError(f"Unknown invasion type: {value}")
    script = _get_invasion_script()
    if script is None:
        return
    _ensure_state_cache_loaded(script)
    getattr(script, "_invasion_state_cache", {})[normalized_zone_id] = normalized_value
    getattr(script, "_invasion_meta_cache", {})[normalized_zone_id] = {
        "source": str(source or "admin"),
        "updated_at": _now_iso(),
    }
    script.attributes.add(_state_key(normalized_zone_id), normalized_value)
    script.attributes.add(_meta_key(normalized_zone_id), getattr(script, "_invasion_meta_cache", {})[normalized_zone_id])


def is_zone_invaded(zone_id: str) -> bool:
    return get_current_invasion(zone_id) != DEFAULT_INVASION


def list_invasion_types() -> tuple[str, ...]:
    return INVASION_TYPES


def get_invasion_state() -> dict:
    script = _get_invasion_script()
    if script is None:
        return {
            "zones": [],
            "counts": {},
            "types": list_invasion_types(),
        }

    _ensure_state_cache_loaded(script)
    recorded_states = _recorded_invasion_states(script)
    payloads = {str(payload.get("zone_id") or "").strip(): payload for payload in _iter_zone_payloads()}
    zone_ids = sorted({zone_id for zone_id in payloads.keys() if zone_id} | set(recorded_states.keys()))
    zones = []
    counts = Counter()
    for zone_id in zone_ids:
        payload = payloads.get(zone_id)
        invasion_type = recorded_states.get(zone_id, DEFAULT_INVASION)
        counts[invasion_type] += 1
        zones.append(
            {
                "zone_id": zone_id,
                "name": str((payload or {}).get("name") or zone_id),
                "invasion": invasion_type,
                "active": invasion_type != DEFAULT_INVASION,
                "meta": dict(getattr(script, "_invasion_meta_cache", {}).get(zone_id, {})),
            }
        )
    return {
        "zones": zones,
        "counts": dict(sorted(counts.items())),
        "types": list_invasion_types(),
    }


class InvasionScript(Script):
    def at_script_creation(self):
        self.key = INVASION_SCRIPT_KEY
        self.interval = 0
        self.repeats = 0
        self.persistent = True

    def at_start(self):
        _reset_state_cache(self)
        invalidate_zone_caches()
        self.db.last_started_iso = _now_iso()

    def at_repeat(self):
        return