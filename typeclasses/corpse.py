import copy
from collections.abc import Mapping
import time

from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.search import search_object
from server.systems.ammo_runtime import merge_ammo_stacks

from .objects import ObjectParent


DEFAULT_CORPSE_EMPATH_WOUNDS = {
    "vitality": 0,
    "bleeding": 0,
    "poison": 0,
    "disease": 0,
    "fatigue": 0,
    "trauma": 0,
}

CORPSE_DECAY_STAGE_PENALTIES = {
    0: {"label": "Fresh", "internal": 0, "bleed": 0, "favor": 0, "chance": 0.0},
    1: {"label": "Fading", "internal": 6, "bleed": 1, "favor": 0, "chance": 0.08},
    2: {"label": "Failing", "internal": 14, "bleed": 3, "favor": 1, "chance": 0.18},
    3: {"label": "Ruinous", "internal": 24, "bleed": 6, "favor": 2, "chance": 0.32},
}

CORPSE_SINGLE_EMPATH_PREP_CAP = 55


def _normalize_corpse_empath_wounds(wounds=None):
    normalized = dict(DEFAULT_CORPSE_EMPATH_WOUNDS)
    for key, value in dict(wounds or {}).items():
        if key not in normalized:
            continue
        try:
            normalized[key] = max(0, min(100, int(value or 0)))
        except (TypeError, ValueError):
            normalized[key] = 0
    return normalized


def _normalize_corpse_injuries(injuries=None):
    normalized = {}
    for part_name, raw_part in dict(injuries or {}).items():
        if not isinstance(raw_part, Mapping):
            continue
        part = dict(raw_part)
        part["external"] = max(0, int(part.get("external", 0) or 0))
        part["internal"] = max(0, int(part.get("internal", 0) or 0))
        part["bruise"] = max(0, int(part.get("bruise", 0) or 0))
        part["bleed"] = max(0, int(part.get("bleed", part.get("bleeding", 0)) or 0))
        part["scar"] = max(0, int(part.get("scar", 0) or 0))
        normalized[str(part_name)] = part
    return normalized


def _get_corpse_bleeding_points(injuries):
    return max(0, sum(max(0, int((part or {}).get("bleed", 0) or 0)) for part in dict(injuries or {}).values()))


def _get_corpse_vitality_points(injuries):
    total = 0
    for part in dict(injuries or {}).values():
        body_part = dict(part or {})
        total += max(
            max(0, int(body_part.get("external", 0) or 0)),
            max(0, int(body_part.get("internal", 0) or 0)),
            max(0, int(body_part.get("bruise", 0) or 0)),
        )
    return max(0, total)


def _sync_corpse_aggregate_from_injuries(payload):
    normalized = dict(payload or {})
    empath = _normalize_corpse_empath_wounds(normalized.get("empath"))
    injuries = _normalize_corpse_injuries(normalized.get("injuries"))
    baseline = dict(normalized.get("baseline") or {})

    base_bleeding_points = max(0, int(baseline.get("bleeding_points", 0) or 0))
    base_vitality_points = max(0, int(baseline.get("vitality_points", 0) or 0))
    base_bleeding_load = max(0, int(baseline.get("bleeding_load", empath.get("bleeding", 0)) or 0))
    base_vitality_load = max(0, int(baseline.get("vitality_load", empath.get("vitality", 0)) or 0))

    current_bleeding_points = _get_corpse_bleeding_points(injuries)
    current_vitality_points = _get_corpse_vitality_points(injuries)

    if base_bleeding_points > 0:
        empath["bleeding"] = max(0, min(100, int(round(base_bleeding_load * (current_bleeding_points / float(base_bleeding_points))))))
    if base_vitality_points > 0:
        empath["vitality"] = max(0, min(100, int(round(base_vitality_load * (current_vitality_points / float(base_vitality_points))))))

    normalized["empath"] = empath
    normalized["injuries"] = injuries
    normalized["baseline"] = {
        "bleeding_points": base_bleeding_points or current_bleeding_points,
        "vitality_points": base_vitality_points or current_vitality_points,
        "bleeding_load": base_bleeding_load,
        "vitality_load": base_vitality_load,
    }
    return normalized


def normalize_corpse_wounds(payload=None):
    raw = dict(payload or {})
    normalized = {
        "empath": _normalize_corpse_empath_wounds(raw.get("empath", raw.get("wounds"))),
        "injuries": _normalize_corpse_injuries(raw.get("injuries")),
        "baseline": dict(raw.get("baseline") or {}),
    }
    return _sync_corpse_aggregate_from_injuries(normalized)


def get_corpse_wounds(corpse):
    if not corpse:
        return normalize_corpse_wounds()
    return normalize_corpse_wounds(getattr(getattr(corpse, "db", None), "wounds", None) or {})


def get_corpse_internal_load(wounds):
    normalized = normalize_corpse_wounds(wounds)
    return max(0, sum(max(0, int((part or {}).get("internal", 0) or 0)) for part in normalized.get("injuries", {}).values()))


def is_stable(wounds):
    normalized = normalize_corpse_wounds(wounds)
    return (
        int(normalized.get("empath", {}).get("bleeding", 0) or 0) < 15
        and get_corpse_internal_load(normalized) < 20
        and int(normalized.get("empath", {}).get("vitality", 0) or 0) < 40
    )


def is_near_stable(wounds):
    normalized = normalize_corpse_wounds(wounds)
    return (
        int(normalized.get("empath", {}).get("bleeding", 0) or 0) < 25
        and get_corpse_internal_load(normalized) < 30
        and int(normalized.get("empath", {}).get("vitality", 0) or 0) < 60
    )


def _corpse_selector_matches(selector, part_name):
    part_key = str(part_name or "").strip().lower()
    selector_key = str(selector or "").strip().lower()
    if not selector_key:
        return True
    if selector_key == "arm":
        return "arm" in part_key or "hand" in part_key
    if selector_key == "leg":
        return "leg" in part_key or "foot" in part_key
    if selector_key == "chest":
        return part_key in {"chest", "abdomen", "back"}
    if selector_key == "head":
        return part_key in {"head", "neck", "face", "eyes"}
    return part_key == selector_key


class Corpse(ObjectParent, DefaultObject):
    """Minimal corpse object used by death, depart, and resurrection flows."""

    RITUAL_STATE_ORDER = {
        "unprepared": 0,
        "prepared": 1,
        "stabilized": 2,
        "restored": 3,
        "bound": 4,
    }

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_corpse = True
        self.db.owner_id = None
        self.db.corpse_owner_id = None
        self.db.owner_name = self.key
        self.db.death_timestamp = 0.0
        self.db.time_of_death = 0.0
        self.db.death_type = "vitality"
        self.db.decay_time = 0.0
        self.db.decay_end_time = 0.0
        self.db.decay_stage = 0
        self.db.memory_time = 0.0
        self.db.memory_faded = False
        self.db.memory_loss_applied = False
        self.db.favor_snapshot = None
        self.db.favor_detail_snapshot = None
        self.db.condition = 100.0
        self.db.stabilized = False
        self.db.preserve_stacks = 0
        self.db.preparation_stacks = 0
        self.db.devotional_vigil_until = 0.0
        self.db.irrecoverable = False
        self.db.resurrection_failures = 0
        self.db.stored_coins = 0
        self.db.ammo_inventory = []
        self.db.recovery_allowed = []
        self.db.is_valid_for_revive = True
        self.db.ritual_state = "unprepared"
        self.db.memory_stable = False
        self.db.soul_bound = False
        self.db.prepared_by = None
        self.db.ritual_failures = 0
        self.db.ritual_quality = 0
        self.db.ritual_participants = []
        self.db.stage_contributors = {"prepare": [], "stabilize": [], "restore": [], "bind": []}
        self.db.ritual_quality_bonus_contributors = []
        self.db.specialization_bonus_stages = []
        self.db.empath_prep_totals = {}
        self.db.last_empath_prep_result = None
        self.db.wounds = normalize_corpse_wounds()
        self.locks.add("get:false()")

    def get_corpse_wounds(self):
        wounds = get_corpse_wounds(self)
        self.db.wounds = copy.deepcopy(wounds)
        return copy.deepcopy(wounds)

    def set_corpse_wounds(self, wounds):
        normalized = normalize_corpse_wounds(wounds)
        self.db.wounds = copy.deepcopy(normalized)
        return self.get_corpse_wounds()

    def get_empath_wounds(self):
        return dict(self.get_corpse_wounds().get("empath", {}))

    def sync_empath_wounds_from_resources(self):
        return self.get_empath_wounds()

    def sync_resources_from_empath_wounds(self):
        return self.get_empath_wounds()

    def get_empath_wound(self, wound_type):
        wound_key = str(wound_type or "").strip().lower()
        return max(0, int(self.get_empath_wounds().get(wound_key, 0) or 0))

    def set_empath_wound(self, wound_type, value):
        wound_key = str(wound_type or "").strip().lower()
        payload = self.get_corpse_wounds()
        if wound_key not in payload["empath"]:
            return 0
        payload["empath"][wound_key] = max(0, min(100, int(value or 0)))
        self.db.wounds = copy.deepcopy(payload)
        return int(payload["empath"][wound_key] or 0)

    def get_corpse_internal_total(self):
        payload = self.get_corpse_wounds()
        return max(0, sum(max(0, int((part or {}).get("internal", 0) or 0)) for part in payload.get("injuries", {}).values()))

    def get_corpse_bleed_total(self):
        payload = self.get_corpse_wounds()
        return _get_corpse_bleeding_points(payload.get("injuries"))

    def get_decay_total_window(self):
        death_time = float(getattr(self.db, "time_of_death", 0.0) or getattr(self.db, "death_timestamp", 0.0) or 0.0)
        decay_time = float(getattr(self.db, "decay_end_time", 0.0) or getattr(self.db, "decay_time", 0.0) or 0.0)
        if death_time <= 0.0 or decay_time <= death_time:
            return 0.0
        return max(0.0, decay_time - death_time)

    def refresh_decay_stage(self, now=None):
        now = float(now or time.time())
        total_window = self.get_decay_total_window()
        if total_window <= 0.0:
            stage = max(0, min(3, int(getattr(self.db, "decay_stage", 0) or 0)))
            self.db.decay_stage = stage
            return stage
        death_time = float(getattr(self.db, "time_of_death", 0.0) or getattr(self.db, "death_timestamp", 0.0) or now)
        elapsed_ratio = max(0.0, min(1.0, (now - death_time) / total_window))
        if elapsed_ratio >= 0.75:
            stage = 3
        elif elapsed_ratio >= 0.5:
            stage = 2
        elif elapsed_ratio >= 0.25:
            stage = 1
        else:
            stage = 0
        self.db.decay_stage = stage
        return stage

    def get_decay_stage(self, now=None):
        return self.refresh_decay_stage(now=now)

    def get_decay_stage_penalties(self, now=None):
        stage = self.get_decay_stage(now=now)
        penalties = dict(CORPSE_DECAY_STAGE_PENALTIES.get(stage, CORPSE_DECAY_STAGE_PENALTIES[3]))
        penalties["stage"] = stage
        return penalties

    def get_single_empath_prep_cap(self, handler=None):
        penalties = self.get_decay_stage_penalties()
        base_cap = CORPSE_SINGLE_EMPATH_PREP_CAP - (int(penalties.get("stage", 0) or 0) * 8)
        return max(24, int(base_cap))

    def get_empath_prep_totals(self):
        raw = dict(getattr(self.db, "empath_prep_totals", {}) or {})
        normalized = {}
        for key, value in raw.items():
            try:
                handler_id = int(key)
                total = int(value or 0)
            except (TypeError, ValueError):
                continue
            if handler_id > 0 and total > 0:
                normalized[handler_id] = total
        self.db.empath_prep_totals = normalized
        return dict(normalized)

    def get_empath_prep_remaining(self, handler):
        handler_id = int(getattr(handler, "id", 0) or 0)
        if handler_id <= 0:
            return self.get_single_empath_prep_cap(handler=handler)
        totals = self.get_empath_prep_totals()
        spent = int(totals.get(handler_id, 0) or 0)
        return max(0, self.get_single_empath_prep_cap(handler=handler) - spent)

    def record_empath_prep_contribution(self, handler, amount):
        handler_id = int(getattr(handler, "id", 0) or 0)
        if handler_id <= 0:
            return self.get_empath_prep_totals()
        totals = self.get_empath_prep_totals()
        totals[handler_id] = int(totals.get(handler_id, 0) or 0) + max(0, int(amount or 0))
        self.db.empath_prep_totals = totals
        return dict(totals)

    def is_revive_survivable(self):
        return is_stable(self.get_corpse_wounds())

    def reduce_corpse_wound(self, wound_type, amount, selector=None, handler=None):
        wound_key = str(wound_type or "").strip().lower()
        remaining = max(0, int(amount or 0))
        if remaining <= 0:
            return 0

        if handler is not None:
            remaining = min(remaining, self.get_empath_prep_remaining(handler))
            if remaining <= 0:
                self.db.last_empath_prep_result = "cap"
                return 0

        payload = self.get_corpse_wounds()
        current = max(0, int(payload.get("empath", {}).get(wound_key, 0) or 0))
        if current <= 0:
            self.db.last_empath_prep_result = "empty"
            return 0

        removed = 0
        injuries = payload.get("injuries", {})
        if wound_key == "bleeding":
            for part_name, part in injuries.items():
                if remaining <= 0:
                    break
                if not _corpse_selector_matches(selector, part_name):
                    continue
                current_bleed = max(0, int(part.get("bleed", 0) or 0))
                if current_bleed <= 0:
                    continue
                spent = min(current_bleed, remaining)
                part["bleed"] = current_bleed - spent
                remaining -= spent
                removed += spent
            if removed > 0:
                payload = _sync_corpse_aggregate_from_injuries(payload)
        elif wound_key == "vitality":
            field_order = ("internal", "external", "bruise") if str(selector or "").strip().lower() in {"chest", "head"} else ("external", "internal", "bruise")
            for part_name, part in injuries.items():
                if remaining <= 0:
                    break
                if selector and not _corpse_selector_matches(selector, part_name):
                    continue
                for field_name in field_order:
                    current_value = max(0, int(part.get(field_name, 0) or 0))
                    if current_value <= 0:
                        continue
                    spent = min(current_value, remaining)
                    part[field_name] = current_value - spent
                    remaining -= spent
                    removed += spent
                    if remaining <= 0:
                        break
            if removed > 0:
                payload = _sync_corpse_aggregate_from_injuries(payload)
        else:
            removed = min(current, remaining)
            payload["empath"][wound_key] = max(0, current - removed)

        self.db.wounds = copy.deepcopy(payload)
        if removed > 0 and handler is not None:
            self.record_empath_prep_contribution(handler, removed)
            self.db.last_empath_prep_result = "progress"
        return removed

    def get_ritual_state(self):
        state = str(getattr(self.db, "ritual_state", "unprepared") or "unprepared").strip().lower()
        if state not in self.RITUAL_STATE_ORDER:
            state = "unprepared"
        return state

    def set_ritual_state(self, state):
        normalized = str(state or "unprepared").strip().lower() or "unprepared"
        if normalized not in self.RITUAL_STATE_ORDER:
            normalized = "unprepared"
        self.db.ritual_state = normalized
        return normalized

    def has_reached_ritual_state(self, state):
        current = self.RITUAL_STATE_ORDER.get(self.get_ritual_state(), 0)
        target = self.RITUAL_STATE_ORDER.get(str(state or "unprepared").strip().lower(), 0)
        return current >= target

    def get_ritual_failures(self):
        return max(0, int(getattr(self.db, "ritual_failures", 0) or 0))

    def get_ritual_participants(self):
        raw = list(getattr(self.db, "ritual_participants", []) or [])
        normalized = sorted({int(entry) for entry in raw if isinstance(entry, int) or str(entry).isdigit()})
        self.db.ritual_participants = normalized
        return normalized

    def add_ritual_participant(self, character):
        char_id = int(getattr(character, "id", 0) or 0)
        if char_id <= 0:
            return self.get_ritual_participants(), False
        participants = set(self.get_ritual_participants())
        added = char_id not in participants
        participants.add(char_id)
        updated = sorted(participants)
        self.db.ritual_participants = updated
        return updated, added

    def get_stage_contributors(self):
        raw = dict(getattr(self.db, "stage_contributors", {}) or {})
        normalized = {}
        for stage in ("prepare", "stabilize", "restore", "bind"):
            entries = list(raw.get(stage, []) or [])
            normalized[stage] = sorted({int(entry) for entry in entries if isinstance(entry, int) or str(entry).isdigit()})
        self.db.stage_contributors = normalized
        return normalized

    def get_stage_contributor_ids(self, stage):
        return list(self.get_stage_contributors().get(str(stage or "").strip().lower(), []))

    def has_stage_contributor(self, stage, character):
        char_id = int(getattr(character, "id", 0) or 0)
        return char_id > 0 and char_id in set(self.get_stage_contributor_ids(stage))

    def add_stage_contributor(self, stage, character):
        stage_key = str(stage or "").strip().lower()
        contributors = self.get_stage_contributors()
        if stage_key not in contributors:
            return [], False
        char_id = int(getattr(character, "id", 0) or 0)
        if char_id <= 0:
            return list(contributors.get(stage_key, [])), False
        current = set(contributors.get(stage_key, []))
        added = char_id not in current
        current.add(char_id)
        contributors[stage_key] = sorted(current)
        self.db.stage_contributors = contributors
        return contributors[stage_key], added

    def get_unique_quality_bonus_contributors(self):
        raw = list(getattr(self.db, "ritual_quality_bonus_contributors", []) or [])
        normalized = sorted({int(entry) for entry in raw if isinstance(entry, int) or str(entry).isdigit()})
        self.db.ritual_quality_bonus_contributors = normalized
        return normalized

    def add_quality_bonus_contributor(self, character):
        char_id = int(getattr(character, "id", 0) or 0)
        if char_id <= 0:
            return self.get_unique_quality_bonus_contributors(), False
        contributors = set(self.get_unique_quality_bonus_contributors())
        if len(contributors) >= 4 and char_id not in contributors:
            return sorted(contributors), False
        added = char_id not in contributors
        contributors.add(char_id)
        updated = sorted(contributors)
        self.db.ritual_quality_bonus_contributors = updated
        return updated, added

    def get_specialization_bonus_stages(self):
        raw = list(getattr(self.db, "specialization_bonus_stages", []) or [])
        normalized = sorted({str(entry or "").strip().lower() for entry in raw if str(entry or "").strip()})
        self.db.specialization_bonus_stages = normalized
        return normalized

    def mark_specialization_bonus_stage(self, stage):
        stage_key = str(stage or "").strip().lower()
        stages = set(self.get_specialization_bonus_stages())
        added = stage_key not in stages
        stages.add(stage_key)
        updated = sorted(stages)
        self.db.specialization_bonus_stages = updated
        return updated, added

    def get_ritual_quality(self):
        return max(0, min(15, int(getattr(self.db, "ritual_quality", 0) or 0)))

    def set_ritual_quality(self, value):
        updated = max(0, min(15, int(value or 0)))
        self.db.ritual_quality = updated
        return updated

    def adjust_ritual_quality(self, amount):
        return self.set_ritual_quality(self.get_ritual_quality() + int(amount or 0))

    def regress_ritual_state(self, action=None):
        action_key = str(action or "").strip().lower()
        if action_key:
            updated = {
                "prepare": "unprepared",
                "stabilize": "prepared",
                "restore": "stabilized",
                "bind": "restored",
                "revive": "restored",
            }.get(action_key, self.get_ritual_state())
        else:
            current = self.get_ritual_state()
            updated = {
                "bound": "restored",
                "restored": "stabilized",
                "stabilized": "prepared",
                "prepared": "unprepared",
            }.get(current, "unprepared")
        self.set_ritual_state(updated)
        if updated != "bound":
            self.db.soul_bound = False
        if updated not in {"restored", "bound"}:
            self.db.memory_stable = False
        if updated not in {"stabilized", "restored", "bound"}:
            self.db.stabilized = False
        if updated == "unprepared":
            self.db.prepared_by = None
        return updated

    def record_ritual_failure(self, amount=1):
        amount = max(1, int(amount or 1))
        updated = self.get_ritual_failures() + amount
        self.db.ritual_failures = updated
        self.adjust_ritual_quality(-(2 * amount))
        if updated >= 2:
            self.db.memory_stable = False
        if updated >= 3:
            self.db.is_valid_for_revive = False
        return updated

    def get_group_stage_bonus_count(self, stage, pending_character_ids=None):
        contributors = set(self.get_stage_contributor_ids(stage))
        for char_id in list(pending_character_ids or []):
            if int(char_id or 0) > 0:
                contributors.add(int(char_id))
        return len(contributors)

    def get_decay_remaining(self):
        self.refresh_decay_stage()
        return max(0.0, float(getattr(self.db, "decay_time", 0.0) or 0.0) - time.time())

    def _get_decay_schedule_key(self):
        object_id = int(getattr(self, "id", 0) or 0)
        if object_id > 0:
            return f"corpse:decay:{object_id}"
        dbref = str(getattr(self, "dbref", "") or "").strip().lstrip("#")
        if dbref.isdigit():
            return f"corpse:decay:{dbref}"
        stable_name = str(getattr(self, "key", "corpse") or "corpse").strip().lower().replace(" ", "-")
        return f"corpse:decay:{stable_name}"

    def at_object_delete(self):
        self.cancel_decay_transition()
        return super().at_object_delete()

    def cancel_decay_transition(self):
        from world.systems.scheduler import cancel

        return cancel(self._get_decay_schedule_key())

    def schedule_decay_transition(self):
        from world.systems.scheduler import schedule
        from world.systems.time_model import SCHEDULED_EXPIRY

        decay_time = float(getattr(self.db, "decay_time", 0.0) or 0.0)
        if decay_time <= 0.0 or not getattr(self.db, "is_corpse", False):
            self.cancel_decay_transition()
            return None
        delay_seconds = max(0.0, decay_time - time.time())
        return schedule(
            delay_seconds,
            self._expire_decay_to_grave,
            key=self._get_decay_schedule_key(),
            system="world.corpse_decay",
            timing_mode=SCHEDULED_EXPIRY,
            expected_decay_time=decay_time,
        )

    def _expire_decay_to_grave(self, expected_decay_time=None):
        if not getattr(self.db, "is_corpse", False):
            return None
        if hasattr(self, "is_orphaned") and self.is_orphaned():
            self.delete()
            return None
        current_decay_time = float(getattr(self.db, "decay_time", 0.0) or 0.0)
        if current_decay_time <= 0.0:
            return None
        if expected_decay_time is not None and current_decay_time > float(expected_decay_time or 0.0) + 0.01:
            return None
        if time.time() + 0.01 < current_decay_time:
            return None
        owner = self.get_owner() if hasattr(self, "get_owner") else None
        if owner and hasattr(owner, "clear_death_corpse_link"):
            owner.clear_death_corpse_link()
        self.spill_ammo_to_room()
        self.delete()
        return None

    def get_memory_remaining(self):
        return max(0.0, float(getattr(self.db, "memory_time", 0.0) or 0.0) - time.time())

    def has_viable_memory(self):
        return self.get_memory_remaining() > 0 and not bool(getattr(self.db, "memory_faded", False))

    def get_memory_state(self):
        remaining = self.get_memory_remaining()
        if remaining <= 0 or bool(getattr(self.db, "memory_faded", False)):
            return "lost"
        if remaining >= 300:
            return "clear"
        if remaining >= 120:
            return "fading"
        return "critical"

    def get_resurrection_condition_state(self):
        condition = self.get_condition()
        decay_remaining = self.get_decay_remaining()
        decay_stage = self.get_decay_stage()
        if not self.has_viable_memory() or condition < 25 or decay_remaining <= 60 or decay_stage >= 3:
            return "DECAYING"
        if condition >= 75 and decay_remaining >= 360 and decay_stage == 0:
            return "INTACT"
        if condition >= 50 and decay_remaining >= 180 and decay_stage <= 1:
            return "FADING"
        return "CRITICAL"

    def extend_memory(self, seconds, stacks=1):
        current = max(time.time(), float(getattr(self.db, "memory_time", 0.0) or 0.0))
        self.db.memory_time = current + max(0.0, float(seconds or 0.0))
        self.db.memory_faded = False
        self.db.preserve_stacks = max(0, int(getattr(self.db, "preserve_stacks", 0) or 0)) + max(0, int(stacks or 0))
        return self.get_memory_remaining()

    def add_preparation(self, amount=1):
        updated = min(5, max(0, int(getattr(self.db, "preparation_stacks", 0) or 0)) + max(0, int(amount or 0)))
        self.db.preparation_stacks = updated
        return updated

    def apply_memory_loss(self):
        if bool(getattr(self.db, "memory_loss_applied", False)):
            return False
        self.db.memory_faded = True
        self.db.memory_loss_applied = True
        owner = self.get_owner()
        if owner and hasattr(owner, "adjust_exp_debt"):
            owner.adjust_exp_debt(25)
            owner.msg("You feel vital memories slipping beyond recall.")
        return True

    def get_condition(self):
        return max(0.0, min(100.0, float(getattr(self.db, "condition", 100.0) or 0.0)))

    def get_condition_tier(self):
        condition = self.get_condition()
        if condition >= 75:
            return "Fresh"
        if condition >= 50:
            return "Degrading"
        if condition >= 25:
            return "Damaged"
        return "Ruined"

    def update_condition_description(self):
        owner_name = self.db.owner_name or "a fallen adventurer"
        tier = self.get_condition_tier()
        condition = int(round(self.get_condition()))
        decay = self.get_decay_stage_penalties()
        if tier == "Fresh":
            detail = "The body lies still, warmth not yet fully gone."
        elif tier == "Degrading":
            detail = "The body shows clear signs of decay."
        elif tier == "Damaged":
            detail = "The corpse is marred by time and neglect."
        else:
            detail = "The remains are barely recognizable."
        stabilized = " The careful work of an Empath has slowed the worst of the decay." if bool(getattr(self.db, "stabilized", False)) else ""
        memory_state = self.get_memory_state()
        if memory_state == "clear":
            memory_detail = " The soul's memories still cling clearly to the remains."
        elif memory_state == "fading":
            memory_detail = " Lingering memories are beginning to fray."
        elif memory_state == "critical":
            memory_detail = " Only a fragile trace of memory remains."
        else:
            memory_detail = " The lingering memories have faded away."
        decay_detail = f" Decay Stage: {decay['stage']} ({decay['label']})."
        if self.db.owner_name:
            subject = f"The body of {owner_name} lies here."
        else:
            subject = "The body of a fallen adventurer lies here."
        self.db.desc = f"{subject} {detail} Condition: {condition}/100.{decay_detail}{stabilized}{memory_detail}"

    def adjust_condition(self, amount):
        current = self.get_condition()
        self.db.condition = max(0.0, min(100.0, current + float(amount or 0.0)))
        self.update_condition_description()
        return self.get_condition()

    def is_owner(self, player):
        return int(getattr(player, "id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0)

    def get_recovery_allowed_ids(self):
        raw = getattr(self.db, "recovery_allowed", None) or []
        allowed = set()
        for entry in raw:
            try:
                value = int(entry)
            except (TypeError, ValueError):
                continue
            if value > 0:
                allowed.add(value)
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id > 0:
            allowed.add(owner_id)
        return allowed

    def is_recovery_allowed(self, player):
        player_id = int(getattr(player, "id", 0) or 0)
        return player_id > 0 and player_id in self.get_recovery_allowed_ids()

    def grant_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0:
            allowed.add(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def revoke_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0 and player_id != owner_id:
            allowed.discard(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def get_owner(self):
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id <= 0:
            return None
        result = search_object(f"#{owner_id}")
        return result[0] if result else None

    def get_ammo_inventory(self):
        ammo = merge_ammo_stacks(getattr(self.db, "ammo_inventory", None) or [])
        self.db.ammo_inventory = list(ammo)
        return list(ammo)

    def set_ammo_inventory(self, stacks):
        self.db.ammo_inventory = merge_ammo_stacks(stacks)
        return self.get_ammo_inventory()

    def add_ammo_stacks(self, stacks):
        self.db.ammo_inventory = merge_ammo_stacks([*self.get_ammo_inventory(), *list(stacks or [])])
        return self.get_ammo_inventory()

    def spill_ammo_to_room(self):
        ammo = self.get_ammo_inventory()
        room = getattr(self, "location", None)
        if not ammo or room is None or not hasattr(room, "add_loose_ammo"):
            return []
        room.add_loose_ammo(ammo)
        self.db.ammo_inventory = []
        return ammo

    def is_orphaned(self):
        return self.get_owner() is None

    def get_favor_snapshot(self):
        snapshot = getattr(self.db, "favor_snapshot", None)
        return max(0, int(snapshot or 0))

    def get_favor_detail_snapshot(self):
        snapshot = getattr(self.db, "favor_detail_snapshot", None)
        return dict(snapshot) if isinstance(snapshot, Mapping) else None

    def _has_admin_access(self, accessing_obj):
        account = getattr(accessing_obj, "account", None)
        if not account:
            return False
        return account.check_permstring("Admin") or account.check_permstring("Developer")

    def access(self, accessing_obj, access_type="read", default=False, **kwargs):
        if access_type in {"view", "read", "search", "get"}:
            if self.is_recovery_allowed(accessing_obj) or self._has_admin_access(accessing_obj):
                return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)
            return False
        return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)

    def decay_to_grave(self, stored_coins=None, expires_at=None):
        if not getattr(self.db, "is_corpse", False):
            return None
        self.cancel_decay_transition()
        location = self.location
        owner = self.get_owner()
        grave = create_object(
            "typeclasses.grave.Grave",
            key=f"grave of {self.db.owner_name or self.key}",
            location=location,
            home=location,
        )
        grave.db.owner_id = self.db.owner_id
        grave.db.owner_name = self.db.owner_name or self.key
        grave.db.created_at = time.time()
        grave.db.creation_time = grave.db.created_at
        grave.db.recovery_allowed = [int(getattr(self.db, "owner_id", 0) or 0)] if int(getattr(self.db, "owner_id", 0) or 0) > 0 else []
        grave.db.last_grave_damage_tick = time.time()
        grave.db.expires_at = float(expires_at or (time.time() + (30 * 60)))
        grave.db.expiry_time = grave.db.expires_at
        grave.db.expiry_warned = False
        grave.refresh_description()
        grave.db.corpse_condition = self.get_condition()

        grave.db.coins = max(0, int(getattr(self.db, "stored_coins", 0) if stored_coins is None else stored_coins or 0))
        grave.db.stored_coins = grave.db.coins
        self.spill_ammo_to_room()
        stored_items = []
        for item in list(self.contents):
            if item.move_to(grave, quiet=True):
                item.db.grave_damage = 0
                stored_items.append(item.id)
        grave.db.items = list(dict.fromkeys(stored_items))
        grave.db.stored_items = list(grave.db.items)
        if hasattr(grave, "sync_storage_metadata"):
            grave.sync_storage_metadata()
        grave.scripts.add("typeclasses.scripts.GraveMaintenanceScript")

        if owner and int(getattr(owner.db, "last_corpse_id", 0) or 0) == int(self.id or 0):
            owner.db.last_corpse_id = None
            if hasattr(owner, "sync_client_state"):
                owner.sync_client_state()
            if hasattr(owner, "emit_death_event"):
                owner.emit_death_event("on_grave_created", grave=grave, corpse=self)

        self.delete()
        return grave
