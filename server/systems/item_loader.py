from __future__ import annotations

from pathlib import Path

import yaml


ITEM_CATEGORY_DIRECTORIES = {
    "weapon": "weapons",
    "armor": "armor",
    "ammunition": "ammunition",
    "consumable": "consumables",
    "clothing": "clothing",
    "jewelry": "jewelry",
    "furniture": "furniture",
    "container": "containers",
    "misc": "misc",
}
ITEM_EQUIPMENT_SLOTS = {"none", "head", "chest", "legs", "hands", "weapon", "offhand", "accessory"}
ITEM_WEAPON_CLASSES = {
    "light_edge",
    "medium_edge",
    "heavy_edge",
    "light_blunt",
    "heavy_blunt",
    "short_bow",
    "long_bow",
    "crossbow",
    "thrown",
    "polearm",
}
ITEM_ARMOR_CLASSES = {
    "light_armor",
    "leather_armor",
    "chain_armor",
    "plate_armor",
}
ITEM_ARMOR_SLOTS = {
    "head",
    "neck",
    "shoulders",
    "chest",
    "arms",
    "hands",
    "waist",
    "legs",
    "feet",
    "shield",
    "cloak",
}
ITEM_AMMO_TYPES = {"arrow", "bolt"}
ITEM_AMMO_CLASSES = {"short_bow", "long_bow", "crossbow"}
ITEM_AMMO_TIERS = {"below_average", "average", "above_average", "exquisite", "epic", "legendary"}
ITEM_TIERS = set(ITEM_AMMO_TIERS)
ITEM_TIER_ALIASES = {"fine": "above_average"}
ITEM_EQUIPMENT_LAYERS = {"under", "base", "outer", "shield", "accessory", "attachment"}
ITEM_EQUIPMENT_SLOTS = ITEM_EQUIPMENT_SLOTS | ITEM_ARMOR_SLOTS
ITEM_EQUIPMENT_SLOTS = ITEM_EQUIPMENT_SLOTS | {"face", "back", "fingers", "belt_attach", "back_attach", "shoulder_attach"}
ITEM_ROOT = Path(__file__).resolve().parents[2] / "world_data" / "items"
ITEM_ALLOWED_TOP_LEVEL_KEYS = {
    "id",
    "name",
    "category",
    "value",
    "weight",
    "stackable",
    "max_stack",
    "equipment",
    "consumable",
    "container",
    "weapon_class",
    "armor_class",
    "armor_slot",
    "type",
    "ammo_type",
    "ammo_class",
    "stack_size",
    "base_price",
    "tier",
    "capacity",
    "quickdraw_bonus",
    "utility_category",
    "functional_type",
    "tool_type",
    "durability",
    "bait_family",
    "bait_quality",
    "layer",
    "equip_slots",
    "blocks_layers",
    "tags",
    "level_band",
    "description",
    "meta",
}
ITEM_ALLOWED_NESTED_KEYS = {
    "equipment": {"slot", "attack", "defense"},
    "consumable": {"effect", "duration"},
    "container": {"capacity", "weight_reduction", "ammo_container", "allowed_ammo_types"},
    "level_band": {"min", "max"},
    "description": {"short", "long"},
    "meta": {"source", "imported_at"},
}


def _item_defaults(item_id: str = "", category: str = "misc") -> dict:
    return {
        "id": item_id,
        "name": "",
        "category": category,
        "value": 0,
        "weight": 1.0,
        "stackable": False,
        "max_stack": 1,
        "equipment": {
            "slot": "none",
            "attack": 0,
            "defense": 0,
        },
        "consumable": {
            "effect": "",
            "duration": 0,
        },
        "container": {
            "capacity": 0,
            "weight_reduction": 0.0,
            "ammo_container": False,
            "allowed_ammo_types": [],
        },
        "weapon_class": "",
        "armor_class": "",
        "armor_slot": "",
        "type": "",
        "ammo_type": "",
        "ammo_class": "",
        "stack_size": 0,
        "base_price": 0,
        "tier": "",
        "capacity": 0,
        "quickdraw_bonus": 0.0,
        "utility_category": "",
        "functional_type": "",
        "tool_type": "",
        "durability": 0,
        "bait_family": "",
        "bait_quality": 0.0,
        "layer": "",
        "equip_slots": [],
        "blocks_layers": [],
        "tags": [],
        "level_band": {
            "min": 1,
            "max": 1,
        },
        "description": {
            "short": "",
            "long": "",
        },
        "meta": {
            "source": "",
            "imported_at": "",
        },
    }


def _normalize_category(value) -> str:
    category = str(value or "").strip().lower()
    if category not in ITEM_CATEGORY_DIRECTORIES:
        raise ValueError("category must be weapon, armor, ammunition, consumable, clothing, jewelry, furniture, container, or misc")
    return category


def _coerce_int(value, field_name: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return parsed


def _coerce_float(value, field_name: str, *, minimum: float | None = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    return parsed


def _normalize_tags(values) -> list[str]:
    if not isinstance(values, list):
        return []
    tags = []
    seen = set()
    for value in values:
        normalized = str(value or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tags.append(normalized)
    return tags


def _normalize_string_list(values, *, field_name: str, allowed_values: set[str] | None = None) -> list[str]:
    if values in (None, ""):
        return []
    if not isinstance(values, list):
        raise ValueError(f"{field_name} must be a list")
    normalized = []
    seen = set()
    for value in values:
        item = str(value or "").strip().lower()
        if not item or item in seen:
            continue
        if allowed_values and item not in allowed_values:
            raise ValueError(f"{field_name} contains an invalid value")
        seen.add(item)
        normalized.append(item)
    return normalized


def _default_equipment_layer(category: str, armor_class: str, armor_slot: str, equipment_slot: str) -> str:
    if equipment_slot in {"belt_attach", "back_attach", "shoulder_attach"}:
        return "attachment"
    if armor_slot == "shield":
        return "shield"
    if category == "jewelry" or equipment_slot in {"fingers", "accessory"}:
        return "accessory"
    if category == "armor":
        if armor_class in {"chain_armor", "plate_armor"}:
            return "outer"
        return "base"
    return "base"


def _default_blocked_layers(category: str, armor_class: str, armor_slot: str, layer: str) -> list[str]:
    if category != "armor":
        return []
    if armor_slot in {"shield", "cloak"}:
        return []
    if layer == "outer" and armor_class in {"chain_armor", "plate_armor"}:
        return ["under", "base"]
    return []


def validate_item_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Item payload must be an object")
    unknown_top_level = sorted(set(payload.keys()) - ITEM_ALLOWED_TOP_LEVEL_KEYS)
    if unknown_top_level:
        raise ValueError(f"unknown item fields: {', '.join(unknown_top_level)}")
    for field_name, allowed_keys in ITEM_ALLOWED_NESTED_KEYS.items():
        field_value = payload.get(field_name)
        if field_value is None:
            continue
        if not isinstance(field_value, dict):
            raise ValueError(f"{field_name} must be an object")
        unknown_nested = sorted(set(field_value.keys()) - allowed_keys)
        if unknown_nested:
            raise ValueError(f"unknown {field_name} fields: {', '.join(unknown_nested)}")


def normalize_item_payload(payload: dict, *, fallback_id: str = "", fallback_category: str = "misc") -> dict:
    validate_item_payload(payload)

    category = _normalize_category(payload.get("category") or fallback_category)
    defaults = _item_defaults(str(payload.get("id") or fallback_id or "").strip(), category)
    item_id = str(payload.get("id") or fallback_id or "").strip()
    name = str(payload.get("name") or "").strip()
    if not item_id:
        raise ValueError("id is required")
    if not name:
        raise ValueError("name is required")

    equipment_payload = payload.get("equipment") if isinstance(payload.get("equipment"), dict) else {}
    equipment = dict(defaults["equipment"])
    equipment_slot = str(equipment_payload.get("slot", equipment["slot"]) or "none").strip().lower() or "none"
    if equipment_slot not in ITEM_EQUIPMENT_SLOTS:
        raise ValueError("equipment.slot is invalid")
    equipment["slot"] = equipment_slot
    equipment["attack"] = _coerce_int(equipment_payload.get("attack", equipment["attack"]), "equipment.attack", minimum=0)
    equipment["defense"] = _coerce_int(equipment_payload.get("defense", equipment["defense"]), "equipment.defense", minimum=0)
    if category == "weapon":
        equipment["slot"] = "weapon"
    if category not in {"weapon", "armor"}:
        equipment = {"slot": "none", "attack": 0, "defense": 0}

    consumable_payload = payload.get("consumable") if isinstance(payload.get("consumable"), dict) else {}
    consumable = dict(defaults["consumable"])
    consumable["effect"] = str(consumable_payload.get("effect", consumable["effect"]) or "")
    consumable["duration"] = _coerce_int(consumable_payload.get("duration", consumable["duration"]), "consumable.duration", minimum=0)
    if category != "consumable":
        consumable = {"effect": "", "duration": 0}

    container_payload = payload.get("container") if isinstance(payload.get("container"), dict) else {}
    container = dict(defaults["container"])
    container["capacity"] = _coerce_int(container_payload.get("capacity", container["capacity"]), "container.capacity", minimum=0)
    weight_reduction = _coerce_float(container_payload.get("weight_reduction", container.get("weight_reduction", 0.0)), "container.weight_reduction", minimum=0.0)
    if weight_reduction > 1.0:
        raise ValueError("container.weight_reduction must be <= 1.0")
    container["weight_reduction"] = weight_reduction
    container["ammo_container"] = bool(container_payload.get("ammo_container", False))
    container["allowed_ammo_types"] = _normalize_string_list(
        container_payload.get("allowed_ammo_types", []),
        field_name="container.allowed_ammo_types",
        allowed_values=ITEM_AMMO_TYPES,
    )
    if category != "container":
        container = {"capacity": 0, "weight_reduction": 0.0, "ammo_container": False, "allowed_ammo_types": []}

    level_band_payload = payload.get("level_band") if isinstance(payload.get("level_band"), dict) else {}
    level_band = dict(defaults["level_band"])
    level_band["min"] = _coerce_int(level_band_payload.get("min", level_band["min"]), "level_band.min", minimum=1)
    level_band["max"] = _coerce_int(level_band_payload.get("max", level_band["max"]), "level_band.max", minimum=1)
    if level_band["max"] < level_band["min"]:
        raise ValueError("level_band.max must be >= level_band.min")

    weapon_class = str(payload.get("weapon_class") or defaults["weapon_class"] or "").strip().lower()
    if category == "weapon" and not weapon_class:
        raise ValueError("weapon_class is required for weapon items")
    if weapon_class and weapon_class not in ITEM_WEAPON_CLASSES:
        raise ValueError("weapon_class is invalid")
    if category != "weapon":
        weapon_class = ""

    armor_class = str(payload.get("armor_class") or defaults["armor_class"] or "").strip().lower()
    armor_slot = str(payload.get("armor_slot") or defaults["armor_slot"] or "").strip().lower()
    item_type = str(payload.get("type") or defaults["type"] or "").strip().lower()
    ammo_type = str(payload.get("ammo_type") or defaults["ammo_type"] or "").strip().lower()
    ammo_class = str(payload.get("ammo_class") or defaults["ammo_class"] or "").strip().lower()
    stack_size = _coerce_int(payload.get("stack_size", defaults["stack_size"]), "stack_size", minimum=0)
    base_price = _coerce_int(payload.get("base_price", defaults["base_price"]), "base_price", minimum=0)
    tier = str(payload.get("tier") or defaults["tier"] or "").strip().lower()
    tier = ITEM_TIER_ALIASES.get(tier, tier)
    if tier and tier not in ITEM_TIERS:
        raise ValueError("tier is invalid")
    if category == "armor":
        if not armor_class:
            raise ValueError("armor_class is required for armor items")
        if armor_class not in ITEM_ARMOR_CLASSES:
            raise ValueError("armor_class is invalid")
        if not armor_slot:
            raise ValueError("armor_slot is required for armor items")
        if armor_slot not in ITEM_ARMOR_SLOTS:
            raise ValueError("armor_slot is invalid")
        if not tier:
            raise ValueError("tier is required for armor items")
        equipment["slot"] = armor_slot
    else:
        armor_class = ""
        armor_slot = ""
    if category == "ammunition":
        if not ammo_type:
            raise ValueError("ammo_type is required for ammunition items")
        if ammo_type not in ITEM_AMMO_TYPES:
            raise ValueError("ammo_type is invalid")
        if not ammo_class:
            raise ValueError("ammo_class is required for ammunition items")
        if ammo_class not in ITEM_AMMO_CLASSES:
            raise ValueError("ammo_class is invalid")
        if stack_size != 10:
            raise ValueError("stack_size must equal 10 for ammunition items")
        if not tier:
            raise ValueError("tier is required for ammunition items")
        if base_price <= 0:
            raise ValueError("base_price is required for ammunition items")
    else:
        if item_type != "ammo_container":
            ammo_type = ""
        ammo_class = ""
        stack_size = 0
        base_price = 0

    utility_category = str(payload.get("utility_category") or defaults["utility_category"] or "").strip().lower()
    functional_type = str(payload.get("functional_type") or defaults["functional_type"] or "").strip().lower()
    tool_type = str(payload.get("tool_type") or defaults["tool_type"] or "").strip().lower()
    durability = _coerce_int(payload.get("durability", defaults["durability"]), "durability", minimum=0)
    quickdraw_bonus = _coerce_float(payload.get("quickdraw_bonus", defaults["quickdraw_bonus"]), "quickdraw_bonus", minimum=0.0)
    bait_family = str(payload.get("bait_family") or defaults["bait_family"] or "").strip().lower()
    bait_quality = _coerce_float(payload.get("bait_quality", defaults["bait_quality"]), "bait_quality", minimum=0.0)
    if item_type == "ammo_container":
        if category != "container":
            raise ValueError("type ammo_container requires category container")
        functional_type = functional_type or "quiver"
        utility_category = utility_category or "containers"
        container["ammo_container"] = True
        if ammo_type and ammo_type not in ITEM_AMMO_TYPES:
            raise ValueError("ammo_type is invalid")
        if not ammo_type:
            ammo_type = "arrow"
        container_capacity = payload.get("capacity", container_payload.get("capacity", container.get("capacity", 0)))
        container["capacity"] = _coerce_int(container_capacity, "capacity", minimum=0)
    else:
        item_type = ""
        quickdraw_bonus = 0.0
    if functional_type != "bait":
        bait_family = ""
        bait_quality = 0.0

    equip_slots = _normalize_string_list(
        payload.get("equip_slots", defaults["equip_slots"]),
        field_name="equip_slots",
        allowed_values=ITEM_EQUIPMENT_SLOTS,
    )
    if category == "armor":
        equip_slots = [armor_slot]
    elif category in {"clothing", "jewelry", "container"} and equipment["slot"] != "none" and not equip_slots:
        equip_slots = [equipment["slot"]]

    layer = str(payload.get("layer") or defaults["layer"] or "").strip().lower()
    if not layer:
        layer = _default_equipment_layer(category, armor_class, armor_slot, equipment["slot"])
    if layer not in ITEM_EQUIPMENT_LAYERS:
        raise ValueError("layer is invalid")

    blocks_layers = _normalize_string_list(
        payload.get("blocks_layers", defaults["blocks_layers"]),
        field_name="blocks_layers",
        allowed_values=ITEM_EQUIPMENT_LAYERS,
    )
    if not blocks_layers:
        blocks_layers = _default_blocked_layers(category, armor_class, armor_slot, layer)

    tags = _normalize_tags(payload.get("tags", defaults["tags"]))

    description_payload = payload.get("description") if isinstance(payload.get("description"), dict) else {}
    description = dict(defaults["description"])
    description["short"] = str(description_payload.get("short", description["short"]) or "").strip()
    description["long"] = str(description_payload.get("long", description["long"]) or "").strip()

    meta_payload = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta = dict(defaults["meta"])
    meta["source"] = str(meta_payload.get("source", meta["source"]) or "").strip()
    meta["imported_at"] = str(meta_payload.get("imported_at", meta["imported_at"]) or "").strip()

    stackable = bool(payload.get("stackable", defaults["stackable"]))
    max_stack = _coerce_int(payload.get("max_stack", defaults["max_stack"]), "max_stack", minimum=1)
    if not stackable:
        max_stack = 1

    return {
        "id": item_id,
        "name": name,
        "category": category,
        "value": _coerce_int(payload.get("value", defaults["value"]), "value", minimum=0),
        "weight": _coerce_float(payload.get("weight", defaults["weight"]), "weight", minimum=0.0),
        "stackable": stackable,
        "max_stack": max_stack,
        "equipment": equipment,
        "consumable": consumable,
        "container": container,
        "weapon_class": weapon_class,
        "armor_class": armor_class,
        "armor_slot": armor_slot,
        "type": item_type,
        "ammo_type": ammo_type,
        "ammo_class": ammo_class,
        "stack_size": stack_size,
        "base_price": base_price,
        "tier": tier,
        "capacity": int(container.get("capacity", 0) or 0),
        "quickdraw_bonus": quickdraw_bonus,
        "utility_category": utility_category,
        "functional_type": functional_type,
        "tool_type": tool_type,
        "durability": durability,
        "bait_family": bait_family,
        "bait_quality": bait_quality,
        "layer": layer,
        "equip_slots": equip_slots,
        "blocks_layers": blocks_layers,
        "tags": tags,
        "level_band": level_band,
        "description": description,
        "meta": meta,
    }


def get_item_record(item_id: str, item_records: dict | None = None) -> dict:
    normalized_id = str(item_id or "").strip()
    if not normalized_id:
        raise ValueError("item_id is required")
    records = dict(item_records or {}) or load_all_items()
    if normalized_id not in records:
        raise ValueError(f"Unknown item '{normalized_id}'")
    return dict(records[normalized_id])


def _item_directory_for_category(category: str) -> Path:
    return ITEM_ROOT / ITEM_CATEGORY_DIRECTORIES[_normalize_category(category)]


def _iter_item_files():
    if not ITEM_ROOT.exists():
        return
    for directory_name in ITEM_CATEGORY_DIRECTORIES.values():
        directory = ITEM_ROOT / directory_name
        if not directory.exists():
            continue
        for file_path in sorted(directory.glob("*.yaml")):
            if file_path.name == "schema_item.yaml":
                continue
            yield file_path


def _find_item_file(item_id: str) -> Path | None:
    normalized_id = str(item_id or "").strip()
    if not normalized_id:
        return None
    for file_path in _iter_item_files() or []:
        if file_path.stem == normalized_id:
            return file_path
    return None


def load_all_items():
    items = {}
    for file_path in _iter_item_files() or []:
        with file_path.open(encoding="utf-8") as file_handle:
            payload = yaml.safe_load(file_handle) or {}
        normalized = normalize_item_payload(payload, fallback_id=file_path.stem)
        items[normalized["id"]] = normalized
    return dict(sorted(items.items(), key=lambda item: item[0]))


def save_item_payload(payload: dict) -> dict:
    normalized = normalize_item_payload(payload)
    target_path = _item_directory_for_category(normalized["category"]) / f"{normalized['id']}.yaml"
    previous_path = _find_item_file(normalized["id"])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if previous_path and previous_path != target_path and previous_path.exists():
        previous_path.unlink()
    with target_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(normalized, file_handle, sort_keys=False)
    return normalized


def delete_item_payload(item_id: str) -> str:
    file_path = _find_item_file(item_id)
    if file_path is None or not file_path.exists():
        raise ValueError("not_found")
    file_path.unlink()
    return str(item_id)