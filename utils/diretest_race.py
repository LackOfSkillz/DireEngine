import time
from collections.abc import Mapping

from evennia.utils.create import create_object

from world.races import TEST_RACES, get_race_display_name


RACE_BASELINE_STATS = {
    "strength": 10,
    "agility": 10,
    "reflex": 10,
    "intelligence": 10,
    "wisdom": 10,
    "stamina": 10,
}

RACE_BASELINE_SKILL = "weapons"
RACE_BALANCE_SAMPLE_WEIGHT = 80.0
RACE_BALANCE_BASE_XP = 100


def _normalize_stats(stats=None):
    values = dict(RACE_BASELINE_STATS)
    if isinstance(stats, Mapping):
        for stat_name in values:
            if stat_name in stats:
                values[stat_name] = int(stats.get(stat_name, values[stat_name]) or values[stat_name])
    return values


def _encumbrance_state_for_ratio(ratio):
    value = float(ratio or 0.0)
    if value < 0.5:
        return "Light"
    if value < 0.8:
        return "Moderate"
    if value < 1.0:
        return "Heavy"
    return "Overloaded"


def _build_learning_projection(character, base_xp=RACE_BALANCE_BASE_XP):
    payload = {}
    for category in ("combat", "survival", "magic", "stealth", "lore"):
        modifier = float(character.get_race_learning_modifier(category=category))
        payload[category] = {
            "modifier": modifier,
            "projected_xp": round(float(base_xp) * modifier, 2),
        }
    return payload


def _build_combat_projection(character, weapon_skill=RACE_BASELINE_SKILL):
    reflex = int(character.get_stat("reflex"))
    agility = int(character.get_stat("agility"))
    skill_rank = int(character.get_skill(weapon_skill)) if hasattr(character, "get_skill") else 0
    return {
        "weapon_skill": weapon_skill,
        "skill_rank": skill_rank,
        "attack_accuracy": int(50 + reflex + agility + skill_rank),
        "evasion": int(reflex + agility + 10),
        "stealth": int(character.get_stealth_total()) if hasattr(character, "get_stealth_total") else 0,
        "perception": int(character.get_perception_total()) if hasattr(character, "get_perception_total") else 0,
    }


def build_race_validation_snapshot(character, sample_weight=RACE_BALANCE_SAMPLE_WEIGHT, base_xp=RACE_BALANCE_BASE_XP, weapon_skill=RACE_BASELINE_SKILL):
    if not character:
        raise ValueError("character is required")

    if hasattr(character, "ensure_core_defaults"):
        character.ensure_core_defaults()

    ok, issues = character.validate_race_application() if hasattr(character, "validate_race_application") else (False, ["Character does not expose race validation."])
    current_weight = float(character.get_total_weight()) if hasattr(character, "get_total_weight") else 0.0
    max_carry_weight = float(character.get_max_carry_weight()) if hasattr(character, "get_max_carry_weight") else 0.0
    projected_weight = current_weight + max(0.0, float(sample_weight or 0.0))
    projected_ratio = (projected_weight / max(1.0, max_carry_weight)) if max_carry_weight > 0 else 0.0

    return {
        "name": getattr(character, "key", None),
        "race": character.get_race() if hasattr(character, "get_race") else None,
        "race_name": character.get_race_display_name() if hasattr(character, "get_race_display_name") else None,
        "profession": character.get_profession() if hasattr(character, "get_profession") else getattr(getattr(character, "db", None), "profession", None),
        "stats": {stat_name: int(character.get_stat(stat_name)) for stat_name in RACE_BASELINE_STATS if hasattr(character, "get_stat")},
        "validation_ok": bool(ok),
        "validation_issues": list(issues or []),
        "carry_modifier": float(character.get_race_carry_modifier()) if hasattr(character, "get_race_carry_modifier") else 1.0,
        "max_carry_weight": max_carry_weight,
        "current_weight": current_weight,
        "current_encumbrance_ratio": float(character.get_encumbrance_ratio()) if hasattr(character, "get_encumbrance_ratio") else 0.0,
        "current_encumbrance_state": character.get_encumbrance_state() if hasattr(character, "get_encumbrance_state") else None,
        "projected_weight": projected_weight,
        "projected_encumbrance_ratio": projected_ratio,
        "projected_encumbrance_state": _encumbrance_state_for_ratio(projected_ratio),
        "learning": _build_learning_projection(character, base_xp=base_xp),
        "combat": _build_combat_projection(character, weapon_skill=weapon_skill),
    }


def assert_race_consistency(character):
    snapshot = build_race_validation_snapshot(character, sample_weight=0.0)
    if snapshot["validation_ok"]:
        return snapshot
    issues = "; ".join(snapshot["validation_issues"]) or "unknown race validation failure"
    raise AssertionError(f"Race consistency invariant failed for {snapshot['name']}: {issues}")


def create_race_test_character(room, race_key, profession="commoner", stats=None, key=None):
    if room is None:
        raise ValueError("room is required")

    normalized_stats = _normalize_stats(stats)
    suffix = str(int(time.time() * 1000))[-6:]
    character_key = key or f"diretest_{race_key}_{suffix}"
    character = create_object("typeclasses.characters.Character", key=character_key, location=room, home=room)
    character.ensure_core_defaults()
    character.db.profession = profession
    character.db.stats = dict(normalized_stats)
    character.set_race(race_key, sync=False, emit_messages=False)
    character.sync_client_state()
    return character


def build_cross_race_balance_report(room, profession="commoner", stats=None, sample_weight=RACE_BALANCE_SAMPLE_WEIGHT, base_xp=RACE_BALANCE_BASE_XP, weapon_skill=RACE_BASELINE_SKILL, cleanup=True):
    created = []
    try:
        for race_key in TEST_RACES:
            created.append(create_race_test_character(room, race_key, profession=profession, stats=stats))
        return [
            build_race_validation_snapshot(character, sample_weight=sample_weight, base_xp=base_xp, weapon_skill=weapon_skill)
            for character in created
        ]
    finally:
        if cleanup:
            for character in created:
                try:
                    character.delete()
                except Exception:
                    pass


def format_cross_race_balance_report(rows):
    lines = []
    for row in rows:
        combat = dict(row.get("combat") or {})
        lines.append(
            " | ".join(
                [
                    f"{row.get('race_name') or get_race_display_name(row.get('race'))}",
                    f"carry={float(row.get('max_carry_weight', 0.0)):.1f}",
                    f"enc={float(row.get('projected_encumbrance_ratio', 0.0)):.2f} ({row.get('projected_encumbrance_state')})",
                    f"combat_xp={float(((row.get('learning') or {}).get('combat') or {}).get('projected_xp', 0.0)):.2f}",
                    f"acc={int(combat.get('attack_accuracy', 0) or 0)}",
                    f"eva={int(combat.get('evasion', 0) or 0)}",
                    f"valid={'ok' if row.get('validation_ok') else 'fail'}",
                ]
            )
        )
    return lines


def build_race_impact_log(rows):
    entries = []
    for row in rows:
        learning = dict(row.get("learning") or {})
        combat = dict(row.get("combat") or {})
        projected_xp = {
            category: float((payload or {}).get("projected_xp", 0.0) or 0.0)
            for category, payload in learning.items()
        }
        combat_effectiveness = {
            "attack_accuracy": int(combat.get("attack_accuracy", 0) or 0),
            "evasion": int(combat.get("evasion", 0) or 0),
            "stealth": int(combat.get("stealth", 0) or 0),
            "perception": int(combat.get("perception", 0) or 0),
        }
        entries.append(
            {
                "race": row.get("race"),
                "race_name": row.get("race_name") or get_race_display_name(row.get("race")),
                "encumbrance_ratio": round(float(row.get("projected_encumbrance_ratio", 0.0) or 0.0), 4),
                "xp_rate": projected_xp,
                "combat_effectiveness": combat_effectiveness,
            }
        )
    return entries