from __future__ import annotations

from pathlib import Path

import yaml

from server.systems import item_loader


KIT_TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "world_data" / "kit_templates"
KIT_TEMPLATES: dict[str, dict] = {}
KIT_TEMPLATE_ALLOWED_KEYS = {
    "id",
    "armor_class",
    "theme_tags",
    "required_slots",
    "optional_slots",
    "tier_bias",
}


def _normalize_string_list(values) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized = []
    seen = set()
    for value in values:
        item = str(value or "").strip().lower()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def _normalize_weight_map(values) -> dict[str, float]:
    payload = values if isinstance(values, dict) else {}
    normalized = {}
    total = 0.0
    for key, raw_value in payload.items():
        normalized_key = str(key or "").strip().lower()
        if normalized_key not in item_loader.ITEM_AMMO_TIERS:
            raise ValueError("kit tier_bias contains an invalid tier")
        weight = float(raw_value or 0.0)
        if weight < 0.0:
            raise ValueError("kit tier_bias weights must be >= 0")
        normalized[normalized_key] = weight
        total += weight
    if total > 1.0 + 1e-9:
        raise ValueError("kit tier_bias weights must sum to <= 1.0")
    return normalized


def validate_kit_template(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Kit template payload must be an object")
    unknown = sorted(set(payload.keys()) - KIT_TEMPLATE_ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"unknown kit template fields: {', '.join(unknown)}")


def normalize_kit_template(payload: dict, *, fallback_id: str = "") -> dict:
    validate_kit_template(payload)
    template_id = str(payload.get("id") or fallback_id or "").strip()
    if not template_id:
        raise ValueError("kit template id is required")
    armor_class = str(payload.get("armor_class") or "").strip().lower()
    if armor_class not in item_loader.ITEM_ARMOR_CLASSES:
        raise ValueError("kit template armor_class is invalid")
    required_slots = _normalize_string_list(payload.get("required_slots"))
    optional_slots = _normalize_string_list(payload.get("optional_slots"))
    if not required_slots:
        raise ValueError("kit template required_slots is required")
    for slot_name in required_slots + optional_slots:
        if slot_name not in item_loader.ITEM_ARMOR_SLOTS:
            raise ValueError("kit template slot is invalid")
    tier_bias = _normalize_weight_map(payload.get("tier_bias"))
    if not tier_bias:
        tier_bias = {"average": 0.6, "above_average": 0.3, "exquisite": 0.1}
    return {
        "id": template_id,
        "armor_class": armor_class,
        "theme_tags": _normalize_string_list(payload.get("theme_tags")),
        "required_slots": required_slots,
        "optional_slots": optional_slots,
        "tier_bias": tier_bias,
    }


def _iter_template_files():
    if not KIT_TEMPLATE_ROOT.exists():
        return
    for file_path in sorted(KIT_TEMPLATE_ROOT.glob("*.yaml")):
        if file_path.name == "schema_kit_template.yaml":
            continue
        yield file_path


def load_kit_templates() -> dict[str, dict]:
    templates = {}
    for file_path in _iter_template_files() or []:
        with file_path.open(encoding="utf-8") as file_handle:
            payload = yaml.safe_load(file_handle) or {}
        normalized = normalize_kit_template(payload, fallback_id=file_path.stem)
        templates[normalized["id"]] = normalized
    return dict(sorted(templates.items(), key=lambda item: item[0]))


def reload_kit_templates() -> dict[str, dict]:
    KIT_TEMPLATES.clear()
    KIT_TEMPLATES.update(load_kit_templates())
    return dict(KIT_TEMPLATES)


def get_kit_template(template_id: str) -> dict:
    normalized_id = str(template_id or "").strip()
    if not normalized_id:
        raise ValueError("kit template id is required")
    if not KIT_TEMPLATES:
        reload_kit_templates()
    if normalized_id not in KIT_TEMPLATES:
        raise ValueError(f"Unknown kit template '{normalized_id}'")
    return dict(KIT_TEMPLATES[normalized_id])
