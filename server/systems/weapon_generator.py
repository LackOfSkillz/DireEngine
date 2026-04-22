from __future__ import annotations

import random
from pathlib import Path

import yaml


WEAPON_LAYER_ROOT = Path(__file__).resolve().parents[2] / "world_data" / "weapon_gen" / "layers"
MATERIAL_LAYER_FILES = (
    "materials_metals.yaml",
    "materials_woods.yaml",
    "materials_organic.yaml",
    "materials_stone.yaml",
    "materials_alloys.yaml",
)
EMBELLISHMENT_WEIGHTS = {
    "none": 0.65,
    "engraved": 0.15,
    "gem_inlaid": 0.1,
    "wrapped": 0.1,
}
TIER_ORDER = {"low": 1, "mid": 2, "high": 3, "legendary": 4}
TIER_LEVEL_BANDS = {
    "low": {"min": 1, "max": 3},
    "mid": {"min": 3, "max": 6},
    "high": {"min": 6, "max": 10},
    "legendary": {"min": 10, "max": 20},
}
TIER_ALLOWED_MATERIAL_TIERS = {
    "low": {"common"},
    "mid": {"common", "uncommon"},
    "high": {"common", "uncommon", "rare"},
    "legendary": {"common", "uncommon", "rare", "exotic"},
}
TRAIT_LIMITS = {
    "low": 1,
    "mid": 2,
    "high": 3,
    "legendary": 4,
}
WEAPON_USAGE_TAG_BIASES = {
    "bow": {
        "preferred": {"flexible": 3.0, "ideal_for_bows": 4.0, "lightweight": 1.5, "elastic": 2.5},
        "discouraged": {"heavy": -2.5, "dense": -1.0, "brittle": -1.0},
    },
    "crossbow": {
        "preferred": {"dense": 2.0, "rigid": 2.5, "resilient": 1.5},
        "discouraged": {"soft": -1.0},
    },
    "mace": {
        "preferred": {"heavy": 3.0, "dense": 3.0, "durable": 1.5, "massive": 1.0},
        "discouraged": {"light": -1.5, "brittle": -1.0},
    },
    "sword": {
        "preferred": {"balanced": 2.5, "refined": 1.5, "sharp": 1.5},
        "discouraged": {"crude": -1.0},
    },
    "dagger": {
        "preferred": {"fine": 2.0, "keen": 2.0, "reflective": 1.0, "sharp": 2.5, "light": 1.0},
        "discouraged": {"massive": -2.0, "heavy": -1.5},
    },
    "spear": {
        "preferred": {"flexible": 1.5, "balanced": 2.0, "sharp": 1.5, "lightweight": 1.0},
        "discouraged": {"brittle": -1.0},
    },
}
WEAPON_MATERIAL_SLOTS = {
    "dagger": ("blade", "grip"),
    "sword": ("blade", "grip"),
    "mace": ("blade", "grip"),
    "spear": ("blade", "shaft"),
    "bow": ("shaft", "grip"),
    "crossbow": ("shaft", "grip"),
}
WEAPON_CLASS_BY_TYPE = {
    "dagger": "light_edge",
    "sword": "medium_edge",
    "mace": "heavy_blunt",
    "spear": "polearm",
    "bow": "long_bow",
    "crossbow": "crossbow",
}
BLAND_NAME_STYLES = {
    "brutal",
    "faded",
    "heavy",
    "layered",
    "organic",
    "polished",
    "precise",
    "reliable",
    "seamless",
    "sturdy",
    "weathered",
}
VISUAL_TRAITS = {
    "clean",
    "curved",
    "dulled",
    "etched",
    "faded",
    "flowing",
    "lacquered",
    "ornate",
    "polished",
    "rune-etched",
    "scarred",
    "seamless",
    "weathered",
}
FEEL_TRAITS = {
    "balanced",
    "brutal",
    "efficient",
    "graceful",
    "heavy",
    "organic",
    "precise",
    "practical",
    "reliable",
    "resilient",
    "solid",
    "spare",
    "sturdy",
}
LOW_TIER_AGE_WORDS = {"new", "worn", "ancient"}
LEGENDARY_TITLE_WORDS = {
    "balanced": "Still",
    "curved": "Hook",
    "graceful": "Whisper",
    "lacquered": "Gleam",
    "ornate": "Crown",
    "practical": "Trail",
    "precise": "Needle",
    "reliable": "Ward",
    "spare": "Lean",
    "sturdy": "Stone",
    "weathered": "Ash",
}
TRAIT_PRIORITY = {
    "curved": 4,
    "graceful": 5,
    "lacquered": 3,
    "ornate": 4,
    "precise": 2,
    "severe": 3,
    "sleek": 4,
    "sturdy": 1,
}
BASE_WEAPON_PROFILES = {
    "dagger": {
        "base_name": "dagger",
        "key_template": "training dagger",
        "weapon_profile": {"type": "light_edge", "skill": "light_edge", "damage": 4, "balance": 60, "speed": 2.0, "damage_min": 2, "damage_max": 5, "roundtime": 2.0},
        "weapon_type": "light_edge",
        "balance_cost": 8,
        "fatigue_cost": 4,
        "damage_type": "slice",
        "damage_types": {"slice": 0.6, "impact": 0.1, "puncture": 0.3},
        "balance": 60,
        "damage": 4,
        "speed": 2.0,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "skill_scaling": {
            "light_edge": [
                {"rank": 10, "effects": {"balance": 5}},
                {"rank": 30, "effects": {"accuracy": 3}},
                {"rank": 60, "effects": {"flavor": "blade_flourish"}},
            ]
        },
    },
    "sword": {
        "base_name": "sword",
        "key_template": "training sword",
        "weapon_profile": {"type": "light_edge", "skill": "light_edge", "damage": 5, "balance": 55, "speed": 3.0, "damage_min": 3, "damage_max": 6, "roundtime": 3.0},
        "weapon_type": "light_edge",
        "balance_cost": 10,
        "fatigue_cost": 5,
        "damage_type": "slice",
        "damage_types": {"slice": 0.7, "impact": 0.1, "puncture": 0.2},
        "balance": 55,
        "damage": 5,
        "speed": 3.0,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "skill_scaling": {
            "light_edge": [
                {"rank": 10, "effects": {"balance": 5}},
                {"rank": 30, "effects": {"accuracy": 3}},
                {"rank": 60, "effects": {"flavor": "blade_flourish"}},
            ]
        },
    },
    "mace": {
        "base_name": "mace",
        "key_template": "training mace",
        "weapon_profile": {"type": "blunt", "skill": "blunt", "damage": 6, "balance": 45, "speed": 4.0, "damage_min": 4, "damage_max": 8, "roundtime": 4.0},
        "weapon_type": "blunt",
        "balance_cost": 14,
        "fatigue_cost": 7,
        "damage_type": "impact",
        "damage_types": {"slice": 0.0, "impact": 0.9, "puncture": 0.1},
        "balance": 45,
        "damage": 6,
        "speed": 4.0,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "skill_scaling": {
            "blunt": [
                {"rank": 10, "effects": {"balance": 4}},
                {"rank": 30, "effects": {"accuracy": 2}},
                {"rank": 60, "effects": {"flavor": "blade_flourish"}},
            ]
        },
    },
    "spear": {
        "base_name": "spear",
        "key_template": "training spear",
        "weapon_profile": {"type": "polearm", "skill": "polearm", "damage": 5, "balance": 52, "speed": 4.0, "damage_min": 3, "damage_max": 7, "roundtime": 4.0},
        "weapon_type": "polearm",
        "balance_cost": 12,
        "fatigue_cost": 6,
        "damage_type": "puncture",
        "damage_types": {"slice": 0.1, "impact": 0.1, "puncture": 0.8},
        "balance": 52,
        "damage": 5,
        "speed": 4.0,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "skill_scaling": {
            "polearm": [
                {"rank": 10, "effects": {"balance": 4}},
                {"rank": 30, "effects": {"accuracy": 3}},
                {"rank": 60, "effects": {"flavor": "blade_flourish"}},
            ]
        },
    },
    "bow": {
        "base_name": "bow",
        "key_template": "training bow",
        "weapon_profile": {"type": "attack", "skill": "attack", "damage": 5, "balance": 50, "speed": 4.0, "damage_min": 3, "damage_max": 7, "roundtime": 4.0, "range_band": "far", "weapon_range_type": "bow"},
        "weapon_type": "attack",
        "balance_cost": 10,
        "fatigue_cost": 5,
        "damage_type": "puncture",
        "damage_types": {"slice": 0.0, "impact": 0.1, "puncture": 0.9},
        "balance": 50,
        "damage": 5,
        "speed": 4.0,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "is_ranged": True,
        "weapon_range_type": "bow",
        "range_band": "far",
        "skill_scaling": {
            "attack": [
                {"rank": 10, "effects": {"balance": 4}},
                {"rank": 30, "effects": {"accuracy": 3}},
                {"rank": 60, "effects": {"flavor": "archers_focus"}},
            ]
        },
    },
    "crossbow": {
        "base_name": "crossbow",
        "key_template": "training crossbow",
        "weapon_profile": {"type": "attack", "skill": "attack", "damage": 6, "balance": 45, "speed": 4.5, "damage_min": 4, "damage_max": 8, "roundtime": 4.5, "range_band": "far", "weapon_range_type": "crossbow"},
        "weapon_type": "attack",
        "balance_cost": 12,
        "fatigue_cost": 5,
        "damage_type": "puncture",
        "damage_types": {"slice": 0.0, "impact": 0.05, "puncture": 0.95},
        "balance": 45,
        "damage": 6,
        "speed": 4.5,
        "unlocks": {20: {"damage_bonus": 2}, 40: {"flavor": True}},
        "is_ranged": True,
        "weapon_range_type": "crossbow",
        "range_band": "far",
        "skill_scaling": {
            "attack": [
                {"rank": 10, "effects": {"balance": 3}},
                {"rank": 30, "effects": {"accuracy": 4}},
                {"rank": 60, "effects": {"flavor": "archers_focus"}},
            ]
        },
    },
}


def _load_yaml_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle) or {}


def load_cultures() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "cultures.yaml"))


def load_construction_methods() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "construction_methods.yaml"))


def load_function_styles() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "function_styles.yaml"))


def load_age_profiles() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "age_profiles.yaml"))


def load_embellishments() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "embellishments.yaml"))


def load_material_categories() -> dict[str, list[str]]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "material_categories.yaml"))


def load_trait_families() -> dict[str, list[str]]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "trait_families.yaml"))


def load_trait_conflicts() -> dict[str, list[list[str]]]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "trait_conflicts.yaml"))


def load_trait_phrases() -> dict[str, str]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "trait_phrases.yaml"))


def load_description_voices() -> dict[str, dict]:
    return dict(_load_yaml_file(WEAPON_LAYER_ROOT / "description_voices.yaml"))


def load_materials() -> dict[str, dict]:
    materials = {}
    for filename in MATERIAL_LAYER_FILES:
        materials.update(_load_yaml_file(WEAPON_LAYER_ROOT / filename))
    return materials


def _slugify(value: str) -> str:
    lowered = str(value or "").strip().lower()
    safe = []
    for char in lowered:
        if char.isalnum():
            safe.append(char)
        else:
            safe.append("_")
    return "_".join(filter(None, "".join(safe).split("_")))


def _display_name(value: str) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").strip()


def _with_article(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def _natural_join(parts: list[str]) -> str:
    items = [str(part or "").strip() for part in parts if str(part or "").strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _slot_label(weapon_type: str, slot_name: str) -> str:
    if slot_name == "blade":
        if weapon_type == "mace":
            return "head"
        if weapon_type == "spear":
            return "spearhead"
        return "blade"
    if slot_name == "shaft":
        if weapon_type == "bow":
            return "stave"
        if weapon_type == "crossbow":
            return "stock"
        return "shaft"
    return slot_name


def _material_slot_phrase(weapon_type: str, slot_name: str, material: dict) -> str:
    material_name = _material_display_name(material)
    return _with_article(f"{material_name} {_slot_label(weapon_type, slot_name)}")


def _primary_material_slot(weapon_type: str, materials: dict[str, dict]) -> str:
    for slot_name in ("blade", "shaft", "grip"):
        if slot_name in materials and slot_name in WEAPON_MATERIAL_SLOTS.get(weapon_type, ()):
            return slot_name
    return next(iter(materials), "")


def _secondary_material_slot(weapon_type: str, materials: dict[str, dict]) -> str:
    primary_slot = _primary_material_slot(weapon_type, materials)
    for slot_name in WEAPON_MATERIAL_SLOTS.get(weapon_type, ()):
        if slot_name != primary_slot and slot_name in materials:
            return slot_name
    return primary_slot


def _describe_materials(weapon_type: str, materials: dict[str, dict]) -> str:
    slot_phrases = [
        _material_slot_phrase(weapon_type, slot_name, materials[slot_name])
        for slot_name in WEAPON_MATERIAL_SLOTS.get(weapon_type, ())
        if slot_name in materials
    ]
    return _natural_join(slot_phrases)


def _trait_family_map() -> dict[str, str]:
    families = load_trait_families()
    mapping = {}
    for family_name, trait_names in families.items():
        family = _display_name(family_name).lower()
        for trait_name in trait_names or []:
            label = _display_name(trait_name).lower()
            if label:
                mapping[label] = family
    return mapping


def _resolve_trait_conflicts(traits: list[str], *, tier: str = "mid", rng=None) -> list[str]:
    del rng
    resolved = []
    seen = set()
    for trait in traits:
        label = _display_name(trait).lower()
        if label and label not in seen:
            resolved.append(label)
            seen.add(label)

    conflict_config = load_trait_conflicts()
    hard_conflicts = [
        {_display_name(member).lower() for member in pair or [] if _display_name(member).strip()}
        for pair in conflict_config.get("hard_conflicts") or []
    ]
    soft_conflicts = [
        {_display_name(member).lower() for member in pair or [] if _display_name(member).strip()}
        for pair in conflict_config.get("soft_conflicts") or []
    ]

    filtered = []
    for trait in resolved:
        if any(trait in pair and any(existing in pair and existing != trait for existing in filtered) for pair in hard_conflicts):
            continue
        filtered.append(trait)

    if tier in {"low", "mid"}:
        softened = []
        for trait in filtered:
            if any(trait in pair and any(existing in pair and existing != trait for existing in softened) for pair in soft_conflicts):
                continue
            softened.append(trait)
        filtered = softened

    family_map = _trait_family_map()
    if tier == "low":
        family_seen = set()
        family_filtered = []
        for trait in filtered:
            family = family_map.get(trait)
            if family and family in family_seen:
                continue
            family_filtered.append(trait)
            if family:
                family_seen.add(family)
        filtered = family_filtered

    return filtered


def _ordered_traits(style_stack: dict, traits: list[str]) -> list[str]:
    primary_trait = _display_name(style_stack.get("primary_trait") or "").lower()
    ordered = []
    if primary_trait and primary_trait in traits:
        ordered.append(primary_trait)
    for trait in traits:
        label = _display_name(trait).lower()
        if label and label not in ordered:
            ordered.append(label)
    return ordered


def _trait_to_phrase(trait: str) -> str:
    phrases = load_trait_phrases()
    label = _display_name(trait).lower()
    phrase = phrases.get(label)
    if phrase:
        return str(phrase).strip()
    return label


def _select_voice(tier: str, voices: dict[str, dict], rng) -> tuple[str, str]:
    if tier == "legendary":
        preferred = ["mythic", "historical", "observational"]
    elif tier == "high":
        preferred = ["historical", "observational"]
    else:
        preferred = ["functional", "observational"]

    available = []
    for voice_name in preferred:
        openers = list((voices.get(voice_name) or {}).get("openers") or [])
        if openers:
            available.append((voice_name, openers))
    if not available:
        return "functional", "This weapon is built around"
    voice_name, openers = rng.choice(available)
    return voice_name, str(rng.choice(openers)).strip()


def _select_name_style(style_stack: dict, traits: list[str]) -> str:
    options = []
    primary_trait = _display_name(style_stack.get("primary_trait") or "").lower()
    if primary_trait:
        options.append(primary_trait)
    for value in (style_stack.get("primary_style"), style_stack.get("secondary_style")):
        label = _display_name(value).lower()
        if label:
            options.append(label)
    for trait in traits:
        label = _display_name(trait).lower()
        if label and label not in options:
            options.append(label)
    ranked = [option for option in options if option and option not in BLAND_NAME_STYLES]
    if not ranked:
        return ""
    ranked.sort(key=lambda option: (TRAIT_PRIORITY.get(option, 0), option), reverse=True)
    return ranked[0]


def _build_legendary_sobriquet(weapon_type: str, style_stack: dict, traits: list[str], materials: dict[str, dict]) -> str:
    suffix_map = {
        "bow": "song",
        "crossbow": "lock",
        "dagger": "fang",
        "mace": "maul",
        "spear": "thorn",
        "sword": "edge",
    }
    style_label = _select_name_style(style_stack, traits).lower()
    material = materials.get(_primary_material_slot(weapon_type, materials), {})
    material_root = _material_display_name(material).split()[0].title() if material else ""
    prefix = LEGENDARY_TITLE_WORDS.get(style_label, material_root or "Bright")
    suffix = suffix_map.get(weapon_type, "blade")
    return f"{prefix}{suffix}".title()


def _build_name_expression(weapon_type: str, tier: str, style_stack: dict, materials: dict[str, dict], traits: list[str]) -> str:
    primary_slot = _primary_material_slot(weapon_type, materials)
    secondary_slot = _secondary_material_slot(weapon_type, materials)
    primary_material = _material_display_name(materials.get(primary_slot, {})).title()
    secondary_material = _material_display_name(materials.get(secondary_slot, {})).lower()
    age = _display_name(style_stack.get("age") or "worn").title()
    culture = _display_name(style_stack["primary_culture"]).title()
    secondary_culture = _display_name(style_stack.get("secondary_culture") or "").title()
    style_trait = _select_name_style(style_stack, traits).title()
    weapon = _display_name(weapon_type).title()

    if tier == "low":
        age_part = age if age.lower() in LOW_TIER_AGE_WORDS else ""
        return " ".join(part for part in (age_part, primary_material, weapon) if part)
    if tier == "mid":
        return " ".join(part for part in (style_trait, primary_material, weapon) if part)
    if tier == "high":
        return " ".join(part for part in (style_trait, primary_material, weapon, "of the", culture) if part)

    sobriquet = _build_legendary_sobriquet(weapon_type, style_stack, traits, materials)
    base_name = " ".join(part for part in (style_trait, primary_material, weapon, "of the", culture) if part)
    if secondary_culture and secondary_material:
        secondary_label = _slot_label(weapon_type, secondary_slot)
        return f"{sobriquet}, a {base_name}, reinforced with {secondary_material} {secondary_label} work in the manner of the {secondary_culture}"
    return f"{sobriquet}, a {base_name}"


def _build_construction_sentence(weapon_type: str, style_stack: dict, materials: dict[str, dict]) -> str:
    voice_name = str(style_stack.get("description_voice") or "functional")
    voice_opener = str(style_stack.get("description_voice_opener") or "This weapon is built around")
    construction = _display_name(style_stack["construction"])
    primary_slot = _primary_material_slot(weapon_type, materials)
    secondary_slot = _secondary_material_slot(weapon_type, materials)
    primary_phrase = _material_slot_phrase(weapon_type, primary_slot, materials[primary_slot])
    secondary_phrase = _material_slot_phrase(weapon_type, secondary_slot, materials[secondary_slot])
    if voice_name == "observational":
        return f"{voice_opener} {primary_phrase} paired with {secondary_phrase}."
    if voice_name == "historical":
        return f"{voice_opener} the {construction.lower()} tradition, this weapon pairs {primary_phrase} with {secondary_phrase}."
    if voice_name == "mythic":
        return f"{voice_opener} this weapon was shaped from {primary_phrase} and {secondary_phrase}."
    return f"{voice_opener} {primary_phrase} and finished with {secondary_phrase}."


def _build_trait_sentence(weapon_type: str, style_stack: dict, materials: dict[str, dict], traits: list[str]) -> str:
    del weapon_type, materials
    phrases = []
    for trait in _ordered_traits(style_stack, traits):
        phrase = _trait_to_phrase(trait)
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    if not phrases:
        return ""
    return f"It is {_natural_join(phrases)}."


def _build_culture_sentence(style_stack: dict) -> str:
    primary_culture = _display_name(style_stack["primary_culture"])
    if not primary_culture:
        return ""
    return f"It reflects the style of the {primary_culture}."


def _build_secondary_culture_sentence(style_stack: dict) -> str:
    secondary_culture = _display_name(style_stack.get("secondary_culture") or "")
    if not secondary_culture:
        return ""
    return f"It shows influence from the {secondary_culture}."


def _build_expression_description(weapon_type: str, style_stack: dict, materials: dict[str, dict], traits: list[str]) -> str:
    parts = [
        _build_construction_sentence(weapon_type, style_stack, materials),
        _build_trait_sentence(weapon_type, style_stack, materials, traits),
        _build_culture_sentence(style_stack),
        _build_secondary_culture_sentence(style_stack),
        _embellishment_sentence(style_stack.get("embellishment")),
    ]
    return " ".join(part for part in parts if part)


def _embellishment_sentence(embellishment: str) -> str:
    normalized = str(embellishment or "").strip().lower()
    if normalized in {"", "none"}:
        return ""
    if normalized == "engraved":
        return "Engraved details catch the light along the surface."
    if normalized == "gem_inlaid":
        return "Small inlays break up the surface with flashes of color."
    if normalized == "wrapped":
        return "The grip is bound for a surer hold."
    return f"Its finish carries {_display_name(normalized).lower()} work."


def _weighted_choice(options: list[str], weights: list[float], rng) -> str:
    return rng.choices(options, weights=weights, k=1)[0]


def _get_materials_by_category() -> dict[str, list[dict]]:
    categories = load_material_categories()
    materials = load_materials()
    grouped = {key: [] for key in categories}
    for material_id, raw_material in materials.items():
        material = dict(raw_material or {})
        material["id"] = material_id
        material_category = str(material.get("category") or "").strip().lower()
        material.setdefault("tier", "common")
        material.setdefault("tags", [])
        for category, allowed_categories in categories.items():
            if material_category in set(allowed_categories or []):
                grouped.setdefault(category, []).append(material)
    return grouped


def _material_display_name(material: dict) -> str:
    return _display_name(material.get("id") or "")


def _material_matches_tier(material: dict, tier: str) -> bool:
    return str(material.get("tier") or "common").strip().lower() in TIER_ALLOWED_MATERIAL_TIERS[tier]


def _material_weight_for_usage(weapon_type: str, slot_name: str, material: dict) -> float:
    tags = {str(tag or "").strip().lower() for tag in material.get("tags") or []}
    bias = WEAPON_USAGE_TAG_BIASES.get(weapon_type, {})
    weight = 1.0
    for tag, bonus in bias.get("preferred", {}).items():
        if tag in tags:
            weight += bonus
    for tag, penalty in bias.get("discouraged", {}).items():
        if tag in tags:
            weight += penalty
    material_category = str(material.get("category") or "").strip().lower()
    if weapon_type in {"bow", "crossbow"} and slot_name == "shaft" and material_category == "wood":
        weight += 2.0
    if weapon_type in {"mace", "sword"} and slot_name == "blade" and material_category in {"metal", "alloy"}:
        weight += 1.5
    if weapon_type == "dagger" and slot_name == "blade" and str(material.get("tier") or "").strip().lower() in {"rare", "exotic"}:
        weight += 1.5
    return max(0.1, weight)


def _base_profile_for(weapon_type: str) -> dict:
    normalized = str(weapon_type or "").strip().lower()
    if normalized not in BASE_WEAPON_PROFILES:
        options = ", ".join(sorted(BASE_WEAPON_PROFILES))
        raise ValueError(f"Unknown weapon type '{normalized}'. Choose one of: {options}")
    profile = dict(BASE_WEAPON_PROFILES[normalized])
    profile["weapon_profile"] = dict(profile["weapon_profile"])
    profile["damage_types"] = dict(profile["damage_types"])
    profile["skill_scaling"] = dict(profile["skill_scaling"])
    profile["unlocks"] = dict(profile["unlocks"])
    return profile


def _clamp_tier(tier: str) -> str:
    normalized = str(tier or "low").strip().lower()
    if normalized not in TIER_ORDER:
        raise ValueError("tier must be low, mid, high, or legendary")
    return normalized


def _select_embellishment(embellishments: dict[str, dict], primary_culture: dict, rng) -> str:
    options = list(embellishments)
    weights = []
    favored = set(primary_culture.get("embellishments") or [])
    for option in options:
        weight = EMBELLISHMENT_WEIGHTS.get(option, 0.05)
        if option in favored:
            weight += 0.15
        weights.append(weight)
    return _weighted_choice(options, weights, rng)


def _apply_trait_compatibility(weapon_type: str, traits: list[str]) -> list[str]:
    filtered = list(traits)
    if weapon_type == "bow":
        filtered = [trait for trait in filtered if trait not in {"heavy", "brutal"}]
    if weapon_type == "dagger":
        filtered = [trait for trait in filtered if trait != "massive"]
    return filtered


def _pick_style(values: list[str], rng) -> str | None:
    options = [str(value or "").strip() for value in values or [] if str(value or "").strip()]
    if not options:
        return None
    return rng.choice(options)


def _build_description(weapon_type: str, style_stack: dict, materials: dict[str, dict], traits: list[str]) -> str:
    return _build_expression_description(weapon_type, style_stack, materials, traits)


def _build_name(weapon_type: str, tier: str, style_stack: dict, materials: dict[str, dict], traits: list[str]) -> str:
    return _build_name_expression(weapon_type, tier, style_stack, materials, traits)


def generate_weapon_definition(weapon_type: str, *, tier: str = "low", rng=None) -> dict:
    rng = rng or random.Random()
    resolved_tier = _clamp_tier(tier)
    profile = _base_profile_for(weapon_type)
    cultures = load_cultures()
    construction_methods = load_construction_methods()
    function_styles = load_function_styles()
    age_profiles = load_age_profiles()
    embellishments = load_embellishments()
    description_voices = load_description_voices()
    materials_by_category = _get_materials_by_category()

    style_stack = {}
    culture_keys = sorted(cultures)
    primary_culture = rng.choice(culture_keys)
    secondary_culture = None
    if resolved_tier != "low" and len(culture_keys) > 1 and rng.random() < 0.3:
        secondary_options = [culture for culture in culture_keys if culture != primary_culture]
        secondary_culture = rng.choice(secondary_options)

    construction = rng.choice(sorted(construction_methods))
    function_style = rng.choice(sorted(function_styles))
    age = rng.choice(sorted(age_profiles))
    embellishment = "none" if resolved_tier == "low" else _select_embellishment(embellishments, cultures[primary_culture], rng)

    style_stack["primary_culture"] = primary_culture
    style_stack["secondary_culture"] = secondary_culture
    style_stack["construction"] = construction
    style_stack["function_style"] = function_style
    style_stack["age"] = age
    style_stack["embellishment"] = embellishment
    style_stack["primary_style"] = _pick_style(cultures[primary_culture].get("primary_styles") or [], rng)
    style_stack["secondary_style"] = _pick_style(cultures[primary_culture].get("secondary_styles") or [], rng)
    style_stack["secondary_culture_style"] = _pick_style(cultures.get(secondary_culture, {}).get("primary_styles") or [], rng) if secondary_culture else None
    description_voice, description_voice_opener = _select_voice(resolved_tier, description_voices, rng)
    style_stack["description_voice"] = description_voice
    style_stack["description_voice_opener"] = description_voice_opener

    preferred_primary_materials = set(cultures[primary_culture].get("materials") or [])
    preferred_secondary_materials = set(cultures.get(secondary_culture, {}).get("materials") or []) if secondary_culture else set()

    def select_material(category):
        candidates = [candidate for candidate in materials_by_category[category] if _material_matches_tier(candidate, resolved_tier)]
        if not candidates:
            candidates = list(materials_by_category[category])
        weights = []
        for candidate in candidates:
            weight = 1.0
            if candidate["id"] in preferred_primary_materials:
                weight += 2.0
            if candidate["id"] in preferred_secondary_materials:
                weight += 1.0
            weight += _material_weight_for_usage(weapon_type, category, candidate) - 1.0
            weights.append(weight)
        return rng.choices(candidates, weights=weights, k=1)[0]

    assigned_materials = {}
    for slot_name in WEAPON_MATERIAL_SLOTS.get(weapon_type, ()):  # pragma: no branch - controlled list
        assigned_materials[slot_name] = select_material(slot_name)

    traits = []
    for culture_trait in [style_stack.get("primary_style"), style_stack.get("secondary_style"), style_stack.get("secondary_culture_style")]:
        if culture_trait:
            traits.append(culture_trait)
    traits.extend(construction_methods[construction].get("traits") or [])
    traits.extend(function_styles[function_style].get("traits") or [])
    traits.extend(age_profiles[age].get("traits") or [])
    traits.extend(embellishments.get(embellishment, {}).get("traits") or [])
    traits = _apply_trait_compatibility(weapon_type, traits)
    traits = _resolve_trait_conflicts(traits, tier=resolved_tier, rng=rng)
    traits = traits[: TRAIT_LIMITS.get(resolved_tier, 4)]
    style_stack["primary_trait"] = rng.choice(traits) if traits else None

    name = _build_name(weapon_type, resolved_tier, style_stack, assigned_materials, traits)
    description = _build_description(weapon_type, style_stack, assigned_materials, traits)
    generated_id = _slugify(f"{primary_culture}_{secondary_culture or 'single'}_{weapon_type}_{resolved_tier}_{construction}_{assigned_materials.get('blade', assigned_materials.get('shaft', assigned_materials.get('grip')))['id']}")
    weapon_class = WEAPON_CLASS_BY_TYPE[weapon_type]
    tags = [
        "generated",
        "weapon",
        weapon_type,
        resolved_tier,
        primary_culture,
        function_style,
        construction,
    ]
    if secondary_culture:
        tags.append(secondary_culture)
    item_payload = {
        "id": generated_id,
        "name": name,
        "category": "weapon",
        "value": int(profile["damage"] * (8 + TIER_ORDER[resolved_tier] * 2)),
        "weight": 2.0 + (profile["speed"] * 0.35),
        "stackable": False,
        "max_stack": 1,
        "equipment": {"slot": "weapon", "attack": int(profile["damage"]), "defense": 0},
        "weapon_class": weapon_class,
        "tags": tags,
        "level_band": dict(TIER_LEVEL_BANDS[resolved_tier]),
        "description": {"short": name.lower(), "long": description},
        "meta": {"source": "weapon_generator", "imported_at": ""},
    }

    return {
        "weapon_type": weapon_type,
        "tier": resolved_tier,
        "name": name,
        "description": description,
        "traits": traits,
        "style_stack": style_stack,
        "materials": {key: dict(value) for key, value in assigned_materials.items()},
        "runtime_profile": profile,
        "item_payload": item_payload,
    }