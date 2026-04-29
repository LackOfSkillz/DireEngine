from __future__ import annotations

from collections.abc import Mapping, Sequence

from world.builder.schemas.generation_context_schema import normalize_generation_context
from world.builder.schemas.room_tag_schema import normalize_room_tags


_LIST_FIELDS = (
    "required_room_facts",
    "allowed_but_not_required",
    "soft_zone_context",
    "soft_area_context",
    "soft_room_context",
    "forbidden_features",
    "interactive_objects",
)
_GENERATION_INPUT_KEY = "generation_input"


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _normalize_optional_string(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_string_list(value: object, label: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a list of strings.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _normalize_allowed_exits(value: object, label: str) -> list[dict[str, str]]:
    if value in (None, ""):
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be a list.")

    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index, item in enumerate(value):
        direction: str | None = None
        target: str | None = None
        exit_type: str | None = None
        description: str | None = None
        if isinstance(item, Mapping):
            direction = _normalize_optional_string(item.get("direction"))
            target = _normalize_optional_string(item.get("target"))
            exit_type = _normalize_optional_string(item.get("type"))
            description = _normalize_optional_string(item.get("description"))
        else:
            direction = _normalize_optional_string(item)
        if not direction:
            raise ValueError(f"{label}[{index}] must include a direction.")
        entry = {
            "direction": direction.lower(),
            "target": target or "",
            "type": exit_type or "",
            "description": description or "",
        }
        key = (entry["direction"], entry["target"], entry["type"], entry["description"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(entry)
    return normalized


def _humanize(value: object) -> str:
    return " ".join(str(value or "").replace("_", " ").replace("-", " ").split()).strip().lower()


def empty_typed_generation_input() -> dict[str, object]:
    return {
        "required_room_facts": [],
        "allowed_but_not_required": [],
        "soft_zone_context": [],
        "soft_area_context": [],
        "soft_room_context": [],
        "forbidden_features": [],
        "allowed_exits": [],
        "interactive_objects": [],
    }


def normalize_typed_generation_input(data: object) -> dict[str, object]:
    if data in (None, ""):
        return empty_typed_generation_input()

    payload = _require_mapping(data, "typed generation input")
    normalized = {
        field: _normalize_string_list(payload.get(field), f"generation_input.{field}")
        for field in _LIST_FIELDS
    }
    normalized["allowed_exits"] = _normalize_allowed_exits(payload.get("allowed_exits"), "generation_input.allowed_exits")
    return normalized


def _extract_explicit_generation_input(payload: Mapping | None) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        return empty_typed_generation_input()
    explicit = payload.get(_GENERATION_INPUT_KEY)
    return normalize_typed_generation_input(explicit)


def _legacy_room_generation_input(room_payload: Mapping | None) -> dict[str, object]:
    if not isinstance(room_payload, Mapping):
        return empty_typed_generation_input()

    room_tags = normalize_room_tags(room_payload.get("tags"))
    legacy = empty_typed_generation_input()

    for field in ("structure", "specific_function", "named_feature"):
        value = _humanize(room_tags.get(field))
        if value:
            legacy["required_room_facts"].append(value)

    condition = _humanize(room_tags.get("condition"))
    if condition:
        legacy["allowed_but_not_required"].append(condition)

    for value in list(room_tags.get("custom") or []):
        text = _humanize(value)
        if text:
            legacy["soft_room_context"].append(text)

    atmosphere = dict(room_tags.get("atmosphere") or {})
    for field in ("materials", "social_character", "surroundings", "sensory"):
        for value in list(atmosphere.get(field) or []):
            text = _humanize(value)
            if text:
                legacy["allowed_but_not_required"].append(text)
    upkeep = _humanize(atmosphere.get("upkeep"))
    if upkeep:
        legacy["allowed_but_not_required"].append(upkeep)

    exits = room_payload.get("exits") or room_payload.get("exitMap") or {}
    legacy["allowed_exits"] = _normalize_allowed_exits(
        [
            {
                "direction": direction,
                "target": (spec.get("target") or spec.get("target_id")) if isinstance(spec, Mapping) else spec,
            }
            for direction, spec in dict(exits).items()
            if str(direction or "").strip()
        ],
        "legacy.allowed_exits",
    )
    return normalize_typed_generation_input(legacy)


def _legacy_zone_soft_context(zone_payload: Mapping | None) -> list[str]:
    if not isinstance(zone_payload, Mapping):
        return []
    context = normalize_generation_context(zone_payload.get("generation_context"))
    if not context:
        return []

    values: list[str] = []
    zone_name = _normalize_optional_string(zone_payload.get("name") or zone_payload.get("zone_id"))
    if zone_name:
        values.append(zone_name)
    for field in ("setting_type", "era_feel", "climate", "voice"):
        text = _humanize(context.get(field))
        if text:
            values.append(text)
    for field in ("culture", "mood"):
        for item in list(context.get(field) or []):
            text = _humanize(item)
            if text:
                values.append(text)
    return _normalize_string_list(values, "legacy.soft_zone_context")


def _merge_string_lists(*values: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for items in values:
        for item in items:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
    return merged


def resolve_typed_generation_input(
    room_payload: Mapping | None,
    zone_payload: Mapping | None = None,
    area_payload: Mapping | None = None,
) -> dict[str, object]:
    zone_explicit = _extract_explicit_generation_input(zone_payload)
    area_explicit = _extract_explicit_generation_input(area_payload)
    room_explicit = _extract_explicit_generation_input(room_payload)
    room_legacy = _legacy_room_generation_input(room_payload)

    resolved = empty_typed_generation_input()
    resolved["required_room_facts"] = _merge_string_lists(
        list(room_legacy.get("required_room_facts") or []),
        list(room_explicit.get("required_room_facts") or []),
    )
    resolved["allowed_but_not_required"] = _merge_string_lists(
        list(room_legacy.get("allowed_but_not_required") or []),
        list(room_explicit.get("allowed_but_not_required") or []),
    )
    resolved["soft_zone_context"] = _merge_string_lists(
        _legacy_zone_soft_context(zone_payload),
        list(zone_explicit.get("soft_zone_context") or []),
    )
    resolved["soft_area_context"] = _merge_string_lists(
        [_normalize_optional_string((area_payload or {}).get("name")) or ""] if isinstance(area_payload, Mapping) else [],
        list(area_explicit.get("soft_area_context") or []),
    )
    resolved["soft_room_context"] = _merge_string_lists(
        list(room_legacy.get("soft_room_context") or []),
        list(zone_explicit.get("soft_room_context") or []),
        list(area_explicit.get("soft_room_context") or []),
        list(room_explicit.get("soft_room_context") or []),
    )
    resolved["forbidden_features"] = _merge_string_lists(
        list(zone_explicit.get("forbidden_features") or []),
        list(area_explicit.get("forbidden_features") or []),
        list(room_explicit.get("forbidden_features") or []),
    )
    resolved["interactive_objects"] = _merge_string_lists(
        list(zone_explicit.get("interactive_objects") or []),
        list(area_explicit.get("interactive_objects") or []),
        list(room_explicit.get("interactive_objects") or []),
    )

    normalized_allowed_exits = _normalize_allowed_exits(
        list(room_explicit.get("allowed_exits") or []) or list(room_legacy.get("allowed_exits") or []),
        "resolved.allowed_exits",
    )
    resolved["allowed_exits"] = normalized_allowed_exits

    return resolved