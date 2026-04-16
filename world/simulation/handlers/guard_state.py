from evennia.objects.models import ObjectDB
from evennia.utils import logger

from world.simulation.patrol_routes import get_patrol_route, get_route_length


SUSPICION_DECAY_PER_TICK = 1
MIN_TARGET_THRESHOLD = 10
MIN_PURSUIT_THRESHOLD = 20
MIN_WARN_THRESHOLD = 15
MIN_ARREST_THRESHOLD = 30
HOSTILE_SUSPICION_THRESHOLD = 51
SUSPICIOUS_THRESHOLD = 11
VALID_PURSUIT_STATES = {"none", "tracking", "intercepting"}
VALID_CONFRONTATION_STATES = {"none", "warning", "arresting", "cooldown"}


def clamp_suspicion(value):
    if isinstance(value, dict):
        value = value.get("value", 0)
    try:
        normalized = int(value or 0)
    except (TypeError, ValueError):
        normalized = 0
    return max(0, min(normalized, 100))


class GuardStateHandler:
    STORAGE_KEY = "diresim_guard_state"
    STORAGE_CATEGORY = "simulation"

    def __init__(self, obj):
        self.obj = obj
        self._dirty = False
        self.reset_transient()
        self._load()

    def _load(self):
        attributes = getattr(self.obj, "attributes", None)
        payload = {}
        if attributes is not None:
            payload = dict(attributes.get(self.STORAGE_KEY, category=self.STORAGE_CATEGORY, default={}) or {})

        db_state = getattr(self.obj, "db", None)
        self.patrol_route_id = payload.get("patrol_route_id")
        self.patrol_zone_id = payload.get("patrol_zone_id")
        self.patrol_home_room_id = payload.get("patrol_home_room_id", payload.get("home_room_id"))
        self.patrol_room_ids = list(payload.get("patrol_room_ids") or [])
        self.patrol_route_room_ids = list(payload.get("patrol_route_room_ids") or [])
        self.patrol_enabled = payload.get("patrol_enabled", bool(self.patrol_route_id))
        self.patrol_index = payload.get("patrol_index", getattr(db_state, "previous_room_id", 0) or 0)
        self.movement_target_room_id = payload.get("movement_target_room_id")
        self.movement_progress_index = payload.get("movement_progress_index", self.patrol_index)
        self.behavior_state = payload.get("behavior_state", getattr(db_state, "enforcement_state", None) or "idle")
        self.warning_count = payload.get("warning_count", getattr(db_state, "warning_count", 0) or 0)
        self.suspicion_targets = dict(payload.get("suspicion_targets") or getattr(db_state, "suspicion_targets", None) or {})
        self.current_target_id = payload.get("current_target_id", getattr(db_state, "current_target_id", None))
        self.confrontation_target_id = payload.get("confrontation_target_id")
        self.confrontation_state = payload.get("confrontation_state", "none")
        self.warning_stage = payload.get("warning_stage", 0)
        self.last_warning_at = payload.get("last_warning_at", 0.0) or 0.0
        self.arrest_attempted_at = payload.get("arrest_attempted_at", 0.0) or 0.0
        self.pursuit_target_id = payload.get("pursuit_target_id")
        self.pursuit_last_known_room_id = payload.get("pursuit_last_known_room_id")
        self.pursuit_state = payload.get("pursuit_state", "none")
        self.pursuit_started_at = payload.get("pursuit_started_at", 0.0) or 0.0
        self.intercept_room_id = payload.get("intercept_room_id")
        self.cooldowns = dict(payload.get("cooldowns") or {})
        self.last_significant_event_at = payload.get("last_significant_event_at", 0.0) or 0.0
        self.home_room_id = payload.get("home_room_id")
        self.validate()

    def _save(self):
        attributes = getattr(self.obj, "attributes", None)
        if attributes is not None:
            attributes.add(self.STORAGE_KEY, self.to_dict(), category=self.STORAGE_CATEGORY)
        self._dirty = False

    def to_dict(self):
        # Persistent state only: patrol state, warnings, suspicion, target, cooldowns, home room, and last meaningful event time.
        return {
            "patrol_route_id": self.patrol_route_id,
            "patrol_zone_id": self.patrol_zone_id,
            "patrol_home_room_id": self.patrol_home_room_id,
            "patrol_room_ids": list(self.patrol_room_ids or []),
            "patrol_route_room_ids": list(self.patrol_route_room_ids or []),
            "patrol_enabled": bool(self.patrol_enabled),
            "patrol_index": self.patrol_index,
            "movement_target_room_id": self.movement_target_room_id,
            "movement_progress_index": self.movement_progress_index,
            "behavior_state": self.behavior_state,
            "warning_count": self.warning_count,
            "suspicion_targets": dict(self.suspicion_targets or {}),
            "current_target_id": self.current_target_id,
            "confrontation_target_id": self.confrontation_target_id,
            "confrontation_state": self.confrontation_state,
            "warning_stage": self.warning_stage,
            "last_warning_at": self.last_warning_at,
            "arrest_attempted_at": self.arrest_attempted_at,
            "pursuit_target_id": self.pursuit_target_id,
            "pursuit_last_known_room_id": self.pursuit_last_known_room_id,
            "pursuit_state": self.pursuit_state,
            "pursuit_started_at": self.pursuit_started_at,
            "intercept_room_id": self.intercept_room_id,
            "cooldowns": dict(self.cooldowns or {}),
            "last_significant_event_at": self.last_significant_event_at,
            "home_room_id": self.home_room_id,
        }

    def mark_dirty(self):
        self._dirty = True

    def save_if_needed(self):
        if self._dirty:
            self._save()

    def reset_transient(self):
        # Transient only: do not serialize significance, queues, due flags, wake sources, or per-cycle metrics.
        self.last_cycle_metrics = {}
        self.last_known_room_fact_version = 0
        self.last_decision_reason = None
        self.cached_candidates = []
        self._missing_route_logged = False
        self._missing_patrol_zone_logged = False

    def validate(self):
        self.patrol_zone_id = str(self.patrol_zone_id or "").strip() or None
        normalized_patrol_home_room_id = int(self.patrol_home_room_id or 0) or None
        self.patrol_home_room_id = normalized_patrol_home_room_id
        normalized_patrol_room_ids = []
        for room_id in list(self.patrol_room_ids or []):
            normalized_room_id = int(room_id or 0)
            if normalized_room_id <= 0 or normalized_room_id in normalized_patrol_room_ids:
                continue
            normalized_patrol_room_ids.append(normalized_room_id)
        self.patrol_room_ids = normalized_patrol_room_ids
        normalized_patrol_route_room_ids = []
        for room_id in list(self.patrol_route_room_ids or []):
            normalized_room_id = int(room_id or 0)
            if normalized_room_id <= 0 or normalized_room_id in normalized_patrol_route_room_ids:
                continue
            normalized_patrol_route_room_ids.append(normalized_room_id)
        self.patrol_route_room_ids = normalized_patrol_route_room_ids
        self.patrol_enabled = bool(self.patrol_enabled)
        if not isinstance(self.patrol_index, int):
            self.patrol_index = int(self.patrol_index or 0)
        if not isinstance(self.movement_progress_index, int):
            self.movement_progress_index = int(self.movement_progress_index or 0)
        self.patrol_index = max(0, int(self.patrol_index or 0))
        self.movement_progress_index = max(0, int(self.movement_progress_index or 0))
        self.warning_count = max(0, int(self.warning_count or 0))
        self.warning_stage = max(0, min(2, int(self.warning_stage or 0)))
        if not isinstance(self.suspicion_targets, dict):
            self.suspicion_targets = {}
        normalized_suspicion_targets = {}
        for raw_key, raw_entry in list(self.suspicion_targets.items()):
            try:
                key = str(int(raw_key or 0) or 0)
            except (TypeError, ValueError):
                continue
            if key == "0":
                continue
            if isinstance(raw_entry, dict):
                normalized_value = clamp_suspicion(raw_entry.get("value", 0))
                normalized_seen = float(raw_entry.get("last_seen_at", 0.0) or 0.0)
            else:
                normalized_value = clamp_suspicion(raw_entry)
                normalized_seen = 0.0
            if normalized_value <= 0:
                continue
            normalized_suspicion_targets[key] = {
                "value": normalized_value,
                "last_seen_at": normalized_seen,
            }
        self.suspicion_targets = normalized_suspicion_targets
        if not isinstance(self.cooldowns, dict):
            self.cooldowns = {}
        if self.behavior_state not in {"idle", "observe", "warn", "patrol", "escort"}:
            self.behavior_state = "idle"
        if self.confrontation_state not in VALID_CONFRONTATION_STATES:
            self.confrontation_state = "none"
        if self.pursuit_state not in VALID_PURSUIT_STATES:
            self.pursuit_state = "none"
        self.last_significant_event_at = float(self.last_significant_event_at or 0.0)
        self.last_warning_at = float(self.last_warning_at or 0.0)
        self.arrest_attempted_at = float(self.arrest_attempted_at or 0.0)
        self.pursuit_started_at = float(self.pursuit_started_at or 0.0)
        if self.home_room_id in ("", 0):
            self.home_room_id = None
        if self.patrol_home_room_id is None and self.home_room_id is not None:
            self.patrol_home_room_id = int(self.home_room_id or 0) or None
        if self.home_room_id is None and self.patrol_home_room_id is not None:
            self.home_room_id = int(self.patrol_home_room_id or 0) or None
        if self.current_target_id in ("", 0):
            self.current_target_id = None
        if self.confrontation_target_id in ("", 0):
            self.confrontation_target_id = None
        if self.pursuit_target_id in ("", 0):
            self.pursuit_target_id = None
        if self.pursuit_last_known_room_id in ("", 0):
            self.pursuit_last_known_room_id = None
        if self.intercept_room_id in ("", 0):
            self.intercept_room_id = None
        if self.movement_target_room_id in ("", 0):
            self.movement_target_room_id = None
        return self

    def set_patrol_route_id(self, value):
        normalized = str(value or "").strip() or None
        if self.patrol_route_id != normalized:
            self.patrol_route_id = normalized
            self.mark_dirty()
        return self.patrol_route_id

    def set_patrol_zone_id(self, value):
        normalized = str(value or "").strip() or None
        if self.patrol_zone_id != normalized:
            self.patrol_zone_id = normalized
            self.mark_dirty()
        return self.patrol_zone_id

    def get_patrol_zone_id(self):
        return self.patrol_zone_id

    def set_patrol_home_room_id(self, value):
        normalized = int(value or 0) or None
        if self.patrol_home_room_id is None and normalized is not None:
            self.patrol_home_room_id = normalized
            self.mark_dirty()
        if self.home_room_id is None and normalized is not None:
            self.home_room_id = normalized
            self.mark_dirty()
        return self.patrol_home_room_id

    def get_patrol_home_room_id(self):
        return self.patrol_home_room_id

    def set_patrol_room_ids(self, values):
        normalized = []
        for room_id in list(values or []):
            normalized_room_id = int(room_id or 0)
            if normalized_room_id <= 0 or normalized_room_id in normalized:
                continue
            normalized.append(normalized_room_id)
        if self.patrol_room_ids != normalized:
            self.patrol_room_ids = normalized
            self.mark_dirty()
        return list(self.patrol_room_ids or [])

    def set_patrol_route_room_ids(self, values):
        normalized = []
        for room_id in list(values or []):
            normalized_room_id = int(room_id or 0)
            if normalized_room_id <= 0 or normalized_room_id in normalized:
                continue
            normalized.append(normalized_room_id)
        if self.patrol_route_room_ids != normalized:
            self.patrol_route_room_ids = normalized
            self.mark_dirty()
        return list(self.patrol_route_room_ids or [])

    def get_patrol_route_room_ids(self):
        return list(self.patrol_route_room_ids or [])

    def get_patrol_room_ids(self):
        return list(self.patrol_room_ids or [])

    def get_patrol_zone_size(self):
        return len(list(self.patrol_room_ids or []))

    def set_patrol_enabled(self, value):
        normalized = bool(value)
        if self.patrol_enabled != normalized:
            self.patrol_enabled = normalized
            self.mark_dirty()
        return self.patrol_enabled

    def get_response_zone_id(self):
        return self.get_patrol_zone_id()

    def is_room_in_patrol_zone(self, room_id):
        normalized_room_id = int(room_id or 0) or 0
        if normalized_room_id <= 0:
            return False
        return normalized_room_id in set(self.get_patrol_room_ids())

    def ensure_home_room_id(self, fallback_room_id=None):
        fallback_room_id = int(fallback_room_id or 0) or None
        if self.home_room_id is None and fallback_room_id is not None:
            self.home_room_id = fallback_room_id
            self.mark_dirty()
        if self.patrol_home_room_id is None and fallback_room_id is not None:
            self.patrol_home_room_id = fallback_room_id
            self.mark_dirty()
        return self.home_room_id

    def set_behavior_state(self, value):
        normalized = str(value or "idle").strip().lower() or "idle"
        if normalized not in {"idle", "observe", "warn", "patrol", "escort"}:
            normalized = "idle"
        if self.behavior_state != normalized:
            self.behavior_state = normalized
            self.mark_dirty()
        return self.behavior_state

    def set_warning_count(self, value):
        normalized = max(0, int(value or 0))
        if self.warning_count != normalized:
            self.warning_count = normalized
            self.mark_dirty()
        return self.warning_count

    def increment_warning_count(self, delta=1):
        return self.set_warning_count(int(self.warning_count or 0) + int(delta or 0))

    def set_current_target_id(self, value):
        normalized = int(value or 0) or None
        if self.current_target_id != normalized:
            self.current_target_id = normalized
            self.mark_dirty()
        return self.current_target_id

    def set_confrontation_state(self, value):
        normalized = str(value or "none").strip().lower() or "none"
        if normalized not in VALID_CONFRONTATION_STATES:
            normalized = "none"
        if self.confrontation_state != normalized:
            self.confrontation_state = normalized
            self.mark_dirty()
        return self.confrontation_state

    def begin_warning(self, target_id, now):
        normalized_target_id = int(target_id or 0) or None
        normalized_now = float(now or 0.0)
        if self.confrontation_target_id != normalized_target_id:
            self.confrontation_target_id = normalized_target_id
            self.mark_dirty()
        if self.current_target_id != normalized_target_id:
            self.current_target_id = normalized_target_id
            self.mark_dirty()
        self.set_confrontation_state("warning")
        if self.last_warning_at != normalized_now:
            self.last_warning_at = normalized_now
            self.mark_dirty()
        return self.confrontation_target_id

    def advance_warning_stage(self, now):
        normalized_stage = min(int(self.warning_stage or 0) + 1, 2)
        normalized_now = float(now or 0.0)
        if self.warning_stage != normalized_stage:
            self.warning_stage = normalized_stage
            self.mark_dirty()
        if self.last_warning_at != normalized_now:
            self.last_warning_at = normalized_now
            self.mark_dirty()
        return self.warning_stage

    def begin_arrest(self, target_id, now):
        normalized_target_id = int(target_id or 0) or None
        normalized_now = float(now or 0.0)
        if self.confrontation_target_id != normalized_target_id:
            self.confrontation_target_id = normalized_target_id
            self.mark_dirty()
        if self.current_target_id != normalized_target_id:
            self.current_target_id = normalized_target_id
            self.mark_dirty()
        self.set_confrontation_state("arresting")
        if self.arrest_attempted_at != normalized_now:
            self.arrest_attempted_at = normalized_now
            self.mark_dirty()
        return self.confrontation_target_id

    def clear_confrontation(self):
        cleared = False
        if self.confrontation_target_id is not None:
            self.confrontation_target_id = None
            cleared = True
        if self.confrontation_state != "none":
            self.confrontation_state = "none"
            cleared = True
        if self.warning_stage != 0:
            self.warning_stage = 0
            cleared = True
        if self.last_warning_at != 0.0:
            self.last_warning_at = 0.0
            cleared = True
        if self.arrest_attempted_at != 0.0:
            self.arrest_attempted_at = 0.0
            cleared = True
        if cleared:
            self.mark_dirty()
        return True

    def set_pursuit_state(self, value):
        normalized = str(value or "none").strip().lower() or "none"
        if normalized not in VALID_PURSUIT_STATES:
            normalized = "none"
        if self.pursuit_state != normalized:
            self.pursuit_state = normalized
            self.mark_dirty()
        return self.pursuit_state

    def begin_pursuit(self, target_id, room_id, now):
        normalized_target_id = int(target_id or 0) or None
        normalized_room_id = int(room_id or 0) or None
        normalized_now = float(now or 0.0)
        if self.pursuit_target_id != normalized_target_id:
            self.pursuit_target_id = normalized_target_id
            self.mark_dirty()
        if self.current_target_id != normalized_target_id:
            self.current_target_id = normalized_target_id
            self.mark_dirty()
        if self.pursuit_last_known_room_id != normalized_room_id:
            self.pursuit_last_known_room_id = normalized_room_id
            self.mark_dirty()
        if self.pursuit_started_at != normalized_now:
            self.pursuit_started_at = normalized_now
            self.mark_dirty()
        self.set_pursuit_state("tracking")
        return self.pursuit_target_id

    def update_last_known_room(self, room_id, now=None):
        normalized_room_id = int(room_id or 0) or None
        normalized_now = float(now or 0.0) if now is not None else None
        if self.pursuit_last_known_room_id != normalized_room_id:
            self.pursuit_last_known_room_id = normalized_room_id
            self.mark_dirty()
        if normalized_now is not None and self.last_significant_event_at != normalized_now:
            self.last_significant_event_at = normalized_now
            self.mark_dirty()
        return self.pursuit_last_known_room_id

    def set_intercept_room(self, room_id):
        normalized_room_id = int(room_id or 0) or None
        if self.intercept_room_id != normalized_room_id:
            self.intercept_room_id = normalized_room_id
            self.mark_dirty()
        return self.intercept_room_id

    def clear_pursuit(self):
        cleared = False
        if self.pursuit_target_id is not None:
            self.pursuit_target_id = None
            cleared = True
        if self.pursuit_last_known_room_id is not None:
            self.pursuit_last_known_room_id = None
            cleared = True
        if self.intercept_room_id is not None:
            self.intercept_room_id = None
            cleared = True
        if self.pursuit_started_at != 0.0:
            self.pursuit_started_at = 0.0
            cleared = True
        if self.pursuit_state != "none":
            self.pursuit_state = "none"
            cleared = True
        if cleared:
            self.mark_dirty()
        return True

    def set_patrol_index(self, value):
        normalized = int(value or 0)
        if self.patrol_index != normalized:
            self.patrol_index = normalized
            self.mark_dirty()
        return self.patrol_index

    def set_movement_target_room_id(self, value):
        normalized = int(value or 0) or None
        if self.movement_target_room_id != normalized:
            self.movement_target_room_id = normalized
            self.mark_dirty()
        return self.movement_target_room_id

    def set_movement_progress_index(self, value):
        normalized = max(0, int(value or 0))
        if self.movement_progress_index != normalized:
            self.movement_progress_index = normalized
            self.mark_dirty()
        return self.movement_progress_index

    def get_route_length(self, route=None):
        route = route or get_patrol_route(self.patrol_route_id)
        if isinstance(route, dict) and list(route.get("room_ids") or []):
            return get_route_length(route)
        return len(list(self.get_patrol_route_room_ids() or []))

    def get_next_patrol_room(self):
        if not bool(self.patrol_enabled):
            return None

        patrol_home_room_id = self.get_patrol_home_room_id()
        patrol_room_ids = self.get_patrol_room_ids()
        if patrol_home_room_id is None or not patrol_room_ids:
            if not self._missing_patrol_zone_logged:
                logger.log_trace(
                    f"[DireSim] Missing patrol zone guard={int(getattr(self.obj, 'id', 0) or 0)} patrol_zone_id={self.patrol_zone_id}"
                )
                self._missing_patrol_zone_logged = True
            return None

        self._missing_patrol_zone_logged = False
        route = get_patrol_route(self.patrol_route_id)
        route_room_ids = [int(room_id or 0) for room_id in list((route or {}).get("room_ids") or []) if int(room_id or 0) in set(patrol_room_ids)]
        if not route_room_ids:
            route_room_ids = [int(room_id or 0) for room_id in self.get_patrol_route_room_ids() if int(room_id or 0) in set(patrol_room_ids)]
        route_length = len(route_room_ids)
        if route_length <= 0:
            if not self._missing_route_logged:
                logger.log_trace(
                    f"[DireSim] Missing patrol route guard={int(getattr(self.obj, 'id', 0) or 0)} route_id={self.patrol_route_id}"
                )
                self._missing_route_logged = True
            return None

        self._missing_route_logged = False
        index = int(self.patrol_index or 0)
        loop_route = bool((route or {}).get("loop", True))
        if index >= route_length:
            index = 0 if loop_route else max(0, route_length - 1)
        next_room_id = int(route_room_ids[index] or 0) or None
        if next_room_id is None or not self.is_room_in_patrol_zone(next_room_id):
            return None
        return next_room_id

    def advance_patrol_index(self):
        route = get_patrol_route(self.patrol_route_id)
        route_room_ids = list((route or {}).get("room_ids") or [])
        if not route_room_ids:
            route_room_ids = self.get_patrol_route_room_ids()
        route_length = len(list(route_room_ids or []))
        if route_length <= 0:
            return int(self.patrol_index or 0)

        next_index = int(self.patrol_index or 0) + 1
        if next_index >= route_length:
            if bool((route or {}).get("loop", True)):
                next_index = 0
            else:
                next_index = max(0, route_length - 1)

        changed = False
        if self.patrol_index != next_index:
            self.patrol_index = next_index
            changed = True
        if self.movement_progress_index != next_index:
            self.movement_progress_index = next_index
            changed = True
        if changed:
            self.mark_dirty()
        return next_index

    def is_movement_due(self, now):
        return not self.is_cooldown_active("move_until", now)

    def is_pursuit_due(self, now):
        return not self.is_cooldown_active("pursuit_until", now)

    def is_warning_due(self, now):
        return not self.is_cooldown_active("warn_until", now)

    def is_arrest_due(self, now):
        return not self.is_cooldown_active("arrest_until", now)

    def can_emit_enter(self, now):
        return not self.is_cooldown_active("msg_enter_until", now)

    def can_emit_exit(self, now):
        return not self.is_cooldown_active("msg_exit_until", now)

    def can_emit_observe(self, now):
        return not self.is_cooldown_active("msg_observe_until", now)

    def set_enter_cooldown(self, now):
        return self.set_cooldown("msg_enter_until", float(now or 0.0) + 5.0)

    def set_exit_cooldown(self, now):
        return self.set_cooldown("msg_exit_until", float(now or 0.0) + 5.0)

    def set_observe_cooldown(self, now):
        return self.set_cooldown("msg_observe_until", float(now or 0.0) + 10.0)

    def is_target_in_custody(self, target_id):
        normalized_target_id = int(target_id or 0) or 0
        if normalized_target_id <= 0:
            return False
        try:
            target = ObjectDB.objects.get(id=normalized_target_id)
        except Exception:
            return False
        return bool(getattr(getattr(target, "db", None), "is_in_custody", False))

    def has_valid_pursuit(self):
        return bool(self.pursuit_target_id and self.pursuit_last_known_room_id)

    def get_suspicion(self, target_id):
        key = str(int(target_id or 0) or 0)
        if key == "0":
            return 0
        entry = self.suspicion_targets.get(key, {})
        if isinstance(entry, dict):
            return clamp_suspicion(entry.get("value", 0))
        return clamp_suspicion(entry)

    def _get_suspicion_entry(self, target_id, create=False):
        key = str(int(target_id or 0) or 0)
        if key == "0":
            return None
        entry = self.suspicion_targets.get(key)
        if isinstance(entry, dict):
            entry.setdefault("value", clamp_suspicion(entry.get("value", 0)))
            entry.setdefault("last_seen_at", float(entry.get("last_seen_at", 0.0) or 0.0))
            return entry
        if entry is not None:
            normalized = {
                "value": clamp_suspicion(entry),
                "last_seen_at": 0.0,
            }
            self.suspicion_targets[key] = normalized
            return normalized
        if create:
            created = {"value": 0, "last_seen_at": 0.0}
            self.suspicion_targets[key] = created
            return created
        return None

    def set_suspicion(self, target_id, value):
        key = str(int(target_id or 0) or 0)
        if key == "0":
            return 0
        normalized = clamp_suspicion(value)
        existing = self.get_suspicion(target_id)
        if normalized <= 0:
            if key in self.suspicion_targets:
                self.suspicion_targets.pop(key, None)
                self.mark_dirty()
            return 0
        if existing != normalized:
            entry = self._get_suspicion_entry(target_id, create=True) or {"value": 0, "last_seen_at": 0.0}
            entry["value"] = normalized
            self.suspicion_targets[key] = entry
            self.mark_dirty()
        return normalized

    def add_suspicion(self, target_id, delta):
        return self.set_suspicion(target_id, self.get_suspicion(target_id) + int(delta or 0))

    def touch_target(self, target_id, now):
        entry = self._get_suspicion_entry(target_id, create=True)
        if entry is None:
            return None
        normalized_now = float(now or 0.0)
        if float(entry.get("last_seen_at", 0.0) or 0.0) != normalized_now:
            entry["last_seen_at"] = normalized_now
            self.mark_dirty()
        return entry

    def add_suspicion_from_event(self, target_id, amount, now):
        entry = self._get_suspicion_entry(target_id, create=True)
        if entry is None:
            return 0
        normalized_amount = int(amount or 0)
        normalized_value = clamp_suspicion(int(entry.get("value", 0) or 0) + normalized_amount)
        entry["value"] = normalized_value
        entry["last_seen_at"] = float(now or 0.0)
        self.suspicion_targets[str(int(target_id or 0) or 0)] = entry
        self.mark_dirty()
        return normalized_value

    def get_effective_suspicion(self, target_id, now):
        entry = self._get_suspicion_entry(target_id, create=False)
        if not entry:
            return 0
        raw_value = clamp_suspicion(entry.get("value", 0))
        last_seen_at = float(entry.get("last_seen_at", 0.0) or 0.0)
        elapsed = max(0.0, float(now or 0.0) - last_seen_at)
        decayed = raw_value - int(elapsed * SUSPICION_DECAY_PER_TICK)
        return clamp_suspicion(decayed)

    def cleanup_suspicion(self, now):
        removed = []
        for target_key in list(self.suspicion_targets.keys()):
            if self.get_effective_suspicion(target_key, now) > 0:
                continue
            self.suspicion_targets.pop(target_key, None)
            removed.append(int(target_key or 0))
        if removed:
            self.mark_dirty()
        return removed

    def is_suspicious(self, target_id, now=None):
        value = self.get_effective_suspicion(target_id, now if now is not None else 0.0) if now is not None else self.get_suspicion(target_id)
        return value >= SUSPICIOUS_THRESHOLD

    def is_hostile(self, target_id, now=None):
        value = self.get_effective_suspicion(target_id, now if now is not None else 0.0) if now is not None else self.get_suspicion(target_id)
        return value >= HOSTILE_SUSPICION_THRESHOLD

    def get_primary_target(self, now):
        best_target_id = None
        best_value = 0
        for target_key in list(self.suspicion_targets.keys()):
            effective_value = self.get_effective_suspicion(target_key, now)
            if effective_value < MIN_TARGET_THRESHOLD:
                continue
            target_id = int(target_key or 0)
            if effective_value > best_value:
                best_target_id = target_id
                best_value = effective_value
        return best_target_id

    def update_primary_target(self, now):
        self.cleanup_suspicion(now)
        primary_target_id = self.get_primary_target(now)
        if primary_target_id is None and self.current_target_id is not None and self.is_target_in_custody(self.current_target_id):
            custody_target_id = int(self.current_target_id or 0) or None
            self.set_current_target_id(custody_target_id)
            self.clear_pursuit()
            return custody_target_id
        self.set_current_target_id(primary_target_id)
        if primary_target_id is None:
            self.clear_confrontation()
            self.clear_pursuit()
        elif self.pursuit_target_id is None:
            self.pursuit_target_id = primary_target_id
            self.mark_dirty()
        return primary_target_id

    def clear_suspicion(self, target_id):
        return self.set_suspicion(target_id, 0)

    def get_cooldown(self, name):
        return self.cooldowns.get(str(name or ""))

    def set_cooldown(self, name, value):
        key = str(name or "").strip()
        if not key:
            return None
        normalized = float(value or 0.0)
        if self.cooldowns.get(key) != normalized:
            self.cooldowns[key] = normalized
            self.mark_dirty()
        return normalized

    def clear_cooldown(self, name):
        key = str(name or "").strip()
        if key in self.cooldowns:
            self.cooldowns.pop(key, None)
            self.mark_dirty()

    def is_cooldown_active(self, name, now):
        value = self.get_cooldown(name)
        if value is None:
            return False
        return float(value or 0.0) > float(now or 0.0)

    def set_last_significant_event_at(self, value):
        normalized = float(value or 0.0)
        if self.last_significant_event_at != normalized:
            self.last_significant_event_at = normalized
            self.mark_dirty()
        return self.last_significant_event_at