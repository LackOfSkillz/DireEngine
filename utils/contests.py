import random


DEBUG_CONTESTS = False


def _apply_character_modifier(character, value):
    if character and hasattr(character, "apply_death_sting_to_contest_value"):
        return character.apply_death_sting_to_contest_value(value)
    return value


def contest(attacker_value, defender_value):
    roll_a = attacker_value + random.randint(1, 100)
    roll_d = defender_value + random.randint(1, 100)
    diff = roll_a - roll_d
    return roll_a, roll_d, diff


def resolve_outcome(diff):
    if diff <= 0:
        return "fail"
    if diff < 20:
        return "partial"
    if diff < 50:
        return "success"
    return "strong"


def get_difficulty_band(diff):
    if diff <= -20:
        return "too_hard"
    if diff <= 0:
        return "hard"
    if diff < 20:
        return "ideal"
    if diff < 50:
        return "easy"
    return "trivial"


def soften_extreme_failure_margin(diff, threshold=-30.0, target=-20.0, scale=0.6):
    if diff >= threshold:
        return diff
    return target + ((diff - threshold) * float(scale))


def run_contest(attacker_value, defender_value, attacker=None, defender=None):
    attacker_value = _apply_character_modifier(attacker, attacker_value)
    defender_value = _apply_character_modifier(defender, defender_value)
    roll_a, roll_d, diff = contest(attacker_value, defender_value)
    outcome = resolve_outcome(diff)
    band = get_difficulty_band(diff)

    if DEBUG_CONTESTS:
        print(f"[CONTEST] A:{roll_a} D:{roll_d} DIFF:{diff} OUT:{outcome}")

    return {
        "attacker_roll": roll_a,
        "defender_roll": roll_d,
        "diff": diff,
        "outcome": outcome,
        "difficulty": band,
    }


def run_group_contest_against_best(
    attacker_value,
    defender_values,
    *,
    attacker=None,
    defenders=None,
    support_slots=3,
    support_scale=0.09,
    crowd_penalty_per_observer=1.2,
    crowd_penalty_cap=10.0,
):
    attacker_value = _apply_character_modifier(attacker, attacker_value)
    attacker_roll = attacker_value + random.randint(1, 100)

    defender_entries = []
    defender_list = list(defenders or [])
    for index, defender_value in enumerate(list(defender_values or [])):
        defender = defender_list[index] if index < len(defender_list) else None
        adjusted_defender_value = _apply_character_modifier(defender, defender_value)
        defender_roll = adjusted_defender_value + random.randint(1, 100)
        individual_diff = attacker_roll - defender_roll
        defender_entries.append(
            {
                "defender": defender,
                "defender_value": adjusted_defender_value,
                "defender_roll": defender_roll,
                "diff": individual_diff,
                "outcome": resolve_outcome(individual_diff),
                "difficulty": get_difficulty_band(individual_diff),
            }
        )

    if not defender_entries:
        diff = attacker_roll
        return {
            "attacker_roll": attacker_roll,
            "defender_roll": 0.0,
            "effective_defender_roll": 0.0,
            "primary_pressure": 0.0,
            "support_pressure": 0.0,
            "crowd_penalty": 0.0,
            "observer_pressure": 0.0,
            "observer_count": 0,
            "diff": diff,
            "outcome": resolve_outcome(diff),
            "difficulty": get_difficulty_band(diff),
            "individual_results": [],
        }

    sorted_entries = sorted(defender_entries, key=lambda entry: entry["defender_roll"], reverse=True)
    observer_count = len(sorted_entries)
    primary_pressure = float(sorted_entries[0]["defender_roll"])
    support_pressure = 0.0
    for entry in sorted_entries[1 : 1 + max(0, int(support_slots or 0))]:
        base_support = max(0.0, float(entry["defender_roll"]) - (primary_pressure * 0.5))
        engagement = random.uniform(0.35, 1.0) if observer_count >= 6 else 1.0
        support_pressure += base_support * float(support_scale or 0.0) * engagement
    crowd_penalty = min(
        float(crowd_penalty_cap or 0.0),
        max(0, observer_count - 1) * float(crowd_penalty_per_observer or 0.0),
    )
    effective_defender_roll = primary_pressure + support_pressure
    if observer_count >= 6:
        effective_defender_roll *= 0.92
    diff = attacker_roll - effective_defender_roll - crowd_penalty
    diff = soften_extreme_failure_margin(diff)
    outcome = resolve_outcome(diff)
    band = get_difficulty_band(diff)

    return {
        "attacker_roll": attacker_roll,
        "defender_roll": primary_pressure,
        "effective_defender_roll": effective_defender_roll,
        "primary_pressure": primary_pressure,
        "support_pressure": support_pressure,
        "crowd_penalty": crowd_penalty,
        "observer_pressure": effective_defender_roll + crowd_penalty,
        "observer_count": observer_count,
        "diff": diff,
        "outcome": outcome,
        "difficulty": band,
        "individual_results": sorted_entries,
    }


def get_skill_total(character, skill, stat="agility"):
    skill_val = character.get_skill(skill)
    stat_val = (character.db.stats or {}).get(stat, 10)
    return skill_val + stat_val


def apply_learning(character, skill, difficulty):
    if difficulty in {"trivial", "too_hard"}:
        return

    character.use_skill(skill, apply_roundtime=False, emit_placeholder=False)


def skill_vs_skill(attacker, defender, skill_a, skill_d, stat_a="agility", stat_d="agility"):
    a_val = get_skill_total(attacker, skill_a, stat_a)
    d_val = get_skill_total(defender, skill_d, stat_d)
    return run_contest(a_val, d_val, attacker=attacker, defender=defender)