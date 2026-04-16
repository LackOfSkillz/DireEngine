from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


TEMPLATE_SCHEMA_VERSION = "v1"
ALLOWED_TEMPLATE_TYPES = {"item", "npc"}
TEMPLATE_SCHEMA = {
    "template_id": str,
    "type": str,
    "name": str,
    "description": str,
    "tags": list,
}
OPTIONAL_TEMPLATE_FIELDS = {
	"attributes": dict,
	"flags": list,
	"item_kind": str,
	"weight": (int, float),
	"value": (int, float),
}


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _require_type(value: object, expected_type: type | tuple[type, ...], label: str) -> None:
    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_name = ", ".join(current_type.__name__ for current_type in expected_type)
        else:
            expected_name = expected_type.__name__
        raise ValueError(f"{label} must be of type {expected_name}.")


def _require_non_empty_string(value: object, label: str) -> str:
    _require_type(value, str, label)
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must be a non-empty string.")
    return normalized


def _normalize_tags(value: object) -> list[str]:
    _require_type(value, list, "tags")
    normalized_tags = []
    for index, tag in enumerate(value):
        normalized_tag = _require_non_empty_string(tag, f"tags[{index}]")
        normalized_tags.append(normalized_tag)
    return normalized_tags


def _normalize_attributes(value: object) -> dict[str, int | float]:
    _require_type(value, Mapping, "attributes")
    normalized_attributes: dict[str, int | float] = {}
    for raw_key, raw_value in value.items():
        attribute_name = _require_non_empty_string(raw_key, "attributes key").lower()
        _require_type(raw_value, (int, float), f"attributes.{attribute_name}")
        normalized_attributes[attribute_name] = int(raw_value) if isinstance(raw_value, int) else float(raw_value)
    return normalized_attributes


def _normalize_flags(value: object) -> list[str]:
    _require_type(value, list, "flags")
    normalized_flags: list[str] = []
    for index, flag in enumerate(value):
        normalized_flag = _require_non_empty_string(flag, f"flags[{index}]").lower()
        if normalized_flag not in normalized_flags:
            normalized_flags.append(normalized_flag)
    return normalized_flags


def validate_template(template: dict) -> None:
    payload = _require_mapping(template, "template")

    for field_name, field_type in TEMPLATE_SCHEMA.items():
        if field_name not in payload:
            raise ValueError(f"template is missing required field: {field_name}")
        _require_type(payload[field_name], field_type, field_name)

    template_id = _require_non_empty_string(payload.get("template_id"), "template_id")
    template_type = _require_non_empty_string(payload.get("type"), "type").lower()
    _require_non_empty_string(payload.get("name"), "name")
    _require_type(payload.get("description"), str, "description")
    _normalize_tags(payload.get("tags"))

    if template_type not in ALLOWED_TEMPLATE_TYPES:
        raise ValueError(f"type must be one of: {', '.join(sorted(ALLOWED_TEMPLATE_TYPES))}")
    if not template_id:
        raise ValueError("template_id must be a non-empty string.")

    for field_name, field_type in OPTIONAL_TEMPLATE_FIELDS.items():
        if field_name not in payload:
            continue
        _require_type(payload[field_name], field_type, field_name)

    if "attributes" in payload:
        _normalize_attributes(payload.get("attributes"))
    if "flags" in payload:
        _normalize_flags(payload.get("flags"))
    if "item_kind" in payload and str(payload.get("item_kind") or "").strip():
        _require_non_empty_string(payload.get("item_kind"), "item_kind")


def validate_template_registry(data: dict) -> None:
    payload = _require_mapping(data, "template registry")

    if payload.get("version") != TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f"template registry version must be {TEMPLATE_SCHEMA_VERSION}.")
    templates = payload.get("templates")
    _require_type(templates, list, "templates")

    seen_template_ids = set()
    for index, template in enumerate(templates):
        validate_template(template)
        template_id = _require_non_empty_string(template.get("template_id"), f"templates[{index}].template_id")
        if template_id in seen_template_ids:
            raise ValueError(f"duplicate template_id: {template_id}")
        seen_template_ids.add(template_id)


def get_template_registry_path() -> Path:
    return Path(__file__).resolve().parent.parent / "templates" / "template_registry_v1.json"