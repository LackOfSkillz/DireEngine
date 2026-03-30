from collections.abc import Mapping

from .definitions import (
    BASE_CARRY_WEIGHT,
    DEFAULT_RACE,
    RACE_ALIASES,
    RACE_DEFINITIONS,
    RACE_LEARNING_CATEGORIES,
    RACE_STATS,
)


LEARNING_CATEGORY_ALIASES = {
    "armor": "combat",
}


def _normalize(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_") or None


def normalize_learning_category(category):
    normalized = _normalize(category)
    if not normalized:
        return None
    normalized = LEARNING_CATEGORY_ALIASES.get(normalized, normalized)
    if normalized in RACE_LEARNING_CATEGORIES:
        return normalized
    return None


def resolve_race_name(race_name, default=DEFAULT_RACE):
    normalized = _normalize(race_name)
    if not normalized:
        return default
    normalized = RACE_ALIASES.get(normalized, normalized)
    if normalized in RACE_DEFINITIONS:
        return normalized
    return default


def get_race_profile(race_name):
    race_key = resolve_race_name(race_name)
    profile = dict(RACE_DEFINITIONS.get(race_key, RACE_DEFINITIONS[DEFAULT_RACE]))
    profile["stat_modifiers"] = dict(profile.get("stat_modifiers", {}))
    profile["stat_caps"] = dict(profile.get("stat_caps", {}))
    profile["learning_modifiers"] = dict(profile.get("learning_modifiers", {}))
    profile["key"] = race_key
    profile["race"] = race_key
    return profile


def get_race_display_name(race_name):
    return get_race_profile(race_name).get("name", "Human")


def get_race_description(race_name):
    return get_race_profile(race_name).get("description", "")


def get_race_stat_modifier(race_name, stat):
    normalized_stat = _normalize(stat)
    if normalized_stat not in RACE_STATS:
        return 0
    return int(get_race_profile(race_name).get("stat_modifiers", {}).get(normalized_stat, 0) or 0)


def get_race_stat_cap(race_name, stat):
    normalized_stat = _normalize(stat)
    if normalized_stat not in RACE_STATS:
        return None
    return int(get_race_profile(race_name).get("stat_caps", {}).get(normalized_stat, 100) or 100)


def get_race_learning_modifier(race_name, category):
    normalized_category = normalize_learning_category(category)
    if not normalized_category:
        return 1.0
    return float(get_race_profile(race_name).get("learning_modifiers", {}).get(normalized_category, 1.0) or 1.0)


def get_race_carry_modifier(race_name):
    return float(get_race_profile(race_name).get("carry_modifier", 1.0) or 1.0)


def get_race_size(race_name):
    return str(get_race_profile(race_name).get("size", "medium") or "medium").strip().lower()


def get_race_base_carry_weight(race_name):
    return float(BASE_CARRY_WEIGHT) * get_race_carry_modifier(race_name)


def apply_race_modifiers_to_stats(base_stats, race_name, minimum=5, maximum=20):
    stats = dict(base_stats or {})
    profile = get_race_profile(race_name)
    for stat in RACE_STATS:
        base_value = int(stats.get(stat, 10) or 10)
        modified = base_value + int(profile["stat_modifiers"].get(stat, 0) or 0)
        stats[stat] = max(int(minimum), min(int(maximum), modified))
    return stats


def get_race_debug_payload(race_name):
    profile = get_race_profile(race_name)
    return {
        "race": profile["key"],
        "name": profile["name"],
        "size": profile["size"],
        "carry_modifier": float(profile["carry_modifier"]),
        "base_carry_weight": get_race_base_carry_weight(profile["key"]),
        "stat_modifiers": dict(profile["stat_modifiers"]),
        "stat_caps": dict(profile["stat_caps"]),
        "learning_modifiers": dict(profile["learning_modifiers"]),
    }


TEST_RACES = tuple(RACE_DEFINITIONS.keys())


def validate_race_application(character):
    if not character:
        return False, ["No character provided."]

    race_key = resolve_race_name(getattr(getattr(character, "db", None), "race", None), default=None)
    if not race_key:
        return False, ["Character has no canonical race set."]

    profile = get_race_profile(race_key)
    issues = []

    if dict(getattr(character.db, "stat_caps", {}) or {}) != dict(profile["stat_caps"]):
        issues.append("Character stat caps do not match the canonical race definition.")
    if dict(getattr(character.db, "learning_modifiers", {}) or {}) != dict(profile["learning_modifiers"]):
        issues.append("Character learning modifiers do not match the canonical race definition.")
    if str(getattr(character.db, "size", "") or "").strip().lower() != profile["size"]:
        issues.append("Character size does not match the canonical race definition.")
    if abs(float(getattr(character.db, "carry_modifier", 1.0) or 1.0) - float(profile["carry_modifier"])) > 0.0001:
        issues.append("Character carry modifier does not match the canonical race definition.")

    stats = dict(getattr(character.db, "stats", {}) or {}) if isinstance(getattr(character.db, "stats", {}), Mapping) else {}
    for stat in RACE_STATS:
        current_value = int(stats.get(stat, 10) or 10)
        cap = int(profile["stat_caps"].get(stat, 100) or 100)
        if current_value > cap:
            issues.append(f"{stat} exceeds the racial cap ({current_value} > {cap}).")

    return (not issues), issues