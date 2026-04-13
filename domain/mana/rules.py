import math
import random

from domain.mana.backlash import (
    calculate_backlash_chance as calculate_backlash_chance_by_margin,
    calculate_cast_margin,
    calculate_control_score,
    calculate_strain_penalty,
)

from domain.mana.constants import (
    MANA_MAX,
    MANA_MIN,
    MAX_FINAL_POWER_MULTIPLIER,
    MAX_HARNESS_EFFICIENCY,
    MIN_HARNESS_EFFICIENCY,
)


def clamp(value, min_value, max_value):
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def clamp_mana(value):
    return clamp(float(value), MANA_MIN, MANA_MAX)


def clamp_backlash(value):
    return clamp(float(value), 0.0, 75.0)


def calculate_backlash_chance(*args):
    if len(args) == 4:
        spell, mana_input, cast_margin, effective_env_mana = args
        return calculate_backlash_chance_by_margin(spell, mana_input, cast_margin, effective_env_mana)

    if len(args) == 5:
        prep_cost, attunement_current_before_cast, mana_input, min_prep, primary_magic_skill = args
        strain_ratio = float(prep_cost) / max(1.0, float(attunement_current_before_cast))
        difficulty_pressure = float(mana_input) / max(1.0, float(min_prep))
        backlash = max(
            0.0,
            (strain_ratio - 0.35) * 40.0
            + (difficulty_pressure - 1.5) * 10.0
            - float(primary_magic_skill) * 0.01,
        )
        return clamp_backlash(backlash)

    raise TypeError("calculate_backlash_chance expects either 4 or 5 positional arguments.")


def calculate_attunement_max(attunement_skill, intelligence, discipline, circle):
    value = (
        40
        + float(attunement_skill) * 0.60
        + float(intelligence) * 0.80
        + float(discipline) * 0.50
        + float(circle) * 0.75
    )
    return float(max(40.0, value))


def calculate_effective_env_mana(room_mana, global_modifier, profession_modifier):
    value = float(room_mana) * float(global_modifier) * float(profession_modifier)
    return clamp_mana(value)


def calculate_ambient_floor_required(min_prep):
    return max(1, int(math.ceil(float(min_prep) * 0.10)))


def calculate_attunement_regen(attunement_current, attunement_maximum, attunement_skill, wisdom, regen_modifiers=1.0):
    maximum = float(attunement_maximum)
    current = float(attunement_current)
    if maximum <= 0:
        missing_ratio = 0.0
    else:
        missing_ratio = max(0.0, (maximum - current) / maximum)

    base = 0.8 + float(attunement_skill) * 0.015 + float(wisdom) * 0.020
    regen = base * (0.50 + missing_ratio) * float(regen_modifiers)
    return max(0.0, regen)


def calculate_prep_cost(mana_input, effective_env_mana):
    env_discount = 0.75 + (float(effective_env_mana) * 0.25)
    cost = float(mana_input) / env_discount
    return int(math.ceil(cost))


def calculate_harness_efficiency(attunement_skill, arcana_skill):
    value = 0.60 + float(attunement_skill) * 0.0015 + float(arcana_skill) * 0.0010
    return clamp(float(value), MIN_HARNESS_EFFICIENCY, MAX_HARNESS_EFFICIENCY)


def calculate_harness_cost(requested_harness, harness_efficiency):
    efficiency = clamp(float(harness_efficiency), MIN_HARNESS_EFFICIENCY, MAX_HARNESS_EFFICIENCY)
    return int(math.ceil(float(requested_harness) / efficiency))


def calculate_final_spell_power(
    mana_input,
    primary_magic_skill,
    effective_env_mana,
    attunement_current,
    attunement_maximum,
    profession_cast_modifier=1.0,
):
    mana_input_value = float(mana_input)
    skill_factor = 1.00 + (float(primary_magic_skill) / 1000.0)
    env_factor = 0.75 + (float(effective_env_mana) * 0.35)
    if float(attunement_maximum) <= 0:
        control_ratio = 0.0
    else:
        control_ratio = clamp(float(attunement_current) / float(attunement_maximum), 0.0, 1.0)
    control_factor = 0.85 + control_ratio * 0.25
    value = mana_input_value * skill_factor * env_factor * control_factor * float(profession_cast_modifier)
    return min(value, mana_input_value * MAX_FINAL_POWER_MULTIPLIER)


def calculate_cyclic_drain(prepared_mana, ticks_active=0):
    base_cyclic_drain = max(1, int(math.ceil(float(prepared_mana) * 0.08)))
    instability = 1.0 + (max(0, int(ticks_active or 0)) * 0.03)
    return max(1, int(math.ceil(base_cyclic_drain * instability)))


def calculate_cyclic_control_margin(character, spell, ticks_active, random_roll_small=None):
    character_data = dict(character or {})
    spell_data = dict(spell or {})
    control_score = calculate_control_score(character_data, spell_data)
    base_difficulty = float(spell_data.get("base_difficulty", 0.0) or 0.0)
    strain_penalty = calculate_strain_penalty(
        character_data.get("attunement_current", 0.0),
        character_data.get("attunement_max", 0.0),
    )
    if random_roll_small is None:
        random_roll_small = random.uniform(-4.0, 4.0)
    return calculate_cast_margin(
        control_score,
        base_difficulty + (max(0, int(ticks_active or 0)) * 1.5),
        strain_penalty,
        random_roll_small,
    )