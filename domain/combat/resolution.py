from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import random

from domain.combat.armor import ArmorReduction, apply_armor_reduction
from domain.combat.cleanup import apply_cleanup
from domain.combat.damage import RawDamage, compute_damage
from domain.combat.hit_area import BodyPart, body_part_to_key, determine_hit_area
from domain.combat.maneuvers import get_defense_scaling
from domain.combat.rng import CombatRng
from domain.combat.wounds import apply_wounds
from engine.services.ranger_saf_service import RangerSafService


EARLY_GAME_DAMAGE_CLAMP_RATIO = 0.15
EARLY_GAME_DAMAGE_CLAMP_RANK = 20

NO_PARRY_THRESHOLD = 50
FULL_PARRY_THRESHOLD = 150

SHIELD_MIN_DEF = 10
SHIELD_MAX_DEF = 60


class CombatOutcome(Enum):
    EVADED = "evaded"
    FULLY_PARRIED = "parried_full"
    PARTIALLY_PARRIED = "parried_partial"
    FULLY_SHIELDED = "shielded_full"
    PARTIALLY_SHIELDED = "shielded_partial"
    HIT = "hit"


@dataclass(frozen=True)
class OffensiveFactor:
    """Offensive factor composition.

    Canon provenance: GSL S00041 and S00091 apply combat RNG inside OF,
    then subtract EDF in S00091/S00092.
    """

    base: int
    offensive_mod_pct: int
    fatigue_pct: int
    rng_pct: int
    stance_pct: int
    position_pct: int = 100
    intoxication_pct: int = 100
    total: int = field(init=False)

    def __post_init__(self):
        total = max(1, int(self.base or 1))
        for pct in (
            self.offensive_mod_pct,
            self.fatigue_pct,
            self.rng_pct,
            self.stance_pct,
            self.position_pct,
            self.intoxication_pct,
        ):
            total = max(0, total * max(0, int(pct or 0)) // 100)
        object.__setattr__(self, "total", total)


@dataclass(frozen=True)
class EvasionDefenseFactor:
    """Deterministic evasion defense factor from GSL S00042."""

    reflex: int
    evasion_skill: int
    usable_evasion_pct: int
    maneuver_scale_pct: int
    maneuver_mod_pct: int
    total: int = field(init=False)

    def __post_init__(self):
        total = max(0, int(self.reflex or 0) + int(self.evasion_skill or 0))
        total = total * max(0, int(self.usable_evasion_pct or 0)) // 100
        total = total * max(0, int(self.maneuver_scale_pct or 0)) // 100
        total = total * max(0, int(self.maneuver_mod_pct or 0)) // 100
        object.__setattr__(self, "total", total)


@dataclass(frozen=True)
class ForceOfImpact:
    """Post-evasion force of impact bridge from S00092."""

    base_roll: int
    strength_bonus: int
    after_mods: int
    total: int = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "total", max(0, int(self.after_mods or 0)))


@dataclass(frozen=True)
class ParrySubcontest:
    """Parry block magnitude from GSL S00043."""

    parry_score: int
    leftover_of: int
    parry_percent: int
    block_pct: int
    maneuver_scale_pct: int = 100


@dataclass(frozen=True)
class ShieldSubcontest:
    """Shield block magnitude bridge from GSL S00046."""

    shield_score: int
    block_pct: int
    maneuver_scale_pct: int = 100


class AttackResolution:
    def __init__(self, hit=False, damage=0, roundtime=0, details=None):
        self.hit = hit
        self.damage = damage
        self.roundtime = roundtime
        self.details = details or {}


def _coerce_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _coerce_float(value, default=0.0):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return default


def _get_position_pct(actor, key):
    if not hasattr(actor, "get_position_modifiers"):
        return 100
    modifiers = actor.get_position_modifiers() or {}
    return max(25, 100 + _coerce_int(modifiers.get(key, 0)))


def _get_stance_pct(actor, key):
    stance = getattr(getattr(actor, "db", None), "stance", None) or {"offense": 50, "defense": 50}
    return max(25, 50 + _coerce_int(stance.get(key, 50)))


def _get_intoxication_pct(actor):
    if bool(getattr(getattr(actor, "db", None), "intoxicated", False)):
        return 80
    return 100


def _get_last_maneuver_id(actor):
    getter = getattr(actor, "get_last_maneuver", None)
    if callable(getter):
        return _coerce_int(getter())
    return _coerce_int(getattr(getattr(actor, "db", None), "last_maneuver", 0))


def _get_fatigue_pct(actor):
    fatigue = _coerce_int(getattr(getattr(actor, "db", None), "fatigue", 0))
    if fatigue <= 0:
        return 100
    return max(40, 100 - min(60, fatigue))


def _get_weapon_profile(attacker, context):
    profile = dict(context.get("profile") or {})
    if profile:
        return profile
    if hasattr(attacker, "get_weapon_profile"):
        return dict(attacker.get_weapon_profile() or {})
    return {}


def _get_weapon_force(profile, weapon):
    if weapon is not None:
        value = getattr(getattr(weapon, "db", None), "force", None)
        if value is not None:
            return max(1, _coerce_int(value, 1))
    damage_max = _coerce_int(profile.get("damage_max", profile.get("damage", 1)), 1)
    damage_min = _coerce_int(profile.get("damage_min", damage_max), damage_max)
    balance = _coerce_int(profile.get("balance", 50), 50)
    return max(5, damage_min + damage_max + max(0, (balance - 35) // 3))


def _get_weapon_power(profile, weapon):
    if weapon is not None:
        value = getattr(getattr(weapon, "db", None), "power", None)
        if value is not None:
            return max(1, _coerce_int(value, 1))
    damage = _coerce_int(profile.get("damage", profile.get("damage_max", 1)), 1)
    balance = _coerce_int(profile.get("balance", 50), 50)
    return max(10, damage * 12 + max(0, balance - 30))


def _get_active_effect(actor, category, effect_name):
    getter = getattr(actor, "get_state", None)
    if not callable(getter):
        return {}
    active_effects = getter("active_effects") or {}
    if not isinstance(active_effects, Mapping):
        return {}
    effect_map = active_effects.get(str(category or "").strip().lower(), {}) or {}
    if not isinstance(effect_map, Mapping):
        return {}
    payload = effect_map.get(str(effect_name or "").strip().lower().replace(" ", "_"), {}) or {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _get_augmentation_modifier(actor, modifier_key):
    getter = getattr(actor, "get_state", None)
    if not callable(getter):
        return 0
    buff = getter("augmentation_buff") or {}
    if not isinstance(buff, Mapping):
        return 0
    modifiers = dict(buff.get("modifiers") or {})
    scale = _coerce_float(modifiers.get(str(modifier_key or "").strip().lower().replace(" ", "_"), 0.0))
    if scale <= 0.0:
        return 0
    return max(0, int(round(_coerce_float(buff.get("strength", 0)) * scale)))


def _is_undead_target(target):
    trait_values = [
        str(getattr(getattr(target, "db", None), key, "") or "").strip().lower()
        for key in ("creature_type", "npc_type", "species", "race")
    ]
    searchable = " ".join([
        str(getattr(target, "key", "") or "").lower(),
        str(getattr(getattr(target, "db", None), "desc", "") or "").lower(),
        *trait_values,
    ])
    return any(keyword in searchable for keyword in ("undead", "zombie", "skeleton", "ghost", "wraith"))


def _get_bless_accuracy_bonus(actor, target):
    if not _is_undead_target(target):
        return 0
    bless = _get_active_effect(actor, "utility", "bless")
    return max(0, _coerce_int(bless.get("undead_accuracy_bonus", 0)))


def _get_bless_damage_bonus(actor, target):
    if not _is_undead_target(target):
        return 0
    bless = _get_active_effect(actor, "utility", "bless")
    return max(0, _coerce_int(bless.get("undead_damage_bonus", 0)))


def _get_protection_from_evil_bonus(defender, attacker):
    if not _is_undead_target(attacker):
        return 0
    getter = getattr(defender, "get_state", None)
    if not callable(getter):
        return 0
    active_effects = getter("active_effects") or {}
    if not isinstance(active_effects, Mapping):
        return 0
    warding_effects = active_effects.get("warding", {}) or {}
    if not isinstance(warding_effects, Mapping):
        return 0
    best_bonus = 0
    for payload in warding_effects.values():
        if not isinstance(payload, Mapping):
            continue
        best_bonus = max(best_bonus, max(0, _coerce_int(payload.get("undead_evasion_bonus", 0))))
    return best_bonus


def compute_offensive_factor(attacker, target, context=None, *, combat_rng=None):
    context = context or {}
    combat_rng = combat_rng or CombatRng()
    profile = _get_weapon_profile(attacker, context)
    weapon_effects = dict(context.get("weapon_effects") or {})
    skill_name = str(context.get("skill_name") or profile.get("skill") or "brawling")
    skill_rank = _coerce_int(attacker.get_skill(skill_name) if hasattr(attacker, "get_skill") else 0)
    tactics = _coerce_int(attacker.get_skill("tactics") if hasattr(attacker, "get_skill") else 0)
    agility = _coerce_int(attacker.get_stat("agility") if hasattr(attacker, "get_stat") else 0)
    reflex = _coerce_int(attacker.get_stat("reflex") if hasattr(attacker, "get_stat") else 0)
    balance = max(2, _coerce_int(profile.get("balance", 50)) + _coerce_int(weapon_effects.get("balance", 0)))
    stat_term = max(2.0, (agility + reflex + 1) * max(1.0, math.log(balance)))
    base = skill_rank + int(math.log(stat_term) * 25)
    base += 10 + (tactics // 10)
    base += _coerce_int(context.get("suitability", 0))
    base += _coerce_int(weapon_effects.get("accuracy", 0))
    base += _get_augmentation_modifier(attacker, "accuracy")
    base += _get_bless_accuracy_bonus(attacker, target)

    if hasattr(attacker, "is_staggered") and attacker.is_staggered():
        base -= 10
    if hasattr(attacker, "get_pressure_accuracy_penalty"):
        base -= _coerce_int(attacker.get_pressure_accuracy_penalty())
    if hasattr(attacker, "get_exhaustion_accuracy_penalty"):
        base -= _coerce_int(attacker.get_exhaustion_accuracy_penalty())
    structured_accuracy_penalty = attacker.get_effect_modifier("accuracy") if hasattr(attacker, "get_effect_modifier") else 0
    if structured_accuracy_penalty:
        base -= _coerce_int(structured_accuracy_penalty)
    else:
        debilitation = attacker.get_state("debilitated") if hasattr(attacker, "get_state") else None
        if debilitation:
            base -= _coerce_int(debilitation.get("penalty", 0))
    att_awareness = attacker.get_awareness() if hasattr(attacker, "get_awareness") else "normal"
    if att_awareness == "alert":
        base += 5
    elif att_awareness == "unaware":
        base -= 10

    is_ranged_weapon = bool(context.get("is_ranged_weapon", False))
    ranger_aim_stacks = _coerce_int(context.get("ranger_aim_stacks", 0))
    current_range = str(context.get("current_range", "melee") or "melee")
    if hasattr(attacker, "get_barbarian_roar_offense_penalty"):
        penalty_key = "missile_accuracy" if is_ranged_weapon else "melee_accuracy"
        base -= _coerce_int(attacker.get_barbarian_roar_offense_penalty(penalty_key))
    if hasattr(attacker, "get_barbarian_dance_offense_bonus"):
        bonus_key = "missile_accuracy" if is_ranged_weapon else "melee_accuracy"
        base += _coerce_int(attacker.get_barbarian_dance_offense_bonus(bonus_key))
    if getattr(getattr(attacker, "db", None), "aiming", None) == getattr(target, "id", None):
        base += 15 if not is_ranged_weapon else 10 + (ranger_aim_stacks * 5)
    if is_ranged_weapon:
        if current_range == "melee":
            base -= 35
        elif current_range == "near":
            base += 5
        elif current_range == "far":
            base += 10

    if bool(context.get("ambush")):
        base += _coerce_int(context.get("ambush_accuracy_bonus", 0))

    attacker_tempo_state = context.get("attacker_tempo_state")
    if attacker_tempo_state == "surging":
        base += 3
    elif attacker_tempo_state == "frenzied":
        base += 5

    if hasattr(attacker, "get_rhythm_accuracy_bonus"):
        base += _coerce_int(attacker.get_rhythm_accuracy_bonus())

    for key in ("surge_state", "press_state", "frenzy_state"):
        state = context.get(key)
        if isinstance(state, dict):
            base += _coerce_int(state.get("bonus", state.get("accuracy", 0)))

    attacker_berserk = context.get("attacker_berserk")
    if attacker_berserk:
        base += _coerce_int(attacker_berserk.get("accuracy_bonus", 0))

    for effect_key in ("attacker_disrupt", "attacker_unnerving", "attacker_intimidate"):
        effect = context.get(effect_key)
        if isinstance(effect, dict):
            base -= _coerce_int(effect.get("accuracy_penalty", 0))

    tactics_prep = attacker.get_state("tactics_prep") if hasattr(attacker, "get_state") else None
    ranger_pounce = attacker.get_state("ranger_pounce") if hasattr(attacker, "get_state") else None
    if tactics_prep and tactics_prep.get("target") == getattr(target, "id", None):
        base += _coerce_int(tactics_prep.get("bonus", 0))
        if hasattr(attacker, "clear_state"):
            attacker.clear_state("tactics_prep")
    if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == getattr(target, "id", None):
        base += _coerce_int(ranger_pounce.get("accuracy_bonus", 0))
    if bool(context.get("snipe_active")):
        prepared_snipe = dict(context.get("prepared_snipe") or context.get("ranger_snipe") or {})
        base += _coerce_int(prepared_snipe.get("accuracy_bonus", 0))
    ranger_mark = context.get("ranger_mark")
    if isinstance(ranger_mark, Mapping):
        base += _coerce_int(ranger_mark.get("accuracy_bonus", 0))

    if bool(getattr(getattr(attacker, "db", None), "is_npc", False)):
        npc_max_hp = _coerce_int(getattr(getattr(attacker, "db", None), "max_hp", 0))
        npc_hp = _coerce_int(getattr(getattr(attacker, "db", None), "hp", 0))
        npc_hp_ratio = (npc_hp / npc_max_hp) if npc_max_hp else 1.0
        if npc_hp_ratio > 0.7:
            base += 5

    nearby_engaged = 0
    if getattr(attacker, "location", None):
        for obj in attacker.location.contents:
            if obj in {attacker, target} or not hasattr(obj, "get_target"):
                continue
            if obj.get_target() == attacker:
                nearby_engaged += 1
    if nearby_engaged > 0:
        base += int(tactics / 5)

    if skill_rank < 10:
        base -= 10

    aimed_part = context.get("aimed_part")
    if aimed_part == "head":
        base -= 20
    elif aimed_part in {"arm", "leg"}:
        base -= 10

    if hasattr(attacker, "apply_death_sting_to_contest_value"):
        base = attacker.apply_death_sting_to_contest_value(base)

    maneuver_hindrance, _ = attacker.get_total_hindrance() if hasattr(attacker, "get_total_hindrance") else (0, 0)
    offensive_mod_pct = max(25, 100 - min(60, int(round(_coerce_float(maneuver_hindrance) * 4)) + _coerce_int(attacker.get_arm_penalty() if hasattr(attacker, "get_arm_penalty") else 0)))
    return OffensiveFactor(
        base=max(1, base),
        offensive_mod_pct=offensive_mod_pct,
        fatigue_pct=_get_fatigue_pct(attacker),
        rng_pct=combat_rng.roll(),
        stance_pct=_get_stance_pct(attacker, "offense"),
        position_pct=_get_position_pct(attacker, "offense"),
        intoxication_pct=_get_intoxication_pct(attacker),
    )


def compute_edf(defender, attacker=None, context=None):
    context = context or {}
    defense_scaling = get_defense_scaling(_get_last_maneuver_id(defender))
    reflex = _coerce_int(defender.get_stat("reflex") if hasattr(defender, "get_stat") else 0)
    agility = _coerce_int(defender.get_stat("agility") if hasattr(defender, "get_stat") else 0)
    evasion_skill = _coerce_int(defender.get_skill("evasion") if hasattr(defender, "get_skill") else 0) + agility
    usable_evasion_pct = _get_stance_pct(defender, "defense")
    target_awareness = defender.get_awareness() if hasattr(defender, "get_awareness") else "normal"
    if target_awareness == "alert":
        usable_evasion_pct += 10
    elif target_awareness == "unaware":
        usable_evasion_pct -= 10
    if hasattr(defender, "is_surprised") and defender.is_surprised():
        usable_evasion_pct -= 20
    if isinstance(context.get("hold_state"), dict):
        usable_evasion_pct += _coerce_int(context["hold_state"].get("defense", 0))
    if hasattr(defender, "has_warrior_passive") and defender.has_warrior_passive("multitarget_defense_1") and getattr(defender, "incoming_attackers", 0) > 1:
        usable_evasion_pct += 3
    if context.get("defender_tempo_state") == "frenzied":
        usable_evasion_pct -= 8
    if hasattr(defender, "get_exhaustion_defense_penalty"):
        usable_evasion_pct -= _coerce_int(defender.get_exhaustion_defense_penalty())
    defender_berserk = context.get("defender_berserk")
    if defender_berserk:
        usable_evasion_pct += _coerce_int(defender_berserk.get("defense_bonus", 0))
    defensive_roar = context.get("defender_roars", {}).get("defensive") if isinstance(context.get("defender_roars"), dict) else None
    if isinstance(defensive_roar, dict):
        usable_evasion_pct += _coerce_int(defensive_roar.get("defense_bonus", 0))

    structured_evasion_penalty = defender.get_effect_modifier("evasion") if hasattr(defender, "get_effect_modifier") else 0
    if structured_evasion_penalty:
        usable_evasion_pct -= _coerce_int(structured_evasion_penalty)
    else:
        target_debilitation = defender.get_state("debilitated") if hasattr(defender, "get_state") else None
        if target_debilitation and target_debilitation.get("type") == "evasion":
            usable_evasion_pct -= _coerce_int(target_debilitation.get("penalty", 0))
    if hasattr(defender, "get_barbarian_roar_defense_penalty"):
        usable_evasion_pct -= _coerce_int(defender.get_barbarian_roar_defense_penalty("evasion"))
    if hasattr(defender, "get_barbarian_dance_defense_bonus"):
        bonus_key = "missile" if bool(context.get("is_ranged_weapon")) else "melee"
        usable_evasion_pct += _coerce_int(defender.get_barbarian_dance_defense_bonus(bonus_key))
    usable_evasion_pct += _get_augmentation_modifier(defender, "evasion")
    usable_evasion_pct += _get_protection_from_evil_bonus(defender, attacker)

    if hasattr(defender, "apply_death_sting_to_contest_value"):
        evasion_skill = defender.apply_death_sting_to_contest_value(evasion_skill)

    target_maneuver_hindrance, _ = defender.get_total_hindrance() if hasattr(defender, "get_total_hindrance") else (0, 0)
    maneuver_mod_pct = max(10, 100 - min(75, int(round(_coerce_float(target_maneuver_hindrance) * 6))))
    maneuver_mod_pct += _coerce_int((defender.get_position_modifiers() or {}).get("defense", 0)) if hasattr(defender, "get_position_modifiers") else 0

    total = EvasionDefenseFactor(
        reflex=max(0, reflex),
        evasion_skill=max(0, evasion_skill),
        usable_evasion_pct=max(0, usable_evasion_pct),
        maneuver_scale_pct=max(0, defense_scaling.evasion_pct),
        maneuver_mod_pct=max(0, maneuver_mod_pct),
    )
    if context.get("strong_ambush"):
        return EvasionDefenseFactor(reflex=0, evasion_skill=0, usable_evasion_pct=0, maneuver_scale_pct=0, maneuver_mod_pct=0)
    return total


def compute_foi(attacker, context=None, *, rng=None):
    context = context or {}
    rng = rng or random
    profile = dict(context.get("profile") or {})
    weapon = context.get("weapon")
    force_cap = _get_weapon_force(profile, weapon)
    power_rating = _get_weapon_power(profile, weapon)
    strength = _coerce_int(attacker.get_stat("strength") if hasattr(attacker, "get_stat") else 0)
    base_roll = rng.randint(1, force_cap)
    strength_bonus = min(force_cap, ((power_rating * strength) // 100) // 2)
    after_mods = base_roll + strength_bonus
    return ForceOfImpact(base_roll=base_roll, strength_bonus=strength_bonus, after_mods=after_mods)


def compute_parry(defender, leftover_of, context=None):
    context = context or {}
    defense_scaling = get_defense_scaling(_get_last_maneuver_id(defender))
    if leftover_of <= 0:
        return ParrySubcontest(parry_score=0, leftover_of=leftover_of, parry_percent=0, block_pct=0, maneuver_scale_pct=defense_scaling.parry_pct)
    defender_weapon_profile = defender.get_weapon_profile() if hasattr(defender, "get_weapon_profile") else {}
    parry_skill_name = "parry_ability"
    parry_skill = _coerce_int(defender.get_skill(parry_skill_name) if hasattr(defender, "get_skill") else 0)
    agility = _coerce_int(defender.get_stat("agility") if hasattr(defender, "get_stat") else 0)
    reflex = _coerce_int(defender.get_stat("reflex") if hasattr(defender, "get_stat") else 0)
    balance = _coerce_int(defender_weapon_profile.get("balance", 50), 50)
    parry_score = max(0, parry_skill + reflex + agility + (balance // 5))
    if hasattr(defender, "get_barbarian_roar_defense_penalty"):
        parry_score = max(0, parry_score - _coerce_int(defender.get_barbarian_roar_defense_penalty("parry")))
    if hasattr(defender, "get_barbarian_dance_defense_bonus"):
        parry_score += _coerce_int(defender.get_barbarian_dance_defense_bonus("parry"))
    parry_score = max(0, parry_score * max(0, defense_scaling.parry_pct) // 100)
    parry_percent = (parry_score * 100) // max(1, leftover_of)
    if parry_percent < NO_PARRY_THRESHOLD:
        block_pct = 0
    elif parry_percent > FULL_PARRY_THRESHOLD:
        block_pct = 100
    else:
        block_pct = parry_percent - NO_PARRY_THRESHOLD
    return ParrySubcontest(
        parry_score=parry_score,
        leftover_of=leftover_of,
        parry_percent=parry_percent,
        block_pct=max(0, min(100, block_pct)),
        maneuver_scale_pct=defense_scaling.parry_pct,
    )


def compute_shield(defender, leftover_of, context=None):
    context = context or {}
    defense_scaling = get_defense_scaling(_get_last_maneuver_id(defender))
    equipment = {}
    if hasattr(defender, "get_equipment"):
        equipment = dict(defender.get_equipment() or {})
    else:
        equipment = dict(getattr(getattr(defender, "db", None), "equipment", {}) or {})
    shield_items = list(equipment.get("shield", []) or [])
    if leftover_of <= 0 or not shield_items:
        return ShieldSubcontest(shield_score=0, block_pct=0, maneuver_scale_pct=defense_scaling.shield_pct)
    shield_item = shield_items[0]
    shield_skill = _coerce_int(defender.get_skill("shield_usage") if hasattr(defender, "get_skill") else 0)
    min_def = _coerce_int(getattr(getattr(shield_item, "db", None), "mindef", SHIELD_MIN_DEF), SHIELD_MIN_DEF)
    max_def = _coerce_int(getattr(getattr(shield_item, "db", None), "maxdef", SHIELD_MAX_DEF), SHIELD_MAX_DEF)
    shield_score = min(max_def, min_def + shield_skill)
    if hasattr(defender, "get_barbarian_roar_defense_penalty"):
        shield_score = max(0, shield_score - _coerce_int(defender.get_barbarian_roar_defense_penalty("shield")))
    if hasattr(defender, "get_barbarian_dance_defense_bonus"):
        shield_score += _coerce_int(defender.get_barbarian_dance_defense_bonus("shield"))
    shield_score = max(0, shield_score * max(0, defense_scaling.shield_pct) // 100)
    return ShieldSubcontest(shield_score=shield_score, block_pct=max(0, min(100, shield_score)), maneuver_scale_pct=defense_scaling.shield_pct)


def _get_hit_location_options(target):
    db = getattr(target, "db", None)
    injuries = getattr(db, "injuries", None)
    if isinstance(injuries, Mapping) and injuries:
        return list(injuries.keys())
    for helper_name in ("ensure_core_defaults", "ensure_all_defaults"):
        helper = getattr(target, helper_name, None)
        if callable(helper):
            helper()
            injuries = getattr(getattr(target, "db", None), "injuries", None)
            if isinstance(injuries, Mapping) and injuries:
                return list(injuries.keys())
    return ["body"]


def _choose_hit_location(target, rng):
    options = _get_hit_location_options(target)
    chooser = getattr(rng, "choice", None)
    if callable(chooser):
        return chooser(options)
    return random.choice(options)


def _resolve_combat_state(attacker, target, context=None, *, combat_rng=None, rng=None):
    context = dict(context or {})
    rng = rng or random
    combat_rng = combat_rng or CombatRng(rng if hasattr(rng, "randint") else None)

    offensive_factor = compute_offensive_factor(attacker, target, context, combat_rng=combat_rng)
    evasion_defense = compute_edf(target, attacker, context)
    leftover_of = offensive_factor.total - evasion_defense.total

    context["offensive_factor"] = asdict(offensive_factor)
    context["offensive_factor_total"] = offensive_factor.total
    context["evasion_defense_factor"] = asdict(evasion_defense)
    context["evasion_defense_factor_total"] = evasion_defense.total
    context["accuracy"] = offensive_factor.total
    context["evasion"] = evasion_defense.total
    context["leftover_of"] = leftover_of
    context["hit_roll"] = offensive_factor.rng_pct
    context["final_chance"] = max(0, leftover_of)

    if leftover_of <= 0:
        context["combat_outcome"] = CombatOutcome.EVADED.value
        context["outcome"] = "miss"
        context["quality"] = "evaded"
        return {"hit": False, "details": context}

    foi = compute_foi(attacker, context, rng=rng)
    remaining_foi = foi.total
    context["force_of_impact"] = asdict(foi)
    context["force_of_impact_total"] = foi.total

    parry = compute_parry(target, leftover_of, context)
    shield = compute_shield(target, leftover_of, context)
    context["parry"] = asdict(parry)
    context["shield"] = asdict(shield)

    defense_steps = []
    if parry.parry_score > 0:
        defense_steps.append((parry.parry_score, "parry", parry.block_pct))
    if shield.shield_score > 0:
        defense_steps.append((shield.shield_score, "shield", shield.block_pct))
    defense_steps.sort(key=lambda item: item[0], reverse=True)

    combat_outcome = CombatOutcome.HIT
    for _score, defense_name, block_pct in defense_steps:
        if block_pct <= 0:
            continue
        blocked = max(0, remaining_foi * block_pct // 100)
        remaining_foi = max(0, remaining_foi - blocked)
        if defense_name == "parry":
            combat_outcome = CombatOutcome.PARTIALLY_PARRIED if remaining_foi > 0 else CombatOutcome.FULLY_PARRIED
        else:
            combat_outcome = CombatOutcome.PARTIALLY_SHIELDED if remaining_foi > 0 else CombatOutcome.FULLY_SHIELDED
        if remaining_foi <= 0:
            break

    context["post_defense_foi"] = remaining_foi
    context["combat_outcome"] = combat_outcome.value
    if remaining_foi <= 0:
        context["outcome"] = "miss"
        context["quality"] = "blocked"
        return {"hit": False, "details": context}

    context["outcome"] = "hit"
    context["quality"] = _quality_from_pressure(leftover_of, remaining_foi)
    return {"hit": True, "details": context}


def _quality_from_pressure(leftover_of, post_defense_foi):
    pressure = max(0, _coerce_int(leftover_of)) + max(0, _coerce_int(post_defense_foi))
    if pressure >= 100:
        return "devastating"
    if pressure >= 60:
        return "solid"
    if pressure >= 25:
        return "good"
    return "glancing"


def _scale_raw_damage(raw_damage, target_total):
    if target_total >= raw_damage.total:
        return raw_damage
    if target_total <= 0 or raw_damage.total <= 0:
        return RawDamage(0, 0, 0, 0, 0, 0, multiplier_seed=raw_damage.multiplier_seed)

    components = {
        "puncture": int(raw_damage.puncture or 0),
        "slice": int(raw_damage.slice or 0),
        "impact": int(raw_damage.impact or 0),
        "fire": int(raw_damage.fire or 0),
        "cold": int(raw_damage.cold or 0),
        "electric": int(raw_damage.electric or 0),
    }
    total = max(1, int(raw_damage.total or 0))
    scaled = {}
    remainders = []
    allocated = 0
    for key, value in components.items():
        scaled_value = (value * int(target_total)) // total
        scaled[key] = scaled_value
        allocated += scaled_value
        remainders.append(((value * int(target_total)) % total, key, value))

    leftover = int(target_total) - allocated
    for _remainder, key, source_value in sorted(remainders, reverse=True):
        if leftover <= 0:
            break
        if source_value <= 0:
            continue
        scaled[key] += 1
        leftover -= 1

    return RawDamage(
        puncture=max(0, scaled["puncture"]),
        slice=max(0, scaled["slice"]),
        impact=max(0, scaled["impact"]),
        fire=max(0, scaled["fire"]),
        cold=max(0, scaled["cold"]),
        electric=max(0, scaled["electric"]),
        multiplier_seed=raw_damage.multiplier_seed,
    )


def _consume_physical_barrier(target, reduced_damage, context=None):
    context = context if context is not None else {}
    if reduced_damage.total <= 0:
        return reduced_damage, None

    try:
        from engine.services.state_service import StateService
    except Exception:
        return reduced_damage, None

    barrier = StateService.get_strongest_physical_ward(target)
    if not barrier:
        return reduced_damage, None

    absorbed = min(max(0, int(reduced_damage.total or 0)), int(barrier.get("strength", 0) or 0))
    if absorbed <= 0:
        return reduced_damage, None

    remaining_total = max(0, int(reduced_damage.total or 0) - absorbed)
    consume_result = StateService.consume_ward(target, barrier.get("spell_id") or barrier.get("name"), absorbed)
    depleted = bool((consume_result.data or {}).get("depleted", False)) if consume_result.success else False
    remaining_capacity = int((((consume_result.data or {}).get("effect", {}) or {}).get("strength", 0) or 0)) if consume_result.success else max(0, int(barrier.get("strength", 0) or 0) - absorbed)
    event_type = "weakened"
    if depleted:
        event_type = "depleted"
    elif remaining_total <= 0:
        event_type = "shielded"

    barrier_event = {
        "type": event_type,
        "spell_id": str(barrier.get("spell_id", barrier.get("name", "manifest_force")) or "manifest_force"),
        "spell_name": str(barrier.get("name", "manifest_force") or "manifest_force"),
        "absorbed": absorbed,
        "remaining_capacity": remaining_capacity,
    }
    if context is not None:
        context["barrier_event"] = dict(barrier_event)
    return _scale_raw_damage(reduced_damage, remaining_total), barrier_event


def resolve_attack(attacker, target, context=None, *, combat_rng=None, rng=None):
    details = dict(context or {})
    state = _resolve_combat_state(attacker, target, details, combat_rng=combat_rng, rng=rng)
    details = state["details"]
    hit = bool(state["hit"])
    details["hit"] = hit
    roundtime = calculate_roundtime(attacker, target, details)
    damage = calculate_damage(attacker, target, details, rng=rng) if hit else 0
    return AttackResolution(hit=hit, damage=damage, roundtime=roundtime, details=details)


def calculate_hit(attacker, target, context=None, *, combat_rng=None, rng=None):
    details = context if context is not None else {}
    state = _resolve_combat_state(attacker, target, details, combat_rng=combat_rng, rng=rng)
    details.update(state["details"])
    return bool(state["hit"])


def calculate_damage(attacker, target, context=None, *, rng=None):
    context = context or {}
    rng = rng or random
    profile = context["profile"]
    weapon = context["weapon"]
    skill_name = context["skill_name"]
    skill_rank = attacker.get_skill(skill_name)
    suitability = context["suitability"]
    weapon_effects = context["weapon_effects"]
    leftover_of = _coerce_int(context.get("leftover_of", 0))
    post_defense_foi = _coerce_int(context.get("post_defense_foi", 0))
    current_range = context["current_range"]
    is_ranged_weapon = context["is_ranged_weapon"]
    ranger_aim_stacks = context["ranger_aim_stacks"]
    ambush = context["ambush"]
    ambush_damage_multiplier = context["ambush_damage_multiplier"]
    attacker_tempo_state = context["attacker_tempo_state"]
    surge_state = context["surge_state"]
    crush_state = context["crush_state"]
    frenzy_state = context["frenzy_state"]
    attacker_berserk = context["attacker_berserk"]
    offensive_roar = context["offensive_roar"]
    ranger_pounce = context.get("ranger_pounce")
    snipe_active = context["snipe_active"]
    prepared_snipe = context.get("prepared_snipe") or context.get("ranger_snipe") or {}
    aimed_part = context["aimed_part"]
    aimed_location = context["aimed_location"]
    damage_type = context["damage_type"]
    snipe_config = dict(context.get("snipe_config") or {})

    pressure = max(0, leftover_of) + max(0, post_defense_foi)
    quality = _quality_from_pressure(leftover_of, post_defense_foi)

    critical = rng.randint(1, 100) < 5
    if snipe_active and hasattr(attacker, "is_profession") and attacker.is_profession("ranger") and hasattr(attacker, "get_nature_focus"):
        if RangerSafService.get_display_percent(attacker) >= int(snipe_config.get("mastery_bond_threshold", 80) or 80) and attacker.get_nature_focus() >= int(snipe_config.get("mastery_focus_threshold", 60) or 60):
            critical = critical or rng.randint(1, 100) <= int(snipe_config.get("mastery_crit_bonus", 8) or 8)
    hit_area = determine_hit_area(
        rng=rng,
        leftover_of=max(0, leftover_of),
        original_of=max(1, _coerce_int(context.get("of_total", 1), 1)),
        weapon_balance=max(1, _coerce_int(profile.get("balance", 50), 50)),
        attacker_agility=_coerce_int(attacker.get_stat("agility") if hasattr(attacker, "get_stat") else 0),
        defender_reflex=_coerce_int(target.get_stat("reflex") if hasattr(target, "get_stat") else 0),
        defender_has_tail=bool(getattr(getattr(target, "db", None), "has_tail", False)),
        verb=context.get("maneuver") or context.get("verb") or context.get("weapon_attack_verb") or "attack",
        aimed_at=aimed_location,
        defender_injuries=getattr(getattr(target, "db", None), "injuries", None),
        is_brawling=not weapon or str(skill_name).lower() == "brawling",
        attacker_grappled=bool(context.get("is_grapple")),
        defender_prone=str(getattr(getattr(target, "db", None), "position", "")).lower() == "prone",
    )
    hit_location = body_part_to_key(hit_area.area)
    location_name = target.format_body_part_name(hit_location) if hasattr(target, "format_body_part_name") else hit_location

    raw_damage = compute_damage(
        profile,
        attacker_strength=_coerce_int(attacker.get_stat("strength") if hasattr(attacker, "get_stat") else 0),
        leftover_of=max(0, leftover_of),
        maneuver=context.get("maneuver") or context.get("verb") or context.get("weapon_attack_verb"),
        rng=rng,
        combat_rng=None,
        ammo_profile=context.get("ammo_profile"),
    )
    if hasattr(attacker, "get_barbarian_roar_offense_penalty"):
        penalty_key = "missile_damage" if is_ranged_weapon else "melee_damage"
        damage_penalty = _coerce_int(attacker.get_barbarian_roar_offense_penalty(penalty_key))
        if damage_penalty > 0:
            raw_damage = max(1, int(round(float(raw_damage) * max(0.0, (100.0 - float(damage_penalty))) / 100.0)))
    if hasattr(attacker, "get_barbarian_dance_offense_bonus"):
        bonus_key = "missile_damage" if is_ranged_weapon else "melee_damage"
        damage_bonus = _coerce_int(attacker.get_barbarian_dance_offense_bonus(bonus_key))
        if damage_bonus > 0:
            raw_damage = max(1, int(round(float(raw_damage) * (100.0 + float(damage_bonus)) / 100.0)))

    damage_multiplier = 1.0
    if critical:
        damage_multiplier *= 2.0
    if is_ranged_weapon:
        if current_range == "melee":
            damage_multiplier *= 0.75
        elif current_range == "near":
            damage_multiplier *= 1.05
        elif current_range == "far":
            damage_multiplier *= 1.10
        if ranger_aim_stacks:
            damage_multiplier *= 1 + (ranger_aim_stacks * float(snipe_config.get("aim_damage_per_stack", 0.05) or 0.05))
    if ambush:
        damage_multiplier *= ambush_damage_multiplier
    if attacker_tempo_state == "surging":
        damage_multiplier *= 1.10
    elif attacker_tempo_state == "frenzied":
        damage_multiplier *= 1.20
    if isinstance(crush_state, dict):
        damage_multiplier *= float(crush_state.get("damage_multiplier", 1.0) or 1.0)
    if isinstance(frenzy_state, dict):
        damage_multiplier *= float(frenzy_state.get("damage_multiplier", 1.0) or 1.0)
    if attacker_berserk:
        damage_multiplier *= float(attacker_berserk.get("damage_multiplier", 1.0) or 1.0)
    if isinstance(offensive_roar, dict):
        damage_multiplier *= 1.05
    if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == target.id:
        damage_multiplier *= 1 + float(ranger_pounce.get("damage_bonus", 0) or 0.0)
    if snipe_active:
        damage_multiplier *= float(prepared_snipe.get("damage_multiplier", 1.0) or 1.0)
    if getattr(target.db, "roughed", False):
        damage_multiplier *= 1.1

    flat_bonus = int(weapon_effects.get("damage_bonus", 0))
    flat_bonus += max(0, leftover_of // 12)
    flat_bonus += max(0, post_defense_foi // 6)
    flat_bonus += int(suitability * 0.3)
    flat_bonus += int(skill_rank * 0.2)
    flat_bonus -= min(25, attacker.get_hand_penalty())
    if skill_rank > 30:
        flat_bonus += 2
    if isinstance(surge_state, dict):
        flat_bonus += int(surge_state.get("damage", 0) or 0)
    if aimed_part == "head":
        flat_bonus += 2
    elif aimed_part == "arm":
        flat_bonus += 1

    scaled_raw = RawDamage(
        puncture=max(0, int(round(raw_damage.puncture * damage_multiplier)) + flat_bonus),
        slice=max(0, int(round(raw_damage.slice * damage_multiplier)) + flat_bonus),
        impact=max(0, int(round(raw_damage.impact * damage_multiplier)) + flat_bonus),
        fire=max(0, int(round(raw_damage.fire * damage_multiplier))),
        cold=max(0, int(round(raw_damage.cold * damage_multiplier))),
        electric=max(0, int(round(raw_damage.electric * damage_multiplier))),
        multiplier_seed=raw_damage.multiplier_seed,
    )

    armor_list = target.get_armor_for_bodypart(hit_location) if hasattr(target, "get_armor_for_bodypart") else []
    reduced_damage = scaled_raw
    armor_absorbed = False
    flat_reduction = [0, 0, 0]
    pct_reduction = [0, 0, 0, 0, 0, 0]
    for armor in armor_list:
        if hasattr(armor, "get_armor_profile"):
            armor_profile = armor.get_armor_profile() or {}
        else:
            armor_profile = {}
        armor_skill_name = str(armor_profile.get("type") or "armor")
        armor_skill = _coerce_int(target.get_skill(armor_skill_name) if hasattr(target, "get_skill") else 0)
        reduction = apply_armor_reduction(
            reduced_damage,
            armor_profile,
            armor_skill=armor_skill,
            maneuver_mod=_coerce_int(context.get("maneuver_mod", 10), 10),
            multi_armor_penalty=_coerce_int(context.get("multi_armor_penalty", max(0, len(armor_list) - 1) * 4), 0),
            rng=rng,
        )
        armor_absorbed = armor_absorbed or reduction.total < reduced_damage.total
        flat_reduction = [left + right for left, right in zip(flat_reduction, reduction.flat_reduction)]
        pct_reduction = [left + right for left, right in zip(pct_reduction, reduction.percent_reduction)]
        reduced_damage = RawDamage(
            puncture=reduction.puncture,
            slice=reduction.slice,
            impact=reduction.impact,
            fire=reduction.fire,
            cold=reduction.cold,
            electric=reduction.electric,
            multiplier_seed=reduced_damage.multiplier_seed,
        )

    reduced_damage, barrier_event = _consume_physical_barrier(target, reduced_damage, context)

    current_hp = _coerce_int(getattr(getattr(target, "db", None), "hp", 0) or getattr(getattr(target, "db", None), "cbhp", 0), 1)
    max_hp = _coerce_int(getattr(getattr(target, "db", None), "max_hp", 0) or getattr(getattr(target, "db", None), "mbhp", 0), max(1, current_hp))
    body_part = hit_area.area if isinstance(hit_area.area, BodyPart) else BodyPart.CHEST
    wound_result = apply_wounds(
        reduced_damage,
        body_part=body_part,
        max_hp=max_hp,
        current_hp=max(1, current_hp),
        rng=rng,
    )
    damage = wound_result.hp_damage

    if hasattr(attacker, "apply_death_sting_to_damage"):
        damage = attacker.apply_death_sting_to_damage(damage)
    damage += _get_bless_damage_bonus(attacker, target)

    target_evasion = int(target.get_skill("evasion") or 0) if hasattr(target, "get_skill") else 0
    if skill_rank <= EARLY_GAME_DAMAGE_CLAMP_RANK and target_evasion <= EARLY_GAME_DAMAGE_CLAMP_RANK:
        max_hp = max(1, int(target.db.max_hp or 1))
        damage = min(damage, max(1, int(round(max_hp * EARLY_GAME_DAMAGE_CLAMP_RATIO))))

    damage = max(0, int(damage))
    context["armor_absorbed"] = armor_absorbed
    context["attack_context"] = {"damage_type": reduced_damage.dominant_type}
    context["raw_damage"] = asdict(scaled_raw)
    context["post_armor_damage"] = asdict(reduced_damage)
    context["barrier_event"] = dict(barrier_event or {})
    context["armor_flat_reduction"] = tuple(flat_reduction)
    context["armor_percent_reduction"] = tuple(pct_reduction)
    context["critical"] = critical
    context["damage"] = damage
    context["hit_location"] = hit_location
    context["location_name"] = location_name
    context["quality"] = quality
    context["damage_type"] = reduced_damage.dominant_type
    context["hit_area_targeted"] = hit_area.was_targeted
    context["hit_area_target_success"] = hit_area.targeting_succeeded
    context["hit_area_retarget_count"] = hit_area.retarget_count
    context["wound_level"] = wound_result.wound_level
    context["external_wound_level"] = wound_result.external_wound_level
    context["internal_wound_level"] = wound_result.internal_wound_level
    context["destroyed_parts"] = wound_result.destroyed_parts
    context["stamina_denominator"] = wound_result.stamina_denominator
    return damage


def calculate_roundtime(attacker, target, context=None):
    context = context or {}
    profile = context["profile"]
    attacker_berserk = context["attacker_berserk"]
    ambush = context["ambush"]
    partial_ambush = context.get("partial_ambush", False)
    hit = context.get("hit", False)

    explicit_roundtime = context.get("verb_rt")
    if explicit_roundtime is not None:
        action_roundtime = float(explicit_roundtime)
    else:
        action_roundtime = profile.get("speed", profile.get("roundtime", 3.0))
    if attacker_berserk:
        action_roundtime = max(1.0, action_roundtime + float(attacker_berserk.get("roundtime_modifier", 0.0) or 0.0))
    if hasattr(attacker, "is_warrior_overextended") and attacker.is_warrior_overextended():
        action_roundtime += 1
    if ambush:
        if hit:
            action_roundtime = max(action_roundtime, 3.0)
            if getattr(attacker.db, "position_state", "neutral") == "advantaged":
                action_roundtime -= 1
            if partial_ambush:
                action_roundtime += 1
            action_roundtime = max(1, min(action_roundtime, 5))
        else:
            if getattr(attacker.db, "position_state", "neutral") == "advantaged":
                action_roundtime -= 1
            action_roundtime = max(1, min(action_roundtime + 1, 5))
    if hasattr(attacker, "get_barbarian_roar_attack_roundtime_penalty"):
        action_roundtime += float(attacker.get_barbarian_roar_attack_roundtime_penalty() or 0.0)

    cleanup = apply_cleanup(
        attacker,
        target,
        leftover_of=_coerce_int(context.get("leftover_of", 0), 0),
        base_roundtime=action_roundtime,
        fatigue_cost=_coerce_int(context.get("fatigue_cost", 0), 0),
    )

    context["roundtime"] = cleanup.roundtime
    context["fatigue_cost"] = cleanup.fatigue_change
    context["combat_cleanup_sentinel"] = cleanup.sentinel
    context["attacker_mm"] = cleanup.attacker_mm
    context["defender_mm"] = cleanup.defender_mm
    return cleanup.roundtime