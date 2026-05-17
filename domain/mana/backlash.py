from collections.abc import Mapping
import random


_SKILL_BUFFER = 15.0
_SCALE_FACTOR = 100.0
_FULL_PREP_MULTIPLIER = 1.20
_PROFESSION_PENALTY_MULTIPLIER = {
    "barbarian": 50.0,
    "commoner": 50.0,
    "thief": 80.0,
    "trader": 80.0,
}


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


def _coerce_mapping(value):
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return value
    return dict(value)


def _random_factor():
    """GSL S00218:425-430 - triple-averaged random percent centered around 102%."""
    return ((random.randint(40, 90) + random.randint(40, 90) + random.randint(40, 90)) // 6) + 70


def calculate_spell_difficulty(spell, mana_input, effective_env_mana):
    """
    Compute total spell difficulty per GSL Magic v2.1.

    Source:
      S00830:175-178 - base difficulty uses a1 * 100
      S00830:305-380 - excess mana adds diff_per_extra_mana per mana over minimum

    Returns total difficulty scaled by 100.
    """
    spell_data = _coerce_mapping(spell)
    base_difficulty = max(0.0, _coerce_number(spell_data.get("base_difficulty"), default=0.0))
    mana_min = max(0.0, _coerce_number(spell_data.get("mana_min", spell_data.get("safe_mana")), default=0.0))
    diff_per_extra_mana = max(0.0, _coerce_number(spell_data.get("diff_per_extra_mana"), default=0.0))
    mana_input_value = max(0.0, _coerce_number(mana_input, default=0.0))
    excess_mana = max(0.0, mana_input_value - mana_min)
    excess_diff = excess_mana * diff_per_extra_mana
    return float((base_difficulty * _SCALE_FACTOR) + (excess_diff * _SCALE_FACTOR))


def calculate_control_score(character, spell):
    """
    Compute scaled cast skill (v8) per GSL Magic v2.1.

    Source:
      S00218:413-415 - primary magic init, scaled by (skill + 15) * 100
      S00218:425-430 - random factor applied as a percentage multiplier
      S00218:455-505 - full-prep multiplier or partial-prep interpolation
      S00830:68-100 - health and nervous-system modifiers, with empath bypass
      S00830:102-145 - concentration and fatigue modifiers
            S00830:943 - profession penalty inside MANADIFF

        MANADIFF needs one caller-context caveat: GSL's header says v8 is the player's
        skill, but at the point the profession branch runs the operand is functioning on
        the difficulty side of the comparison. The canonical effect is therefore a penalty:
        barbarian/commoner cast with effectively halved skill, thief/trader at 80% skill.

    Returns scaled skill in the range ~0 to ~25,000.
    """
    character_data = _coerce_mapping(character)
    spell_data = _coerce_mapping(spell)
    primary_magic_skill = max(0.0, _coerce_number(character_data.get("primary_magic_skill"), default=0.0))
    pm_bonus = max(0.0, _coerce_number(character_data.get("pm_bonus"), default=0.0))

    scaled_skill = (primary_magic_skill + pm_bonus + _SKILL_BUFFER) * _SCALE_FACTOR
    scaled_skill = (scaled_skill * _random_factor()) / 100.0

    if bool(character_data.get("fully_prepped", True)):
        scaled_skill *= _FULL_PREP_MULTIPLIER
    else:
        prep_time = max(1.0, _coerce_number(spell_data.get("prep_time", spell_data.get("min_prep_time")), default=20.0))
        seconds_waited = max(0.0, _coerce_number(character_data.get("prep_seconds_waited"), default=0.0))
        prep_percent = (11500.0 / (prep_time * 100.0)) * seconds_waited
        scaled_skill = (scaled_skill * prep_percent) / 100.0

    profession = str(character_data.get("profession", "") or "").strip().lower()
    if profession != "empath":
        nervous_injury = max(0.0, _coerce_number(character_data.get("nervous_injury"), default=0.0))
        if nervous_injury > 0.0:
            scaled_skill = (scaled_skill * max(0.0, 100.0 - (nervous_injury * 100.0 / 60.0))) / 100.0

        current_body_hp = max(0.0, _coerce_number(character_data.get("current_body_hp"), default=0.0))
        max_body_hp = max(1.0, _coerce_number(character_data.get("max_body_hp"), default=1.0))
        hp_modifier = 33.0 + ((current_body_hp * 100.0) / max_body_hp)
        scaled_skill = (scaled_skill * hp_modifier) / 100.0

    max_concentration = max(1.0, _coerce_number(character_data.get("max_concentration"), default=1.0))
    current_concentration = _clamp(_coerce_number(character_data.get("current_concentration", max_concentration), default=max_concentration), 0.0, max_concentration)
    scaled_skill = (scaled_skill * ((current_concentration * 100.0) / max_concentration)) / 100.0

    max_fatigue = max(1.0, _coerce_number(character_data.get("max_fatigue"), default=1.0))
    current_fatigue = _clamp(_coerce_number(character_data.get("current_fatigue", max_fatigue), default=max_fatigue), 0.0, max_fatigue)
    scaled_skill = (scaled_skill * ((current_fatigue * 100.0) / max_fatigue)) / 100.0

    # S00830:943, MANADIFF. Caller-context re-read: commoner/barbarian have the
    # worst effective skill, so apply the penalty directly as a skill multiplier.
    multiplier = _PROFESSION_PENALTY_MULTIPLIER.get(profession)
    if multiplier is not None:
        scaled_skill = (scaled_skill * multiplier) / 100.0

    return float(max(0.0, scaled_skill))


def calculate_strain_penalty(attunement_current, attunement_max):
    """
    Preserve the public hook for attunement strain, but return zero for canon math.

    Source: GSL S00218 + S00830 do not apply a separate attunement-strain deduction
    after the core skill build. DireEngine keeps this function for compatibility.
    """
    return 0.0


def calculate_cast_margin(control_score, difficulty, strain_penalty, random_roll):
    """
    Compute the cast contest margin per GSL.

    Source: S00830:178-192 - v7 = v8 - total_difficulty.

    strain_penalty and random_roll are accepted for signature compatibility but ignored.
    Canon randomization is already applied inside calculate_control_score.
    """
    return _coerce_number(control_score) - _coerce_number(difficulty)


def resolve_success_band(cast_margin, control_score=None, difficulty=None, base_difficulty=None):
    """
    Map a cast result to the stable DireEngine success bands using GSL thresholds.

    Source:
      S00830:175-192 - basic failure when skill is below base difficulty * 100
      S00830:479-530 - backlash bands by ratio = (skill * 100) / total_difficulty
    """
    margin = _coerce_number(cast_margin)
    if margin >= 0.0:
        if difficulty is not None and difficulty > 0.0:
            margin_ratio = margin / float(difficulty)
            if margin_ratio >= 1.0:
                return "excellent"
            if margin_ratio >= 0.3:
                return "solid"
        return "partial"

    if control_score is None or difficulty is None:
        return "failure"

    scaled_base_difficulty = _coerce_number(base_difficulty, default=0.0)
    if scaled_base_difficulty > 0.0 and _coerce_number(control_score) < scaled_base_difficulty:
        return "failure"

    return "backlash"


def calculate_backlash_chance(spell, mana_input, cast_margin, effective_env_mana, control_score=None, difficulty=None, base_difficulty=None):
    """
    Return the canonical nerve-damage chance on a backfire.

    Source: S00830:518-528 - nerve chance is max(1, 100 - ratio).
    Returns 0 for successful casts and for basic failures below base difficulty.
    """
    if _coerce_number(cast_margin) >= 0.0:
        return 0.0
    if control_score is None or difficulty is None or difficulty <= 0.0:
        return 0.0
    scaled_base_difficulty = _coerce_number(base_difficulty, default=0.0)
    if scaled_base_difficulty > 0.0 and _coerce_number(control_score) < scaled_base_difficulty:
        return 0.0
    ratio_pct = (_coerce_number(control_score) * 100.0) / _coerce_number(difficulty)
    return float(_clamp(max(1.0, 100.0 - ratio_pct), 0.0, 99.0))


def calculate_backlash_severity(spell, mana_input, cast_margin, control_score=None, difficulty=None, base_difficulty=None):
    """
    Compute backlash severity from the canonical nerve-damage formula.

    Source: S00830:518-528 - nerve damage is (100 - ratio) + 2 on a backfire.
    Maps the canonical damage range into the existing 1-5 severity buckets.
    """
    chance = calculate_backlash_chance(
        spell,
        mana_input,
        cast_margin,
        1.0,
        control_score=control_score,
        difficulty=difficulty,
        base_difficulty=base_difficulty,
    )
    if chance <= 0.0:
        return 1
    nerve_damage = chance + 2.0
    if nerve_damage < 20.0:
        return 1
    if nerve_damage < 40.0:
        return 2
    if nerve_damage < 60.0:
        return 3
    if nerve_damage < 80.0:
        return 4
    return 5


def resolve_backlash_payload(character, severity, spell):
    """
    Compose the backlash payload while preserving DireEngine profession hooks.

    Source:
      S00830:486 - burnout can happen when ratio > 50 on a player
      S00830:518-528 - nervous-system injury scales from 100 - ratio
    """
    character_data = _coerce_mapping(character)
    spell_data = _coerce_mapping(spell)
    severity_value = int(_clamp(_coerce_number(severity, default=1.0), 1.0, 5.0))
    mana_input = max(0.0, _coerce_number(spell_data.get("mana_input"), default=0.0))
    profession = str(character_data.get("profession", "") or "").strip().lower()

    payload = {
        "severity": severity_value,
        "nerve_injury": severity_value * 20,
        "burnout_eligible": severity_value >= 3,
        "attunement_burn_ratio": 0.0,
        "vitality_loss": 0,
        "devotion_loss_ratio": 0.0,
        "shock_gain": 0,
        "focus_penalty_duration": 0,
        "prep_collapse": True,
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