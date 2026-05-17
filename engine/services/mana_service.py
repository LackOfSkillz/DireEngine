from __future__ import annotations

import math
import random
import time
from collections.abc import Mapping

from domain.mana.constants import (
    DEFAULT_GLOBAL_MANA_MODIFIER,
    DEFAULT_PROFESSION_MANA_MODIFIER,
    DEFAULT_ROOM_MANA,
    DEVOTION_PULSE_INTERVAL,
    MANA_REALMS,
    MANA_PULSE_INTERVAL,
)
from domain.mana.backlash import (
    calculate_backlash_chance as calculate_margin_backlash_chance,
    calculate_backlash_severity,
    calculate_cast_margin,
    calculate_control_score,
    calculate_spell_difficulty,
    calculate_strain_penalty,
    resolve_backlash_payload,
    resolve_success_band,
)
from domain.mana.rules import (
    calculate_ambient_floor_required,
    calculate_attunement_regen,
    calculate_backlash_chance,
    calculate_cyclic_drain,
    calculate_cyclic_control_margin,
    calculate_effective_env_mana,
    calculate_final_spell_power,
    calculate_harness_cost,
    calculate_harness_efficiency,
    calculate_prep_cost,
    clamp,
)
from engine.services.result import ActionResult


_SCHEDULER_CALLBACKS_REGISTERED = False
MANA_REGEN_EVENT = "mana_regen"
MANA_DEVOTION_EVENT = "mana_devotion"
MANA_PREPARED_READY_EVENT = "prepared_ready"
MANA_PREPARED_EXPIRE_EVENT = "prepared_expire"


def _get_scheduler_api():
    from world.systems.scheduler import cancel_event, register_event_callback, schedule_event

    return cancel_event, register_event_callback, schedule_event


def _ensure_scheduler_callbacks_registered():
    global _SCHEDULER_CALLBACKS_REGISTERED
    if _SCHEDULER_CALLBACKS_REGISTERED:
        return True
    try:
        _, register_event_callback, _ = _get_scheduler_api()
    except Exception:
        return False

    register_event_callback("mana:process_regen", _callback_process_mana_regen)
    register_event_callback("mana:process_devotion", _callback_process_devotion)
    register_event_callback("mana:prepared_ready", _callback_transition_prepared_spell)
    register_event_callback("mana:prepared_expire", _callback_expire_prepared_spell)
    _SCHEDULER_CALLBACKS_REGISTERED = True
    return True


class ManaService:

    BAND_MULTIPLIERS = {
        "excellent": 1.15,
        "solid": 1.00,
        "partial": 0.65,
        "failure": 0.0,
        "backlash": 0.0,
    }

    @staticmethod
    def _coerce_float(value, default=0.0):
        if value is None:
            return float(default)
        return float(value)

    @staticmethod
    def _coerce_int(value, default=0):
        if value is None:
            return int(default)
        return int(value)

    @staticmethod
    def _apply_integer_multiplier(base_amount, multiplier):
        amount = max(0, ManaService._coerce_int(base_amount, default=0))
        if amount <= 0:
            return 0
        scaled = int(float(amount) * float(multiplier or 1.0))
        return max(1, scaled)

    @staticmethod
    def _get_db_holder(obj):
        if obj is None:
            return None
        return getattr(obj, "db", None)

    @staticmethod
    def _get_ndb_holder(obj):
        if obj is None:
            return None
        return getattr(obj, "ndb", None)

    @staticmethod
    def _get_mapping_attr(holder, attr_name):
        if holder is None:
            return None
        value = getattr(holder, attr_name, None)
        if not isinstance(value, Mapping):
            return None
        return dict(value)

    @staticmethod
    def _set_mapping_attr(holder, attr_name, value):
        if holder is None:
            return dict(value)
        normalized = dict(value)
        setattr(holder, attr_name, normalized)
        return normalized

    @staticmethod
    def _normalize_room_mana_map(mana_map):
        normalized = dict(DEFAULT_ROOM_MANA)
        if isinstance(mana_map, Mapping):
            for realm in MANA_REALMS:
                if realm in mana_map and mana_map.get(realm) is not None:
                    normalized[realm] = ManaService._coerce_float(mana_map.get(realm), default=normalized[realm])
        return normalized

    @staticmethod
    def _normalize_attunement_map(attunement_map):
        current_value = 0.0
        maximum_value = 0.0
        if isinstance(attunement_map, Mapping):
            if attunement_map.get("current") is not None:
                current_value = ManaService._coerce_float(attunement_map.get("current"))
            if attunement_map.get("max") is not None:
                maximum_value = ManaService._coerce_float(attunement_map.get("max"))
        maximum_value = max(0.0, maximum_value)
        current_value = clamp(current_value, 0.0, maximum_value) if maximum_value > 0.0 else max(0.0, current_value)
        return {"current": current_value, "max": maximum_value}

    @staticmethod
    def _normalize_prepared_mana_map(prepared_map):
        if not isinstance(prepared_map, Mapping):
            return None
        realm = str(prepared_map.get("realm", "") or "").strip().lower()
        if realm not in MANA_REALMS:
            return None
        mana_input = ManaService._coerce_int(
            prepared_map.get("intended_mana", prepared_map.get("mana_input")),
            default=0,
        )
        prep_cost = ManaService._coerce_int(prepared_map.get("prep_cost"), default=0)
        held_mana = ManaService._coerce_int(prepared_map.get("held_mana"), default=0)
        normalized = {
            "realm": realm,
            "mana_input": max(0, mana_input),
            "intended_mana": max(0, mana_input),
            "prep_cost": max(0, prep_cost),
            "held_mana": max(0, held_mana),
            "ready": bool(prepared_map.get("ready", True)),
        }
        if prepared_map.get("spell_id") is not None:
            normalized["spell_id"] = str(prepared_map.get("spell_id") or "").strip().lower()
        if prepared_map.get("prep_started_at") is not None:
            normalized["prep_started_at"] = max(0.0, ManaService._coerce_float(prepared_map.get("prep_started_at"), default=0.0))
        if prepared_map.get("min_prep_time") is not None:
            normalized["min_prep_time"] = max(0.0, ManaService._coerce_float(prepared_map.get("min_prep_time"), default=0.0))
        if prepared_map.get("expiry_at") is not None:
            normalized["expiry_at"] = max(0.0, ManaService._coerce_float(prepared_map.get("expiry_at"), default=0.0))
        if prepared_map.get("min_prep") is not None:
            normalized["min_prep"] = max(0, ManaService._coerce_int(prepared_map.get("min_prep"), default=0))
        if prepared_map.get("max_prep") is not None:
            normalized["max_prep"] = max(0, ManaService._coerce_int(prepared_map.get("max_prep"), default=0))
        if prepared_map.get("safe_mana") is not None:
            normalized["safe_mana"] = max(0, ManaService._coerce_int(prepared_map.get("safe_mana"), default=0))
        if prepared_map.get("mana_min") is not None:
            normalized["mana_min"] = max(0, ManaService._coerce_int(prepared_map.get("mana_min"), default=0))
        if prepared_map.get("mana_max") is not None:
            normalized["mana_max"] = max(0, ManaService._coerce_int(prepared_map.get("mana_max"), default=0))
        if prepared_map.get("diff_per_extra_mana") is not None:
            normalized["diff_per_extra_mana"] = max(0.0, ManaService._coerce_float(prepared_map.get("diff_per_extra_mana"), default=0.0))
        if prepared_map.get("provenance") is not None:
            normalized["provenance"] = str(prepared_map.get("provenance", "") or "")
        if prepared_map.get("tier") is not None:
            normalized["tier"] = max(0, ManaService._coerce_int(prepared_map.get("tier"), default=0))
        if prepared_map.get("base_difficulty") is not None:
            normalized["base_difficulty"] = ManaService._coerce_float(prepared_map.get("base_difficulty"), default=0.0)
        if prepared_map.get("spell_category") is not None:
            normalized["spell_category"] = str(prepared_map.get("spell_category", "") or "")
        return normalized

    @staticmethod
    def _get_room_mana(room, realm):
        db_holder = ManaService._get_db_holder(room)
        mana_map = ManaService._normalize_room_mana_map(ManaService._get_mapping_attr(db_holder, "mana"))
        ManaService._set_mapping_attr(db_holder, "mana", mana_map)
        return ManaService._coerce_float(mana_map.get(realm), default=DEFAULT_ROOM_MANA[realm])

    @staticmethod
    def get_environmental_modifier(room, mana_type):
        normalized_mana = str(mana_type or "").strip().lower()
        if normalized_mana not in MANA_REALMS:
            return 1.0
        # ROOM IS CONTEXT ONLY.
        # Spell resolution may read environmental modifiers from the room,
        # but spell execution must never mutate that room state directly.
        db_holder = ManaService._get_db_holder(room)
        env_map = ManaService._get_mapping_attr(db_holder, "environmental_mana")
        if not isinstance(env_map, Mapping):
            return 1.0
        value = env_map.get(normalized_mana)
        if value is None:
            return 1.0
        return max(0.1, ManaService._coerce_float(value, default=1.0))

    @staticmethod
    def _get_attunement_state(character):
        if character is not None and hasattr(character, "ensure_core_defaults"):
            character.ensure_core_defaults()
        db_holder = ManaService._get_db_holder(character)
        attunement_map = ManaService._get_mapping_attr(db_holder, "attunement")
        if attunement_map is None and db_holder is not None:
            current_value = getattr(db_holder, "attunement", None)
            maximum_value = getattr(db_holder, "max_attunement", None)
            if current_value is not None or maximum_value is not None:
                attunement_map = {
                    "current": current_value,
                    "max": maximum_value,
                }
        attunement = ManaService._normalize_attunement_map(attunement_map)
        if db_holder is not None:
            if isinstance(getattr(db_holder, "attunement", None), Mapping):
                ManaService._set_mapping_attr(db_holder, "attunement", attunement)
            else:
                setattr(db_holder, "attunement", attunement["current"])
                setattr(db_holder, "max_attunement", attunement["max"])
        return attunement

    @staticmethod
    def _set_attunement_state(character, current, maximum):
        db_holder = ManaService._get_db_holder(character)
        attunement = ManaService._normalize_attunement_map({"current": current, "max": maximum})
        if db_holder is None:
            return attunement
        if isinstance(getattr(db_holder, "attunement", None), Mapping):
            return ManaService._set_mapping_attr(db_holder, "attunement", attunement)
        setattr(db_holder, "attunement", attunement["current"])
        setattr(db_holder, "max_attunement", attunement["max"])
        return attunement

    @staticmethod
    def _get_prepared_mana_state(character):
        ndb_holder = ManaService._get_ndb_holder(character)
        prepared = ManaService._normalize_prepared_mana_map(ManaService._get_mapping_attr(ndb_holder, "prepared_mana"))
        if prepared is None:
            return None
        return ManaService._set_mapping_attr(ndb_holder, "prepared_mana", prepared)

    @staticmethod
    def _set_prepared_mana_state(character, state_dict):
        ndb_holder = ManaService._get_ndb_holder(character)
        prepared = ManaService._normalize_prepared_mana_map(state_dict)
        if prepared is None:
            return None
        return ManaService._set_mapping_attr(ndb_holder, "prepared_mana", prepared)

    @staticmethod
    def _get_harnessed_mana_state(character):
        db_holder = ManaService._get_db_holder(character)
        if db_holder is None:
            return 0
        amount = max(0, ManaService._coerce_int(getattr(db_holder, "harnessed_mana", 0), default=0))
        setattr(db_holder, "harnessed_mana", amount)
        return amount

    @staticmethod
    def _set_harnessed_mana_state(character, amount):
        db_holder = ManaService._get_db_holder(character)
        normalized = max(0, ManaService._coerce_int(amount, default=0))
        if db_holder is not None:
            setattr(db_holder, "harnessed_mana", normalized)
        return normalized

    @staticmethod
    def _get_devotion_percent(character):
        if character is None:
            return 0.0
        if hasattr(character, "get_devotion") and hasattr(character, "get_devotion_max"):
            maximum = ManaService._coerce_float(character.get_devotion_max(), default=0.0)
            current = ManaService._coerce_float(character.get_devotion(), default=0.0)
            if maximum <= 0.0:
                return 0.0
            return clamp(current / maximum, 0.0, 1.0)

        db_holder = ManaService._get_db_holder(character)
        if db_holder is None:
            return 0.0
        maximum = getattr(db_holder, "devotion_max", None)
        if maximum is None:
            maximum = getattr(db_holder, "max_devotion", None)
        current = getattr(db_holder, "devotion_current", None)
        if current is None:
            current = getattr(db_holder, "devotion", None)
        maximum_value = ManaService._coerce_float(maximum, default=0.0)
        current_value = ManaService._coerce_float(current, default=0.0)
        if maximum_value <= 0.0:
            return 0.0
        return clamp(current_value / maximum_value, 0.0, 1.0)

    @staticmethod
    def _get_shock_ratio(character):
        if character is None:
            return 0.0
        if hasattr(character, "get_empath_shock"):
            shock = ManaService._coerce_float(character.get_empath_shock(), default=0.0)
            return clamp(shock / 100.0, 0.0, 1.0)
        db_holder = ManaService._get_db_holder(character)
        if db_holder is None:
            return 0.0
        shock = getattr(db_holder, "empath_shock", None)
        if shock is None:
            shock = getattr(db_holder, "shock", None)
        return clamp(ManaService._coerce_float(shock, default=0.0) / 100.0, 0.0, 1.0)

    @staticmethod
    def _is_profession(character, profession):
        if character is None:
            return False
        normalized = str(profession or "").strip().lower()
        if hasattr(character, "is_profession"):
            return bool(character.is_profession(normalized))
        db_holder = ManaService._get_db_holder(character)
        if db_holder is None:
            return False
        return str(getattr(db_holder, "profession", "") or "").strip().lower() == normalized

    @staticmethod
    def _get_profession_env_modifier(character, realm):
        normalized_realm = str(realm or "").strip().lower()
        if normalized_realm == "holy" and ManaService._is_profession(character, "cleric"):
            return 1.0 + (ManaService._get_devotion_percent(character) * 0.25)

        if normalized_realm == "elemental" and ManaService._is_profession(character, "warrior mage"):
            db_holder = ManaService._get_db_holder(character)
            alignment_bonus = 0.0 if db_holder is None else ManaService._coerce_float(getattr(db_holder, "elemental_alignment_bonus", None), default=0.0)
            return 1.0 + alignment_bonus

        return DEFAULT_PROFESSION_MANA_MODIFIER

    @staticmethod
    def _get_profession_cast_modifier(character, realm):
        normalized_realm = str(realm or "").strip().lower()
        profession = ManaService._get_profession_name(character)
        if profession in {"warrior mage", "warrior_mage"} and normalized_realm == "elemental":
            return 1.12
        if profession == "cleric" and normalized_realm == "holy":
            return 1.05
        if profession in {"moon mage", "moon_mage"} and normalized_realm == "lunar":
            return 0.95
        return 1.0

    @staticmethod
    def _get_profession_name(character):
        if character is None:
            return ""
        if hasattr(character, "get_profession"):
            return str(character.get_profession() or "").strip().lower()
        db_holder = ManaService._get_db_holder(character)
        if db_holder is not None:
            stored_profession = getattr(db_holder, "profession", None)
            if stored_profession is not None:
                return str(stored_profession or "").strip().lower()
        return str(getattr(character, "profession", "") or "").strip().lower()

    @staticmethod
    def _get_moon_mage_effective_env(character):
        db_holder = ManaService._get_db_holder(character)
        if db_holder is None:
            return 0.2
        lunar_global_state = ManaService._coerce_float(getattr(db_holder, "lunar_global_state", None), default=1.0)
        celestial_alignment = ManaService._coerce_float(getattr(db_holder, "celestial_alignment_modifier", None), default=1.0)
        weather_modifier = ManaService._coerce_float(getattr(db_holder, "weather_modifier", None), default=1.0)
        return clamp(lunar_global_state * celestial_alignment * weather_modifier, 0.2, 2.0)

    @staticmethod
    def _get_empath_healing_modifier(character):
        if character is not None and hasattr(character, "get_empath_healing_modifier"):
            return ManaService._coerce_float(character.get_empath_healing_modifier(), default=1.0)
        return 1.0 - (ManaService._get_shock_ratio(character) * 0.80)

    @staticmethod
    def _get_effective_env_mana(character, room, realm, global_modifier=DEFAULT_GLOBAL_MANA_MODIFIER):
        normalized_realm = str(realm or "").strip().lower()
        if ManaService._is_profession(character, "moon mage") and normalized_realm == "lunar":
            return ManaService._get_moon_mage_effective_env(character) * ManaService.get_environmental_modifier(room, normalized_realm)

        room_mana = ManaService._get_room_mana(room, normalized_realm)
        profession_modifier = ManaService._get_profession_env_modifier(character, normalized_realm)
        environmental_modifier = ManaService.get_environmental_modifier(room, normalized_realm)
        return calculate_effective_env_mana(room_mana * environmental_modifier, global_modifier, profession_modifier)

    @staticmethod
    def _build_control_context(character, primary_magic_skill, attunement_state=None):
        state = dict(attunement_state or {})
        return {
            "primary_magic_skill": ManaService._coerce_float(primary_magic_skill, default=0.0),
            "attunement_skill": ManaService._coerce_float(character.get_skill("attunement"), default=0.0) if character is not None and hasattr(character, "get_skill") else 0.0,
            "arcana_skill": ManaService._coerce_float(character.get_skill("arcana"), default=0.0) if character is not None and hasattr(character, "get_skill") else 0.0,
            "intelligence": ManaService._coerce_float(character.get_stat("intelligence"), default=0.0) if character is not None and hasattr(character, "get_stat") else 0.0,
            "discipline": ManaService._coerce_float(character.get_stat("discipline"), default=0.0) if character is not None and hasattr(character, "get_stat") else 0.0,
            "focus_state_bonus": 0.0,
            "profession": ManaService._get_profession_name(character),
            "attunement_current": ManaService._coerce_float(state.get("current"), default=0.0),
            "attunement_max": ManaService._coerce_float(state.get("max"), default=0.0),
        }

    @staticmethod
    def _get_spell_profile(character, prepared, primary_magic_skill, effective_env_mana):
        prepared_map = dict(prepared or {})
        tier = max(1, ManaService._coerce_int(prepared_map.get("tier"), default=1))
        mana_input = max(0, ManaService._coerce_int(prepared_map.get("mana_input"), default=0))
        spell_id = str(prepared_map.get("spell_id", "") or "").strip().lower()
        base_difficulty = ManaService._coerce_float(prepared_map.get("base_difficulty"), default=10.0 + tier * 3.0)
        difficulty_modifier = ManaService._coerce_int(
            prepared_map.get("spell_difficulty_modifier"),
            default=ManaService._get_spell_difficulty_modifier(character, spell_id),
        )
        return {
            "base_difficulty": max(0.0, base_difficulty + float(difficulty_modifier)),
            "base_difficulty_unmodified": base_difficulty,
            "safe_mana": max(1, ManaService._coerce_int(prepared_map.get("safe_mana"), default=max(1, mana_input))),
            "mana_min": max(1, ManaService._coerce_int(prepared_map.get("mana_min"), default=max(1, mana_input))),
            "mana_max": max(1, ManaService._coerce_int(prepared_map.get("mana_max"), default=max(1, mana_input))),
            "diff_per_extra_mana": max(0.0, ManaService._coerce_float(prepared_map.get("diff_per_extra_mana"), default=0.0)),
            "tier": tier,
            "mana_input": mana_input,
            "spell_id": spell_id,
            "spell_difficulty_modifier": int(difficulty_modifier),
            "realm": prepared_map.get("realm", ""),
            "profession": ManaService._get_profession_name(character),
            "primary_magic_skill": ManaService._coerce_float(primary_magic_skill, default=0.0),
            "effective_env_mana": ManaService._coerce_float(effective_env_mana, default=1.0),
            "spell_category": str(prepared_map.get("spell_category", prepared_map.get("category", "utility")) or "utility"),
            "min_prep_time": ManaService._coerce_float(prepared_map.get("min_prep_time"), default=0.0),
            "provenance": str(prepared_map.get("provenance", "") or ""),
        }

    @staticmethod
    def _get_spell_difficulty_modifier(character, spell_id):
        normalized_spell_id = str(spell_id or "").strip().lower()
        if not normalized_spell_id:
            return 0
        try:
            from domain.spells.spell_definitions import get_spell
            from engine.services.ranger_saf_service import RangerSafService
        except Exception:
            return 0

        spell = get_spell(normalized_spell_id)
        if spell is None:
            return 0
        return int(RangerSafService.get_spellcasting_modifier(character, spell) or 0)

    @staticmethod
    def _apply_backlash_payload(character, backlash_payload):
        from engine.services.feat_service import FeatService

        payload = dict(backlash_payload or {})
        attunement_state = ManaService._get_attunement_state(character)
        attunement_loss = int(
            math.ceil(
                ManaService._coerce_float(attunement_state.get("max"), default=0.0)
                * max(0.0, ManaService._coerce_float(payload.get("attunement_burn_ratio"), default=0.0))
            )
        )
        if attunement_loss > 0:
            ManaService.spend_attunement(character, attunement_loss)

        vitality_loss = max(0, ManaService._coerce_int(payload.get("vitality_loss"), default=0))
        if vitality_loss > 0:
            vitality_loss = ManaService._apply_integer_multiplier(
                vitality_loss,
                FeatService.get_modifier(character, "backlash_injury_multiplier"),
            )
        if vitality_loss > 0 and character is not None and hasattr(character, "set_hp"):
            current_hp = ManaService._coerce_int(getattr(getattr(character, "db", None), "hp", None), default=0)
            character.set_hp(current_hp - vitality_loss)

        devotion_loss = 0
        devotion_loss_ratio = max(0.0, ManaService._coerce_float(payload.get("devotion_loss_ratio"), default=0.0))
        if devotion_loss_ratio > 0.0 and character is not None and hasattr(character, "get_devotion_max"):
            devotion_loss = int(round(ManaService._coerce_float(character.get_devotion_max(), default=0.0) * devotion_loss_ratio))
            if devotion_loss > 0 and hasattr(character, "adjust_devotion"):
                character.adjust_devotion(-devotion_loss, sync=False)

        shock_gain = max(0, ManaService._coerce_int(payload.get("shock_gain"), default=0))
        if shock_gain > 0:
            if character is not None and hasattr(character, "adjust_empath_shock"):
                character.adjust_empath_shock(shock_gain)
            else:
                db_holder = ManaService._get_db_holder(character)
                if db_holder is not None:
                    current_shock = ManaService._coerce_int(getattr(db_holder, "empath_shock", None), default=0)
                    setattr(db_holder, "empath_shock", current_shock + shock_gain)

        focus_penalty_duration = max(0, ManaService._coerce_int(payload.get("focus_penalty_duration"), default=0))
        if focus_penalty_duration > 0 and character is not None and hasattr(character, "set_state"):
            character.set_state("mana_focus_penalty", {"duration": focus_penalty_duration, "severity": payload.get("severity", 1)})

        return {
            "attunement_loss": attunement_loss,
            "devotion_loss": devotion_loss,
            "shock_gain": shock_gain,
            "vitality_loss": vitality_loss,
            "focus_penalty_duration": focus_penalty_duration,
        }

    @staticmethod
    def can_prepare_spell(character, room, realm, mana_input, min_prep, max_prep, spell_id=None, min_prep_time=None, expiry_window=None):
        normalized_realm = str(realm or "").strip().lower()
        if character is None:
            return ActionResult.fail(errors=["Missing character."], data={"realm": normalized_realm})
        if room is None:
            return ActionResult.fail(errors=["Missing room."], data={"realm": normalized_realm})
        if normalized_realm not in MANA_REALMS:
            return ActionResult.fail(errors=["Invalid mana realm."], data={"realm": normalized_realm})

        mana_input_value = ManaService._coerce_int(mana_input, default=0)
        min_prep_value = ManaService._coerce_int(min_prep, default=0)
        max_prep_value = ManaService._coerce_int(max_prep, default=0)
        if mana_input_value < min_prep_value or mana_input_value > max_prep_value:
            return ActionResult.fail(
                errors=["Mana input is outside the allowed preparation range."],
                data={
                    "realm": normalized_realm,
                    "mana_input": mana_input_value,
                    "min_prep": min_prep_value,
                    "max_prep": max_prep_value,
                },
            )

        effective_env_mana = ManaService._get_effective_env_mana(character, room, normalized_realm)
        environmental_modifier = ManaService.get_environmental_modifier(room, normalized_realm)
        ambient_floor_required = calculate_ambient_floor_required(min_prep_value)
        prep_cost = calculate_prep_cost(mana_input_value, effective_env_mana)
        attunement = ManaService._get_attunement_state(character)

        if effective_env_mana * 100.0 < float(ambient_floor_required):
            return ActionResult.fail(
                errors=["Ambient mana is too weak to shape the spell."],
                data={
                    "realm": normalized_realm,
                    "mana_input": mana_input_value,
                    "effective_env_mana": effective_env_mana,
                    "environmental_mana_modifier": environmental_modifier,
                    "ambient_floor_required": ambient_floor_required,
                    "prep_cost": prep_cost,
                },
            )

        if ManaService._coerce_float(attunement.get("current"), default=0.0) < float(mana_input_value):
            return ActionResult.fail(
                errors=["Not enough attunement."],
                data={
                    "realm": normalized_realm,
                    "mana_input": mana_input_value,
                    "effective_env_mana": effective_env_mana,
                    "environmental_mana_modifier": environmental_modifier,
                    "ambient_floor_required": ambient_floor_required,
                    "prep_cost": prep_cost,
                    "required_attunement": mana_input_value,
                    "attunement_current": ManaService._coerce_float(attunement.get("current"), default=0.0),
                },
            )

        return ActionResult.ok(
            data={
                "spell_id": spell_id,
                "realm": normalized_realm,
                "mana_input": mana_input_value,
                "min_prep": min_prep_value,
                "max_prep": max_prep_value,
                "min_prep_time": max(0.0, ManaService._coerce_float(min_prep_time, default=0.0)),
                "expiry_window": max(0.0, ManaService._coerce_float(expiry_window, default=0.0)),
                "effective_env_mana": effective_env_mana,
                "environmental_mana_modifier": environmental_modifier,
                "ambient_floor_required": ambient_floor_required,
                "prep_cost": prep_cost,
            }
        )

    @staticmethod
    def spend_attunement(character, amount):
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        maximum = ManaService._coerce_float(attunement.get("max"), default=0.0)
        updated = max(0.0, current - ManaService._coerce_float(amount, default=0.0))
        return ManaService._set_attunement_state(character, updated, maximum)

    @staticmethod
    def restore_attunement(character, amount):
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        maximum = ManaService._coerce_float(attunement.get("max"), default=0.0)
        updated = min(maximum, current + ManaService._coerce_float(amount, default=0.0))
        return ManaService._set_attunement_state(character, updated, maximum)

    @staticmethod
    def set_attunement_max(character, maximum):
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        maximum_value = max(0.0, ManaService._coerce_float(maximum, default=0.0))
        updated_current = min(current, maximum_value)
        return ManaService._set_attunement_state(character, updated_current, maximum_value)

    @staticmethod
    def clear_prepared_mana(character):
        ManaService.cancel_prepared_spell_timers(character)
        ndb_holder = ManaService._get_ndb_holder(character)
        if ndb_holder is not None:
            setattr(ndb_holder, "prepared_mana", None)
        sync_state = getattr(character, "_sync_prepared_spell_state_from_mana", None)
        if callable(sync_state):
            sync_state(None)

    @staticmethod
    def transition_to_full_prep(character, payload=None):
        _payload = dict(payload or {})
        prepared = ManaService._get_prepared_mana_state(character)
        if prepared is None:
            return ActionResult.ok(data={"transitioned": False, "reason": "missing_prepared_spell"})
        if bool(prepared.get("ready", False)):
            return ActionResult.ok(data={"transitioned": False, "reason": "already_ready", "prepared_mana": dict(prepared)})
        prepared["ready"] = True
        updated = ManaService._set_prepared_mana_state(character, prepared)
        sync_state = getattr(character, "_sync_prepared_spell_state_from_mana", None)
        if callable(sync_state):
            sync_state(updated)
        return ActionResult.ok(data={"transitioned": True, "prepared_mana": dict(updated or {})})

    @staticmethod
    def expire_prepared_spell(character, payload=None):
        _payload = dict(payload or {})
        prepared = ManaService._get_prepared_mana_state(character)
        if prepared is None:
            return ActionResult.ok(data={"expired": False, "reason": "missing_prepared_spell"})
        expired = dict(prepared)
        ManaService.clear_prepared_mana(character)
        return ActionResult.ok(data={"expired": True, "prepared_mana": expired})

    @staticmethod
    def release_harnessed_mana(character):
        released = ManaService._get_harnessed_mana_state(character)
        ManaService._set_harnessed_mana_state(character, 0)
        prepared = ManaService._get_prepared_mana_state(character)
        if prepared is not None:
            prepared["held_mana"] = 0
            updated = ManaService._set_prepared_mana_state(character, prepared)
            sync_state = getattr(character, "_sync_prepared_spell_state_from_mana", None)
            if callable(sync_state):
                sync_state(updated)
        return ActionResult.ok(data={"released": released, "held_mana": 0})

    @staticmethod
    def compute_max_harnessable(character, attunement_skill=None, arcana_skill=None):
        if attunement_skill is None and character is not None and hasattr(character, "get_skill"):
            attunement_skill = character.get_skill("attunement")
        if arcana_skill is None and character is not None and hasattr(character, "get_skill"):
            arcana_skill = character.get_skill("arcana")
        efficiency = calculate_harness_efficiency(
            ManaService._coerce_float(attunement_skill, default=0.0),
            ManaService._coerce_float(arcana_skill, default=0.0),
        )
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        max_requested = int(math.floor(current * efficiency))
        return max(0, max_requested)

    @staticmethod
    def calculate_cyclic_tick_cost(safe_mana, final_spell_power, effect_profile=None):
        profile = dict(effect_profile or {})
        scale = max(0.05, ManaService._coerce_float(profile.get("mana_per_tick_scale"), default=0.15))
        baseline = min(
            max(1.0, ManaService._coerce_float(safe_mana, default=1.0)),
            max(1.0, ManaService._coerce_float(final_spell_power, default=1.0)),
        )
        return max(1, int(round(baseline * scale)))

    @staticmethod
    def consume_mana_for_cyclic(character, amount, sustain_source, sustain_ref=None):
        from engine.services.feat_service import FeatService

        requested_cost = max(0, ManaService._coerce_int(amount, default=0))
        source = str(sustain_source or "").strip().lower().replace("-", "_").replace(" ", "_")
        cost = ManaService._apply_integer_multiplier(
            requested_cost,
            FeatService.get_modifier(character, "cyclic_drain_multiplier"),
        )
        if source == "attunement":
            cost = ManaService._apply_integer_multiplier(
                cost,
                FeatService.get_modifier(character, "harness_attunement_cost_multiplier"),
            )

        if source == "held_mana":
            held_current = ManaService._get_harnessed_mana_state(character)
            if held_current < cost:
                return ActionResult.fail(
                    errors=["Not enough held mana to sustain that cyclic spell."],
                    data={
                        "requested": cost,
                        "requested_base_cost": requested_cost,
                        "remaining_mana": held_current,
                        "remaining_held_mana": held_current,
                        "sustain_source": "held_mana",
                        "sustain_ref": sustain_ref,
                        "reason": "insufficient_held_mana",
                    },
                )
            remaining = ManaService._set_harnessed_mana_state(character, held_current - cost)
            prepared = ManaService._get_prepared_mana_state(character)
            if prepared is not None:
                prepared["held_mana"] = remaining
                updated = ManaService._set_prepared_mana_state(character, prepared)
                sync_state = getattr(character, "_sync_prepared_spell_state_from_mana", None)
                if callable(sync_state):
                    sync_state(updated)
            return ActionResult.ok(
                data={
                    "consumed": cost,
                    "requested_base_cost": requested_cost,
                    "remaining_mana": remaining,
                    "remaining_held_mana": remaining,
                    "sustain_source": "held_mana",
                    "sustain_ref": sustain_ref,
                },
            )

        if source == "attunement":
            if not FeatService.has_feat(character, "raw_channeling") and not FeatService.get_unlock(character, "cyclic_attunement_sustain"):
                return ActionResult.fail(
                    errors=["Raw Channeling is required to sustain cyclic spells from attunement."],
                    data={
                        "requested": cost,
                        "requested_base_cost": requested_cost,
                        "remaining_mana": ManaService._coerce_float(ManaService._get_attunement_state(character).get("current"), default=0.0),
                        "sustain_source": "attunement",
                        "sustain_ref": sustain_ref,
                        "reason": "raw_channeling_lost",
                    },
                )
            result = ManaService.consume_mana(character, cost)
            if not result.success:
                result.data.update(
                    {
                        "requested_base_cost": requested_cost,
                        "sustain_source": "attunement",
                        "sustain_ref": sustain_ref,
                        "reason": "insufficient_attunement",
                    }
                )
                return result
            result.data.update(
                {
                    "requested_base_cost": requested_cost,
                    "sustain_source": "attunement",
                    "sustain_ref": sustain_ref,
                }
            )
            return result

        if source == "cambrinth":
            return ActionResult.fail(
                errors=["Cambrinth sustain is not yet available. Use harnessed mana or Raw Channeling."],
                data={
                    "requested": cost,
                    "requested_base_cost": requested_cost,
                    "sustain_source": "cambrinth",
                    "sustain_ref": sustain_ref,
                    "reason": "cambrinth_subsystem_not_yet_implemented",
                },
            )

        return ActionResult.fail(
            errors=["Unknown cyclic sustain source."],
            data={
                "requested": cost,
                "requested_base_cost": requested_cost,
                "sustain_source": source,
                "sustain_ref": sustain_ref,
                "reason": "unknown_sustain_source",
            },
        )

    @staticmethod
    def consume_mana(character, amount):
        cost = max(0.0, ManaService._coerce_float(amount, default=0.0))
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        maximum = ManaService._coerce_float(attunement.get("max"), default=0.0)
        if current < cost:
            return ActionResult.fail(
                errors=["Not enough attunement."],
                data={"requested": cost, "remaining_mana": current, "attunement_max": maximum},
            )
        updated = ManaService._set_attunement_state(character, current - cost, maximum)
        return ActionResult.ok(
            data={
                "consumed": cost,
                "remaining_mana": ManaService._coerce_float(updated.get("current"), default=0.0),
                "attunement_max": ManaService._coerce_float(updated.get("max"), default=0.0),
            }
        )
        return None

    @staticmethod
    def prepare_spell(character, room, realm, mana_input, min_prep, max_prep, spell_id=None, min_prep_time=None, expiry_window=None):
        from engine.services.feat_service import FeatService

        result = ManaService.can_prepare_spell(
            character,
            room,
            realm,
            mana_input,
            min_prep,
            max_prep,
            spell_id=spell_id,
            min_prep_time=min_prep_time,
            expiry_window=expiry_window,
        )
        if not result.success:
            return result

        prep_cost = ManaService._coerce_int(result.data.get("prep_cost"), default=0)
        now = time.time()
        min_prep_time_value = max(0.0, ManaService._coerce_float(result.data.get("min_prep_time"), default=0.0))
        expiry_window_value = max(0.0, ManaService._coerce_float(result.data.get("expiry_window"), default=0.0))
        expiry_window_value += float(FeatService.get_modifier(character, "prepared_expiry_bonus_seconds") or 0.0)
        expiry_window_value = max(min_prep_time_value, expiry_window_value)
        ManaService.clear_prepared_mana(character)
        prepared = ManaService._set_prepared_mana_state(
            character,
            {
                "realm": str(result.data.get("realm", "") or ""),
                "spell_id": result.data.get("spell_id"),
                "mana_input": ManaService._coerce_int(result.data.get("mana_input"), default=0),
                "min_prep": ManaService._coerce_int(result.data.get("min_prep"), default=0),
                "max_prep": ManaService._coerce_int(result.data.get("max_prep"), default=0),
                "safe_mana": ManaService._coerce_int(result.data.get("mana_input"), default=0),
                "tier": 1,
                "prep_cost": prep_cost,
                "held_mana": ManaService._get_harnessed_mana_state(character),
                "prep_started_at": now,
                "min_prep_time": min_prep_time_value,
                "ready": min_prep_time_value <= 0.0,
                "expiry_at": (now + expiry_window_value) if expiry_window_value > 0.0 else None,
            },
        )
        if prepared is not None and not bool(prepared.get("ready", True)):
            ManaService.schedule_prepared_spell_transition(character, min_prep_time_value)
        if prepared is not None and expiry_window_value > 0.0:
            ManaService.schedule_prepared_spell_expiry(character, expiry_window_value)
        attunement = ManaService._get_attunement_state(character)
        return ActionResult.ok(
            data=dict(result.data) | {
                "attunement_current": ManaService._coerce_float(attunement.get("current"), default=0.0),
                "prepared_mana": dict(prepared or {}),
            }
        )

    @staticmethod
    def harness_mana(character, amount, attunement_skill, arcana_skill):
        from engine.services.feat_service import FeatService

        requested = max(0, ManaService._coerce_int(amount, default=0))
        efficiency = calculate_harness_efficiency(attunement_skill, arcana_skill)
        attunement_spent = calculate_harness_cost(requested, efficiency)
        attunement_spent = ManaService._apply_integer_multiplier(
            attunement_spent,
            FeatService.get_modifier(character, "harness_attunement_cost_multiplier"),
        )
        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        if current < float(attunement_spent):
            return ActionResult.fail(
                errors=["Not enough attunement to harness that much mana."],
                data={
                    "requested_harness": requested,
                    "harness_efficiency": efficiency,
                    "attunement_spent": attunement_spent,
                    "attunement_current": current,
                },
            )

        updated_attunement = ManaService.spend_attunement(character, attunement_spent)
        held_total = ManaService._set_harnessed_mana_state(character, ManaService._get_harnessed_mana_state(character) + requested)
        prepared = ManaService._get_prepared_mana_state(character)
        if prepared is not None:
            prepared["held_mana"] = held_total
            updated = ManaService._set_prepared_mana_state(character, prepared)
            sync_state = getattr(character, "_sync_prepared_spell_state_from_mana", None)
            if callable(sync_state):
                sync_state(updated)
        return ActionResult.ok(
            data={
                "realm": (prepared or {}).get("realm", ""),
                "requested_harness": requested,
                "harness_efficiency": efficiency,
                "attunement_spent": attunement_spent,
                "held_mana": held_total,
                "attunement_current": ManaService._coerce_float(updated_attunement.get("current"), default=0.0),
            }
        )

    @staticmethod
    def cast_spell(character, realm, primary_magic_skill, profession_cast_modifier=1.0, additional_mana=None):
        return ManaService._cast_spell(
            character,
            realm,
            primary_magic_skill,
            profession_cast_modifier=profession_cast_modifier,
            clear_prepared=True,
            additional_mana=additional_mana,
        )

    @staticmethod
    def _cast_spell(character, realm, primary_magic_skill, profession_cast_modifier=1.0, clear_prepared=True, additional_mana=None):
        from engine.services.feat_service import FeatService

        prepared = ManaService._get_prepared_mana_state(character)
        normalized_realm = str(realm or "").strip().lower()
        if prepared is None:
            return ActionResult.fail(errors=["No spell is currently prepared."], data={"realm": normalized_realm})
        if normalized_realm and normalized_realm != prepared["realm"]:
            return ActionResult.fail(errors=["Prepared spell realm does not match cast realm."], data={"realm": normalized_realm, "prepared_realm": prepared["realm"]})

        attunement = ManaService._get_attunement_state(character)
        current = ManaService._coerce_float(attunement.get("current"), default=0.0)
        maximum = ManaService._coerce_float(attunement.get("max"), default=0.0)
        intended_mana = max(0, ManaService._coerce_int(prepared.get("intended_mana", prepared.get("mana_input")), default=0))
        attunement_spent = ManaService._apply_integer_multiplier(
            intended_mana,
            FeatService.get_modifier(character, "spell_attunement_cost_multiplier"),
        )
        if current < float(attunement_spent):
            return ActionResult.fail(
                errors=["Not enough attunement."],
                data={
                    "realm": normalized_realm,
                    "required_attunement": attunement_spent,
                    "attunement_current": current,
                },
            )
        held_pool = ManaService._get_harnessed_mana_state(character)
        held_to_use = held_pool if additional_mana is None else max(0, ManaService._coerce_int(additional_mana, default=0))
        if held_to_use > held_pool:
            return ActionResult.fail(
                errors=["You are not holding that much mana."],
                data={"requested_additional_mana": held_to_use, "held_mana": held_pool},
            )
        updated_attunement = ManaService.spend_attunement(character, attunement_spent)
        remaining_held = ManaService._set_harnessed_mana_state(character, held_pool - held_to_use)
        effective_env_mana = 1.0
        room = getattr(character, "location", None)
        if room is not None:
            effective_env_mana = ManaService._get_effective_env_mana(character, room, prepared["realm"])
        environmental_modifier = ManaService.get_environmental_modifier(room, prepared["realm"])
        cast_modifier = ManaService._coerce_float(profession_cast_modifier, default=1.0) * ManaService._get_profession_cast_modifier(character, prepared["realm"])
        cast_mana = intended_mana + held_to_use
        spell_profile = ManaService._get_spell_profile(character, prepared, primary_magic_skill, effective_env_mana)
        control_context = ManaService._build_control_context(character, primary_magic_skill, attunement)
        control_context["fully_prepped"] = bool(prepared.get("ready", True))
        control_context["prep_seconds_waited"] = ManaService._coerce_float(prepared.get("min_prep_time"), default=0.0)
        control_context["current_concentration"] = 100.0
        control_context["max_concentration"] = 100.0
        control_context["current_fatigue"] = 100.0
        control_context["max_fatigue"] = 100.0
        control_context["current_body_hp"] = 100.0
        control_context["max_body_hp"] = 100.0
        control_context["nervous_injury"] = 0.0
        random_roll = 0.0
        spell_difficulty = calculate_spell_difficulty(spell_profile, cast_mana, effective_env_mana)
        control_score = calculate_control_score(control_context, spell_profile)
        strain_penalty = calculate_strain_penalty(current, maximum)
        cast_margin = calculate_cast_margin(control_score, spell_difficulty, strain_penalty, random_roll)
        success_band = resolve_success_band(
            cast_margin,
            control_score=control_score,
            difficulty=spell_difficulty,
            base_difficulty=ManaService._coerce_float(spell_profile.get("base_difficulty"), default=0.0) * 100.0,
        )
        final_power = calculate_final_spell_power(
            cast_mana,
            primary_magic_skill,
            effective_env_mana,
            current,
            maximum,
            profession_cast_modifier=cast_modifier,
        )
        final_power *= ManaService.BAND_MULTIPLIERS.get(success_band, 1.0)
        if ManaService._get_profession_name(character) == "cleric" and prepared["realm"] == "holy":
            final_power *= 1.0 + (ManaService._get_devotion_percent(character) * 0.25)
        backlash = calculate_margin_backlash_chance(
            spell_profile,
            cast_mana,
            cast_margin,
            effective_env_mana,
            control_score=control_score,
            difficulty=spell_difficulty,
            base_difficulty=ManaService._coerce_float(spell_profile.get("base_difficulty"), default=0.0) * 100.0,
        )
        backlash_severity = calculate_backlash_severity(
            spell_profile,
            cast_mana,
            cast_margin,
            control_score=control_score,
            difficulty=spell_difficulty,
            base_difficulty=ManaService._coerce_float(spell_profile.get("base_difficulty"), default=0.0) * 100.0,
        )
        payload = {
            "realm": prepared["realm"],
            "mana_input": intended_mana,
            "cast_mana": cast_mana,
            "prep_cost": prepared["prep_cost"],
            "held_mana": held_to_use,
            "harnessed_mana_remaining": remaining_held,
            "attunement_spent": attunement_spent,
            "attunement_current": ManaService._coerce_float(updated_attunement.get("current"), default=0.0),
            "effective_env_mana": effective_env_mana,
            "environmental_mana_modifier": environmental_modifier,
            "spell_difficulty_modifier": int(spell_profile.get("spell_difficulty_modifier", 0) or 0),
            "base_difficulty_unmodified": ManaService._coerce_float(spell_profile.get("base_difficulty_unmodified"), default=0.0),
            "base_difficulty_modified": ManaService._coerce_float(spell_profile.get("base_difficulty"), default=0.0),
            "spell_difficulty": spell_difficulty,
            "control_score": control_score,
            "strain_penalty": strain_penalty,
            "cast_margin": cast_margin,
            "success_band": success_band,
            "final_spell_power": final_power,
            "backlash_chance": backlash,
            "backlash_severity": backlash_severity,
            "prepared_mana": dict(prepared),
        }

        should_apply_backlash = success_band == "backlash"

        if should_apply_backlash:
            backlash_payload = resolve_backlash_payload(control_context, backlash_severity, dict(spell_profile) | {"mana_input": cast_mana})
            applied = ManaService._apply_backlash_payload(character, backlash_payload)
            payload["backlash_payload"] = dict(backlash_payload) | dict(applied)
            payload["empath_shock_gain"] = int(applied.get("shock_gain", 0) or 0)
            payload["cleric_devotion_loss"] = int(applied.get("devotion_loss", 0) or 0)
            payload["warrior_mage_self_hit"] = int(applied.get("vitality_loss", 0) or 0)
            payload["moon_mage_focus_penalty"] = int(applied.get("focus_penalty_duration", 0) or 0)

        if clear_prepared or success_band in {"failure", "backlash"}:
            ManaService.clear_prepared_mana(character)
        return ActionResult.ok(data=payload)

    @staticmethod
    def regenerate_attunement(character, attunement_skill=None, wisdom=None, regen_modifiers=1.0):
        from engine.services.feat_service import FeatService

        if attunement_skill is None and character is not None and hasattr(character, "get_skill"):
            attunement_skill = character.get_skill("attunement")
        if wisdom is None and character is not None and hasattr(character, "get_stat"):
            wisdom = character.get_stat("wisdom")
        attunement = ManaService._get_attunement_state(character)
        regen = calculate_attunement_regen(
            attunement.get("current"),
            attunement.get("max"),
            ManaService._coerce_float(attunement_skill, default=0.0),
            ManaService._coerce_float(wisdom, default=0.0),
            regen_modifiers=float(regen_modifiers or 1.0) * FeatService.get_modifier(character, "attunement_regen_multiplier"),
        )
        updated = ManaService.restore_attunement(character, regen)
        return ActionResult.ok(data={"regen": regen, "attunement_current": updated["current"], "attunement_max": updated["max"]})

    @staticmethod
    @staticmethod
    def apply_devotion_pulse(character):
        if character is None or not hasattr(character, "get_devotion") or not hasattr(character, "get_devotion_max"):
            return ActionResult.ok(data={"applied": False, "amount": 0})
        maximum = ManaService._coerce_int(character.get_devotion_max(), default=0)
        current = ManaService._coerce_int(character.get_devotion(), default=0)
        if maximum <= 0 or current >= maximum:
            return ActionResult.ok(data={"applied": False, "amount": 0, "devotion": current, "max_devotion": maximum})
        amount = max(1, int(round(maximum * 0.01)))
        updated = character.adjust_devotion(amount, sync=False) if hasattr(character, "adjust_devotion") else current
        return ActionResult.ok(data={"applied": True, "amount": amount, "devotion": ManaService._coerce_int(updated, default=current), "max_devotion": maximum})

    @staticmethod
    def handle_mana_regen(character, payload=None):
        _payload = dict(payload or {})
        result = ManaService.regenerate_attunement(character)
        if character is not None and getattr(character, "pk", None):
            ManaService.schedule_mana_regen(character)
        return result

    @staticmethod
    def handle_devotion_pulse(character, payload=None):
        result = ManaService.apply_devotion_pulse(character)
        if character is not None and getattr(character, "pk", None) and ManaService._is_profession(character, "cleric"):
            ManaService.schedule_devotion_pulse(character)
        return result

    @staticmethod
    def schedule_mana_regen(character, delay=MANA_PULSE_INTERVAL):
        if character is None or not getattr(character, "pk", None):
            return None
        if not _ensure_scheduler_callbacks_registered():
            return None
        _, _, schedule_event = _get_scheduler_api()
        return schedule_event(
            MANA_REGEN_EVENT,
            character,
            delay,
            "mana:process_regen",
            metadata={"system": "mana", "type": "regen", "timing_mode": "scheduled-expiry"},
        )

    @staticmethod
    def cancel_mana_regen(character):
        if character is None:
            return None
        try:
            cancel_event, _, _ = _get_scheduler_api()
        except Exception:
            return None
        return cancel_event(MANA_REGEN_EVENT, character)

    @staticmethod
    def schedule_devotion_pulse(character, delay=DEVOTION_PULSE_INTERVAL):
        if character is None or not getattr(character, "pk", None):
            return None
        if not ManaService._is_profession(character, "cleric"):
            return None
        if not _ensure_scheduler_callbacks_registered():
            return None
        _, _, schedule_event = _get_scheduler_api()
        return schedule_event(
            MANA_DEVOTION_EVENT,
            character,
            delay,
            "mana:process_devotion",
            metadata={"system": "mana", "type": "devotion", "timing_mode": "scheduled-expiry"},
        )

    @staticmethod
    def cancel_devotion_pulse(character):
        if character is None:
            return None
        try:
            cancel_event, _, _ = _get_scheduler_api()
        except Exception:
            return None
        return cancel_event(MANA_DEVOTION_EVENT, character)

    @staticmethod
    def sync_scheduled_effects(character):
        if character is None or not getattr(character, "pk", None):
            return None
        if ManaService._is_profession(character, "cleric"):
            ManaService.schedule_devotion_pulse(character)
        else:
            ManaService.cancel_devotion_pulse(character)
        return True

    @staticmethod
    def bootstrap_scheduled_effects(character):
        if character is None or not getattr(character, "pk", None):
            return None
        return ManaService.sync_scheduled_effects(character)

    @staticmethod
    def schedule_prepared_spell_transition(character, delay):
        if character is None or not getattr(character, "pk", None):
            return None
        if not _ensure_scheduler_callbacks_registered():
            return None
        _, _, schedule_event = _get_scheduler_api()
        return schedule_event(
            MANA_PREPARED_READY_EVENT,
            character,
            delay,
            "mana:prepared_ready",
            metadata={"system": "mana", "type": "prepared-ready", "timing_mode": "scheduled-expiry"},
        )

    @staticmethod
    def cancel_prepared_spell_transition(character):
        if character is None:
            return None
        try:
            cancel_event, _, _ = _get_scheduler_api()
        except Exception:
            return None
        return cancel_event(MANA_PREPARED_READY_EVENT, character)

    @staticmethod
    def schedule_prepared_spell_expiry(character, delay):
        if character is None or not getattr(character, "pk", None):
            return None
        if not _ensure_scheduler_callbacks_registered():
            return None
        _, _, schedule_event = _get_scheduler_api()
        return schedule_event(
            MANA_PREPARED_EXPIRE_EVENT,
            character,
            delay,
            "mana:prepared_expire",
            metadata={"system": "mana", "type": "prepared-expire", "timing_mode": "scheduled-expiry"},
        )

    @staticmethod
    def cancel_prepared_spell_expiry(character):
        if character is None:
            return None
        try:
            cancel_event, _, _ = _get_scheduler_api()
        except Exception:
            return None
        return cancel_event(MANA_PREPARED_EXPIRE_EVENT, character)

    @staticmethod
    def cancel_prepared_spell_timers(character):
        ManaService.cancel_prepared_spell_transition(character)
        ManaService.cancel_prepared_spell_expiry(character)
        return True

    @staticmethod
    def cancel_scheduled_effects(character):
        ManaService.cancel_mana_regen(character)
        ManaService.cancel_devotion_pulse(character)
        ManaService.cancel_prepared_spell_timers(character)
        return True


def _callback_process_mana_regen(owner, payload=None):
    return ManaService.handle_mana_regen(owner, payload)


def _callback_process_devotion(owner, payload=None):
    return ManaService.handle_devotion_pulse(owner, payload)


def _callback_transition_prepared_spell(owner, payload=None):
    return ManaService.transition_to_full_prep(owner, payload)


def _callback_expire_prepared_spell(owner, payload=None):
    return ManaService.expire_prepared_spell(owner, payload)