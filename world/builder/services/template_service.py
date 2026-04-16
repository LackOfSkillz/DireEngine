from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from world.builder.schemas.template_schema_v1 import (
    ALLOWED_TEMPLATE_TYPES,
    TEMPLATE_SCHEMA_VERSION,
    get_template_registry_path,
    validate_template,
    validate_template_registry,
)


BUILDER_TEMPLATE_SERVICE_AVAILABLE = False

try:
    import world.builder  # noqa: F401
except Exception:  # pragma: no cover - optional builder dependency guard
    pass
else:
    BUILDER_TEMPLATE_SERVICE_AVAILABLE = True


def _require_builder_service() -> None:
    if not BUILDER_TEMPLATE_SERVICE_AVAILABLE:
        raise RuntimeError("Builder template service is unavailable.")


def _normalize_template(template: dict) -> dict:
    validate_template(template)
    attributes = template.get("attributes", {})
    flags = template.get("flags", [])
    return {
        "template_id": str(template["template_id"]).strip(),
        "type": str(template["type"]).strip().lower(),
        "name": str(template["name"]).strip(),
        "description": str(template["description"]),
        "tags": [str(tag).strip() for tag in template.get("tags", [])],
        "attributes": {str(key).strip().lower(): value for key, value in dict(attributes or {}).items()},
        "flags": [str(flag).strip().lower() for flag in list(flags or []) if str(flag).strip()],
        "item_kind": str(template.get("item_kind", "") or "").strip().lower(),
        "weight": float(template.get("weight", 0.0) or 0.0),
        "value": float(template.get("value", 0.0) or 0.0),
        "has_explicit_description": bool(template.get("has_explicit_description", True)),
    }


def _normalize_registry(data: dict) -> dict:
    validate_template_registry(data)
    return {
        "version": TEMPLATE_SCHEMA_VERSION,
        "templates": [_normalize_template(template) for template in data.get("templates", [])],
    }


def _starter_item_templates() -> list[dict]:
    try:
        from systems.character.creation import PROFESSION_STARTER_WEAPONS, RACE_STARTER_KIT
    except Exception:
        return []

    templates: list[dict] = [
        {
            "template_id": "starter.item.divine_charm",
            "type": "item",
            "name": "divine charm",
            "description": "A simple protective charm given to new adventurers.",
            "tags": ["starter", "accessory", "wearable"],
            "item_kind": "wearable",
            "weight": 0.1,
            "value": 0.0,
        },
        {
            "template_id": "starter.item.brookhollow_map",
            "type": "item",
            "name": "brookhollow map",
            "description": "A simple starter map marked with the nearby roads and common landmarks.",
            "tags": ["starter", "map", "utility"],
            "item_kind": "utility",
            "weight": 0.1,
            "value": 0.0,
        },
        {
            "template_id": "starter.item.test_leather_armor",
            "type": "item",
            "name": "test leather armor",
            "description": "A suit of light leather armor fit for a new adventurer.",
            "tags": ["starter", "armor", "light_armor"],
            "item_kind": "armor",
            "weight": 0.0,
            "value": 0.0,
            "attributes": {"protection": 2, "hindrance": 1},
        },
    ]

    weapon_profiles = {
        "dagger": {
            "template_id": "starter.item.training_dagger",
            "name": "training dagger",
            "description": "A simple practice dagger issued to new adventurers.",
            "weight": 3.0,
            "attributes": {"damage_min": 2, "damage_max": 5, "balance": 60},
            "tags": ["starter", "weapon", "dagger", "training"],
        },
        "sword": {
            "template_id": "starter.item.training_sword",
            "name": "training sword",
            "description": "A simple practice sword issued to new adventurers.",
            "weight": 3.0,
            "attributes": {"damage_min": 3, "damage_max": 6, "balance": 55},
            "tags": ["starter", "weapon", "sword", "training"],
        },
        "mace": {
            "template_id": "starter.item.training_mace",
            "name": "training mace",
            "description": "A simple practice mace issued to new adventurers.",
            "weight": 3.0,
            "attributes": {"damage_min": 4, "damage_max": 8, "balance": 45},
            "tags": ["starter", "weapon", "mace", "training"],
        },
        "spear": {
            "template_id": "starter.item.training_spear",
            "name": "training spear",
            "description": "A simple practice spear issued to new adventurers.",
            "weight": 3.0,
            "attributes": {"damage_min": 3, "damage_max": 7, "balance": 52},
            "tags": ["starter", "weapon", "spear", "training"],
        },
    }
    for weapon_type in sorted(set(PROFESSION_STARTER_WEAPONS.values())):
        profile = weapon_profiles.get(str(weapon_type).strip().lower())
        if profile is None:
            continue
        templates.append(
            {
                "template_id": profile["template_id"],
                "type": "item",
                "name": profile["name"],
                "description": profile["description"],
                "tags": list(profile["tags"]),
                "item_kind": "weapon",
                "weight": float(profile["weight"]),
                "value": 0.0,
                "attributes": dict(profile["attributes"]),
            }
        )

    seen_race_kit_items: set[str] = set()
    for race_id, race_kit in dict(RACE_STARTER_KIT).items():
        for slot_name, item_name in dict(race_kit).items():
            normalized_item_name = str(item_name).strip()
            if not normalized_item_name:
                continue
            normalized_template_id = "starter.item.%s" % normalized_item_name.lower().replace("'", "").replace(" ", "_")
            if normalized_template_id in seen_race_kit_items:
                continue
            seen_race_kit_items.add(normalized_template_id)
            item_kind = "container" if slot_name == "container" else "wearable"
            description = (
                "A starter container prepared for a newly arrived adventurer."
                if slot_name == "container"
                else "A basic piece of starter clothing suited to the road."
                if slot_name == "clothing"
                else "A small personal accessory included with a new adventurer's starting kit."
            )
            tags = ["starter", race_id, slot_name]
            if slot_name == "container":
                tags.append("utility")
            else:
                tags.append("wearable")
            templates.append(
                {
                    "template_id": normalized_template_id,
                    "type": "item",
                    "name": normalized_item_name,
                    "description": description,
                    "tags": tags,
                    "item_kind": item_kind,
                    "weight": 1.5 if slot_name == "container" else 1.0 if slot_name == "clothing" else 0.5,
                    "value": 0.0,
                }
            )

    return [_normalize_template(template) for template in templates]


def _guard_templates() -> list[dict]:
    try:
        from world.systems import guards
    except Exception:
        return []

    templates: list[dict] = []
    for template in guards._load_valid_guard_templates():
        template_id = str(template.get("template_id") or template.get("canonical_key") or "").strip()
        template_name = str(template.get("name") or "").strip()
        if not template_id or not template_name:
            continue
        normalized_fields = dict(template.get("normalized_fields") or {})
        base_health = template.get("base_health", 0)
        attributes = {}
        if isinstance(base_health, (int, float)):
            attributes["base_health"] = base_health
        description_text = str(normalized_fields.get("desc") or "").strip()
        templates.append(
            _normalize_template(
                {
                    "template_id": template_id,
                    "type": "npc",
                    "name": template_name,
                    "description": description_text,
                    "tags": [str(tag).strip().lower() for tag in list(template.get("tags") or []) if str(tag).strip()],
                    "attributes": attributes,
                    "flags": ["guard"],
                    "has_explicit_description": bool(description_text),
                }
            )
        )
    if not any(str(template.get("name") or "").strip().lower() == str(getattr(guards, "GUARD_DISPLAY_NAME", "Town Guard")).strip().lower() for template in templates):
        templates.append(
            _normalize_template(
                {
                    "template_id": "guard.town_guard",
                    "type": "npc",
                    "name": str(getattr(guards, "GUARD_DISPLAY_NAME", "Town Guard")),
                    "description": "A watchful civic guard on regular patrol.",
                    "tags": ["guard", "guard_validated", "civic", "patrol"],
                    "attributes": {"base_health": 100},
                    "flags": ["guard"],
                    "has_explicit_description": False,
                }
            )
        )
    return templates


def _list_synthesized_templates() -> list[dict]:
    templates_by_id: dict[str, dict] = {}
    for template in _starter_item_templates() + _guard_templates():
        template_id = str(template.get("template_id") or "").strip()
        if not template_id:
            continue
        templates_by_id[template_id] = dict(template)
    return sorted(templates_by_id.values(), key=lambda template: (template["template_id"], template["name"]))


def _all_templates() -> list[dict]:
    templates_by_id: dict[str, dict] = {}
    for template in _list_synthesized_templates():
        templates_by_id[str(template["template_id"])] = dict(template)
    for template in load_template_registry()["templates"]:
        templates_by_id[str(template["template_id"])] = dict(template)
    return sorted(templates_by_id.values(), key=lambda template: (template["template_id"], template["name"]))


def load_template_registry() -> dict:
    _require_builder_service()
    registry_path = get_template_registry_path()
    if not registry_path.exists():
        return {"version": TEMPLATE_SCHEMA_VERSION, "templates": []}

    with registry_path.open("r", encoding="utf-8") as registry_file:
        data = json.load(registry_file)
    return _normalize_registry(data)


def save_template_registry(data: dict) -> None:
    _require_builder_service()
    normalized_registry = _normalize_registry(data)
    registry_path = get_template_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(registry_path.parent), suffix=".tmp") as temp_file:
            json.dump(normalized_registry, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, registry_path)
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def get_template(template_id: str) -> dict | None:
    _require_builder_service()
    normalized_template_id = str(template_id or "").strip()
    if not normalized_template_id:
        raise ValueError("template_id must be a non-empty string.")

    for template in _all_templates():
        if template["template_id"] == normalized_template_id:
            return dict(template)
    return None


def require_template(template_id: str) -> dict:
    template = get_template(template_id)
    if template is None:
        raise ValueError(f"Unknown template_id: {template_id}")
    return template


def list_templates(template_type: str | None = None) -> list[dict]:
    _require_builder_service()
    templates = [dict(template) for template in _all_templates()]

    if template_type is not None:
        normalized_type = str(template_type or "").strip().lower()
        if normalized_type not in ALLOWED_TEMPLATE_TYPES:
            raise ValueError(f"template_type must be one of: {', '.join(sorted(ALLOWED_TEMPLATE_TYPES))}")
        templates = [template for template in templates if template["type"] == normalized_type]

    return sorted(templates, key=lambda template: (template["template_id"], template["name"]))


def search_templates(query: str, template_type: str | None = None) -> list[dict]:
    _require_builder_service()
    normalized_query = str(query or "").strip().lower()
    if not normalized_query:
        return list_templates(template_type=template_type)

    matches = []
    for template in list_templates(template_type=template_type):
        haystacks = [template["template_id"], template["name"], " ".join(template.get("tags", []))]
        if any(normalized_query in str(value).lower() for value in haystacks):
            matches.append(template)
    return matches


def register_template(template: dict) -> dict:
    _require_builder_service()
    normalized_template = _normalize_template(template)
    registry = load_template_registry()

    if any(candidate["template_id"] == normalized_template["template_id"] for candidate in registry["templates"]):
        raise ValueError(f"duplicate template_id: {normalized_template['template_id']}")

    registry["templates"].append(normalized_template)
    save_template_registry(registry)
    return dict(normalized_template)


def update_template(template_id: str, updates: dict) -> dict:
    _require_builder_service()
    normalized_template_id = str(template_id or "").strip()
    if not normalized_template_id:
        raise ValueError("template_id must be a non-empty string.")
    if not isinstance(updates, dict):
        raise ValueError("updates must be a mapping.")

    allowed_fields = {"name", "description", "tags", "attributes", "flags", "item_kind", "weight", "value"}
    unknown_fields = sorted(set(updates.keys()) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"Unsupported template update fields: {', '.join(unknown_fields)}")
    if "template_id" in updates or "type" in updates:
        raise ValueError("template_id and type cannot be changed.")

    registry = load_template_registry()
    for index, template in enumerate(registry["templates"]):
        if template["template_id"] != normalized_template_id:
            continue

        updated_template = dict(template)
        updated_template.update(updates)
        normalized_updated_template = _normalize_template(updated_template)
        registry["templates"][index] = normalized_updated_template
        save_template_registry(registry)
        return dict(normalized_updated_template)

    raise ValueError(f"Unknown template_id: {template_id}")