from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
import math
import random

from domain.combat.rng import CombatRng


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
    maneuver_mod_pct: int
    total: int = field(init=False)

    def __post_init__(self):
        total = max(0, int(self.reflex or 0) + int(self.evasion_skill or 0))
        total = total * max(0, int(self.usable_evasion_pct or 0)) // 100
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


@dataclass(frozen=True)
class ShieldSubcontest:
    """Shield block magnitude bridge from GSL S00046."""

    shield_score: int
    block_pct: int


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
        ranger_snipe = dict(context.get("ranger_snipe") or {})
        base += _coerce_int(ranger_snipe.get("accuracy_bonus", 0))
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

    if hasattr(defender, "apply_death_sting_to_contest_value"):
        evasion_skill = defender.apply_death_sting_to_contest_value(evasion_skill)

    target_maneuver_hindrance, _ = defender.get_total_hindrance() if hasattr(defender, "get_total_hindrance") else (0, 0)
    maneuver_mod_pct = max(10, 100 - min(75, int(round(_coerce_float(target_maneuver_hindrance) * 6))))
    maneuver_mod_pct += _coerce_int((defender.get_position_modifiers() or {}).get("defense", 0)) if hasattr(defender, "get_position_modifiers") else 0

    total = EvasionDefenseFactor(
        reflex=max(0, reflex),
        evasion_skill=max(0, evasion_skill),
        usable_evasion_pct=max(0, usable_evasion_pct),
        maneuver_mod_pct=max(0, maneuver_mod_pct),
    )
    if context.get("strong_ambush"):
        return EvasionDefenseFactor(reflex=0, evasion_skill=0, usable_evasion_pct=0, maneuver_mod_pct=0)
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
    if leftover_of <= 0:
        return ParrySubcontest(parry_score=0, leftover_of=leftover_of, parry_percent=0, block_pct=0)
    defender_weapon_profile = defender.get_weapon_profile() if hasattr(defender, "get_weapon_profile") else {}
    parry_skill_name = str(defender_weapon_profile.get("skill") or context.get("skill_name") or "brawling")
    parry_skill = _coerce_int(defender.get_skill(parry_skill_name) if hasattr(defender, "get_skill") else 0)
    agility = _coerce_int(defender.get_stat("agility") if hasattr(defender, "get_stat") else 0)
    reflex = _coerce_int(defender.get_stat("reflex") if hasattr(defender, "get_stat") else 0)
    balance = _coerce_int(defender_weapon_profile.get("balance", 50), 50)
    parry_score = max(0, parry_skill + reflex + agility + (balance // 5))
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
    )


def compute_shield(defender, leftover_of, context=None):
    context = context or {}
    equipment = {}
    if hasattr(defender, "get_equipment"):
        equipment = dict(defender.get_equipment() or {})
    else:
        equipment = dict(getattr(getattr(defender, "db", None), "equipment", {}) or {})
    shield_items = list(equipment.get("shield", []) or [])
    if leftover_of <= 0 or not shield_items:
        return ShieldSubcontest(shield_score=0, block_pct=0)
    shield_item = shield_items[0]
    shield_skill = _coerce_int(defender.get_skill("shield") if hasattr(defender, "get_skill") else 0)
    min_def = _coerce_int(getattr(getattr(shield_item, "db", None), "mindef", SHIELD_MIN_DEF), SHIELD_MIN_DEF)
    max_def = _coerce_int(getattr(getattr(shield_item, "db", None), "maxdef", SHIELD_MAX_DEF), SHIELD_MAX_DEF)
    shield_score = min(max_def, min_def + shield_skill)
    return ShieldSubcontest(shield_score=shield_score, block_pct=max(0, min(100, shield_score)))


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
    ranger_snipe = context["ranger_snipe"]
    aimed_part = context["aimed_part"]
    aimed_location = context["aimed_location"]
    damage_type = context["damage_type"]
    snipe_config = dict(context.get("snipe_config") or {})

    base = max(1, int(profile.get("damage") or 1)) if weapon else 1
    if weapon:
        damage_min = max(1, int(profile.get("damage_min") or base))
        damage_max = max(damage_min, int(profile.get("damage_max") or damage_min))
        base = max(base, rng.randint(damage_min, damage_max))
    damage = base + int(skill_rank * 0.2) + int(suitability * 0.3)
    if skill_rank > 30:
        damage += 2
    damage += int(weapon_effects.get("damage_bonus", 0))
    damage -= min(25, attacker.get_hand_penalty())
    damage += max(0, leftover_of // 12)
    damage += max(0, post_defense_foi // 6)
    pressure = max(0, leftover_of) + max(0, post_defense_foi)
    quality = _quality_from_pressure(leftover_of, post_defense_foi)
    if pressure > 120:
        quality = "devastating"
        damage = int(round(damage * 1.8))
    elif pressure > 80:
        quality = "solid"
        damage = int(round(damage * 1.4))
    elif pressure > 40:
        quality = "good"
        damage = int(round(damage * 1.1))
    elif pressure > 0:
        quality = "glancing"
        damage = max(1, int(round(damage * 0.7)))

    critical = rng.randint(1, 100) < 5
    if snipe_active and hasattr(attacker, "get_wilderness_bond") and hasattr(attacker, "get_nature_focus"):
        if attacker.get_wilderness_bond() >= int(snipe_config.get("mastery_bond_threshold", 80) or 80) and attacker.get_nature_focus() >= int(snipe_config.get("mastery_focus_threshold", 60) or 60):
            critical = critical or rng.randint(1, 100) <= int(snipe_config.get("mastery_crit_bonus", 8) or 8)
    if critical:
        damage *= 2

    if is_ranged_weapon:
        if current_range == "melee":
            damage = int(round(damage * 0.75))
        elif current_range == "near":
            damage = int(round(damage * 1.05))
        elif current_range == "far":
            damage = int(round(damage * 1.10))
        if ranger_aim_stacks:
            damage = int(round(damage * (1 + (ranger_aim_stacks * float(snipe_config.get("aim_damage_per_stack", 0.05) or 0.05)))))

    if ambush:
        damage = int(round(damage * ambush_damage_multiplier))
    if attacker_tempo_state == "surging":
        damage = int(round(damage * 1.10))
    elif attacker_tempo_state == "frenzied":
        damage = int(round(damage * 1.20))
    if isinstance(surge_state, dict):
        damage += int(surge_state.get("damage", 0) or 0)
    if isinstance(crush_state, dict):
        damage = int(round(damage * float(crush_state.get("damage_multiplier", 1.0) or 1.0)))
    if isinstance(frenzy_state, dict):
        damage = int(round(damage * float(frenzy_state.get("damage_multiplier", 1.0) or 1.0)))
    if attacker_berserk:
        damage = int(round(damage * float(attacker_berserk.get("damage_multiplier", 1.0) or 1.0)))
    if isinstance(offensive_roar, dict):
        damage = int(round(damage * 1.05))
    if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == target.id:
        damage = int(round(damage * (1 + float(ranger_pounce.get("damage_bonus", 0) or 0.0))))
    if snipe_active:
        damage = int(round(damage * float(ranger_snipe.get("damage_multiplier", 1.0) or 1.0)))

    if getattr(target.db, "roughed", False):
        damage = int(round(damage * 1.1))
    if aimed_part == "head":
        damage += 2
    elif aimed_part == "arm":
        damage += 1

    if aimed_location:
        hit_location = aimed_location
        location_name = aimed_part
    else:
        # TODO(DRG-024a): Replace placeholder hit-location selection with S00047.
        hit_location = _choose_hit_location(target, rng)
        location_name = target.format_body_part_name(hit_location) if hasattr(target, "format_body_part_name") else str(hit_location)

    armor_list = target.get_armor_for_bodypart(hit_location) if hasattr(target, "get_armor_for_bodypart") else target.get_armor_covering(hit_location)
    protection = target.get_total_armor_protection(hit_location) if hasattr(target, "get_total_armor_protection") else sum(target.get_armor_protection_value(armor) for armor in armor_list)
    armor_absorbed = False
    if protection:
        damage = max(1, damage - int(round(protection)))
        armor_absorbed = True
    if hasattr(attacker, "apply_death_sting_to_damage"):
        damage = attacker.apply_death_sting_to_damage(damage)

    target_evasion = int(target.get_skill("evasion") or 0) if hasattr(target, "get_skill") else 0
    if skill_rank <= EARLY_GAME_DAMAGE_CLAMP_RANK and target_evasion <= EARLY_GAME_DAMAGE_CLAMP_RANK:
        max_hp = max(1, int(target.db.max_hp or 1))
        damage = min(damage, max(1, int(round(max_hp * EARLY_GAME_DAMAGE_CLAMP_RATIO))))

    damage = max(0, int(damage))
    context["armor_absorbed"] = armor_absorbed
    context["attack_context"] = {"damage_type": damage_type}
    context["critical"] = critical
    context["damage"] = damage
    context["hit_location"] = hit_location
    context["location_name"] = location_name
    context["quality"] = quality
    return damage


def calculate_roundtime(attacker, target, context=None):
    context = context or {}
    profile = context["profile"]
    attacker_berserk = context["attacker_berserk"]
    ambush = context["ambush"]
    partial_ambush = context.get("partial_ambush", False)
    hit = context.get("hit", False)

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

    context["roundtime"] = action_roundtime
    return action_roundtime