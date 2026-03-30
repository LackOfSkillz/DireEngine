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