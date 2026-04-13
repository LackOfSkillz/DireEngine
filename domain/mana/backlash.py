import math


def _clamp(value, min_value, max_value):
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _coerce_number(value, default=0.0):
    if value is None:
        return float(default)
    return float(value)


def calculate_spell_difficulty(spell, mana_input, effective_env_mana):
    spell_data = dict(spell or {})
    base_difficulty = _coerce_number(spell_data.get("base_difficulty"), default=0.0)
    safe_mana = max(0.0, _coerce_number(spell_data.get("safe_mana"), default=0.0))
    tier = max(0.0, _coerce_number(spell_data.get("tier"), default=0.0))
    mana_pressure = max(0.0, _coerce_number(mana_input) - safe_mana) * 1.25
    complexity_pressure = tier * 6.0
    environment_pressure = max(0.0, 1.0 - _coerce_number(effective_env_mana, default=1.0)) * 12.0
    if _coerce_number(effective_env_mana, default=1.0) < 0.50:
        environment_pressure += 8.0
    return base_difficulty + mana_pressure + complexity_pressure + environment_pressure


def calculate_control_score(character, spell):
    character_data = dict(character or {})
    spell_data = dict(spell or {})
    primary_magic_skill = _coerce_number(character_data.get("primary_magic_skill"), default=0.0)
    attunement_skill = _coerce_number(character_data.get("attunement_skill"), default=0.0)
    arcana_skill = _coerce_number(character_data.get("arcana_skill"), default=0.0)
    intelligence = _coerce_number(character_data.get("intelligence"), default=0.0)
    discipline = _coerce_number(character_data.get("discipline"), default=0.0)
    focus_state_bonus = _coerce_number(character_data.get("focus_state_bonus"), default=0.0)
    profession = str(character_data.get("profession", "") or "").strip().lower()
    profession_bonus_map = {
        "empath": 2.0,
        "cleric": 2.0,
        "moon mage": 4.0,
        "moon_mage": 4.0,
    }
    profession_control_bonus = _coerce_number(
        spell_data.get("profession_control_bonus", character_data.get("profession_control_bonus", profession_bonus_map.get(profession, 0.0))),
        default=0.0,
    )
    return (
        primary_magic_skill * 0.55
        + attunement_skill * 0.30
        + arcana_skill * 0.10
        + intelligence * 0.35
        + discipline * 0.30
        + focus_state_bonus
        + profession_control_bonus
    )


def calculate_strain_penalty(attunement_current, attunement_max):
    maximum = max(1.0, _coerce_number(attunement_max, default=1.0))
    current = _clamp(_coerce_number(attunement_current, default=0.0), 0.0, maximum)
    attunement_ratio = current / maximum
    return (1.0 - attunement_ratio) * 18.0


def calculate_cast_margin(control_score, difficulty, strain_penalty, random_roll):
    return (
        _coerce_number(control_score)
        - _coerce_number(difficulty)
        - _coerce_number(strain_penalty)
        + _coerce_number(random_roll)
    )


def resolve_success_band(cast_margin):
    margin = _coerce_number(cast_margin)
    if margin >= 20.0:
        return "excellent"
    if margin >= 8.0:
        return "solid"
    if margin >= 0.0:
        return "partial"
    if margin >= -10.0:
        return "failure"
    return "backlash"


def calculate_backlash_chance(spell, mana_input, cast_margin, effective_env_mana):
    spell_data = dict(spell or {})
    safe_mana = max(1.0, _coerce_number(spell_data.get("safe_mana"), default=1.0))
    overprep_ratio = _coerce_number(mana_input) / safe_mana
    backlash = max(
        0.0,
        (overprep_ratio - 1.0) * 18.0
        + max(0.0, -_coerce_number(cast_margin)) * 1.5
        + max(0.0, 1.0 - _coerce_number(effective_env_mana, default=1.0)) * 10.0,
    )
    if _coerce_number(effective_env_mana, default=1.0) > 1.30 and overprep_ratio > 1.0:
        backlash += 6.0
    return _clamp(backlash, 0.0, 75.0)


def calculate_backlash_severity(spell, mana_input, cast_margin):
    spell_data = dict(spell or {})
    safe_mana = max(0.0, _coerce_number(spell_data.get("safe_mana"), default=0.0))
    severity = max(
        1,
        int(
            math.ceil(
                (
                    max(0.0, -_coerce_number(cast_margin))
                    + max(0.0, _coerce_number(mana_input) - safe_mana) * 0.8
                )
                / 6.0
            )
        ),
    )
    return int(_clamp(severity, 1, 5))


def resolve_backlash_payload(character, severity, spell):
    character_data = dict(character or {})
    spell_data = dict(spell or {})
    severity_value = int(_clamp(_coerce_number(severity, default=1.0), 1.0, 5.0))
    mana_input = max(0.0, _coerce_number(spell_data.get("mana_input"), default=0.0))
    profession = str(character_data.get("profession", "") or "").strip().lower()

    payload = {
        "severity": severity_value,
        "attunement_burn_ratio": 0.0,
        "vitality_loss": 0,
        "devotion_loss_ratio": 0.0,
        "shock_gain": 0,
        "focus_penalty_duration": 0,
        "prep_collapse": severity_value >= 3,
        "status_ailment": severity_value >= 5,
        "lingering_penalty": severity_value >= 4,
    }

    if profession == "empath":
        payload["shock_gain"] = severity_value * 8
        payload["attunement_burn_ratio"] = 0.03 * severity_value
        return payload
    if profession == "cleric":
        payload["devotion_loss_ratio"] = 0.04 * severity_value
        payload["attunement_burn_ratio"] = 0.03 * severity_value
        return payload
    if profession in {"moon mage", "moon_mage"}:
        payload["focus_penalty_duration"] = severity_value * 2
        payload["attunement_burn_ratio"] = 0.02 * severity_value
        return payload
    if profession in {"warrior mage", "warrior_mage"}:
        payload["vitality_loss"] = int(round(severity_value * (4.0 + mana_input * 0.15)))
        payload["attunement_burn_ratio"] = 0.02 * severity_value
        return payload

    generic_burn = {1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}
    generic_vitality = {1: 0, 2: 2, 3: 5, 4: 10, 5: 15}
    payload["attunement_burn_ratio"] = generic_burn.get(severity_value, 0.25)
    payload["vitality_loss"] = generic_vitality.get(severity_value, 15)
    return payload