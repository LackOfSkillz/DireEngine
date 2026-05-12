from __future__ import annotations

from collections.abc import Mapping, Sequence


ZONE_TYPES = {
    "outdoor_city",
    "wilderness",
    "interior_small",
    "interior_medium",
    "interior_large",
    "transit",
}

OUTDOOR_REQUIRED_KEYS = ("streets", "intersections", "districts", "landmarks", "gates", "doorway_rooms")
WILDERNESS_REQUIRED_KEYS = ("trails", "rivers", "named_areas", "ranges", "landmarks", "doorway_rooms")
INTERIOR_LARGE_REQUIRED_KEYS = ("halls", "wings", "floors", "named_chambers", "exits_to_parent")
INTERIOR_SMALL_REQUIRED_KEYS = ("exits_to_parent",)
TRANSIT_REQUIRED_KEYS = ("routes", "waypoints", "doorway_rooms")

ZONE_TYPE_SPECS = {
    "outdoor_city": {
        "streets": {"room_lists": ("rooms",)},
        "intersections": {"room_lists": ("rooms",)},
        "districts": {"room_lists": ("rooms",)},
        "landmarks": {"room_lists": ("visible_from_rooms", "rooms")},
        "gates": {"room_fields": ("room",)},
        "doorway_rooms": {"room_fields": ("parent_room",), "room_lists": ("rooms",)},
    },
    "wilderness": {
        "trails": {"room_lists": ("rooms",)},
        "rivers": {"room_lists": ("rooms",)},
        "named_areas": {"room_lists": ("rooms",)},
        "ranges": {"room_lists": ("rooms",)},
        "landmarks": {"room_lists": ("visible_from_rooms", "rooms")},
        "doorway_rooms": {"room_fields": ("parent_room",), "room_lists": ("rooms",)},
    },
    "interior_medium": {
        "halls": {"room_lists": ("rooms",)},
        "wings": {"room_lists": ("rooms",)},
        "floors": {"room_lists": ("rooms",)},
        "named_chambers": {"room_fields": ("room",)},
        "exits_to_parent": {"room_fields": ("child_room",)},
    },
    "interior_large": {
        "halls": {"room_lists": ("rooms",)},
        "wings": {"room_lists": ("rooms",)},
        "floors": {"room_lists": ("rooms",)},
        "named_chambers": {"room_fields": ("room",)},
        "exits_to_parent": {"room_fields": ("child_room",)},
    },
    "interior_small": {
        "exits_to_parent": {"room_fields": ("child_room",)},
    },
    "transit": {
        "routes": {"room_lists": ("rooms",)},
        "waypoints": {"room_fields": ("room",), "room_lists": ("rooms",)},
        "doorway_rooms": {"room_fields": ("parent_room",), "room_lists": ("rooms",)},
    },
}


def normalize_zone_type(value: object) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def validate_zone_type(value: object) -> str:
    normalized = normalize_zone_type(value)
    if not normalized:
        raise ValueError("zone_type is required.")
    if normalized not in ZONE_TYPES:
        raise ValueError(f"zone_type must be one of: {', '.join(sorted(ZONE_TYPES))}")
    return normalized


def empty_geographic_structure(zone_type: str) -> dict[str, object]:
    normalized_zone_type = validate_zone_type(zone_type)
    if normalized_zone_type == "outdoor_city":
        keys = OUTDOOR_REQUIRED_KEYS
    elif normalized_zone_type == "wilderness":
        keys = WILDERNESS_REQUIRED_KEYS
    elif normalized_zone_type in {"interior_medium", "interior_large"}:
        keys = INTERIOR_LARGE_REQUIRED_KEYS
    elif normalized_zone_type == "interior_small":
        keys = INTERIOR_SMALL_REQUIRED_KEYS
    else:
        keys = TRANSIT_REQUIRED_KEYS
    return {key: [] for key in keys}


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _require_sequence(data: object, label: str) -> Sequence:
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise ValueError(f"{label} must be a list.")
    return data


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_string_list(value: object, label: str) -> list[str]:
    if value in (None, ""):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _require_sequence(value, label):
        text = _normalize_string(item)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _validate_room_refs(room_refs: object, valid_room_ids: set[str], label: str) -> list[str]:
    normalized = _normalize_string_list(room_refs, label)
    missing = [room_id for room_id in normalized if room_id not in valid_room_ids]
    if missing:
        raise ValueError(f"{label} references missing rooms: {', '.join(missing)}")
    return normalized


def _normalize_entry(payload: object, label: str) -> dict[str, object]:
    return dict(_require_mapping(payload, label))


def _normalize_named_room_collection(
    entries: object,
    valid_room_ids: set[str],
    label: str,
    *,
    room_fields: Sequence[str] = (),
    room_lists: Sequence[str] = (),
) -> list[dict[str, object]]:
    normalized_entries: list[dict[str, object]] = []
    for index, entry in enumerate(_require_sequence(entries, label)):
        payload = _normalize_entry(entry, f"{label}[{index}]")
        normalized_payload = dict(payload)
        for room_field in room_fields:
            room_id = _normalize_string(payload.get(room_field))
            if not room_id:
                raise ValueError(f"{label}[{index}].{room_field} is required.")
            if room_id not in valid_room_ids:
                raise ValueError(f"{label}[{index}].{room_field} references missing room '{room_id}'.")
            normalized_payload[room_field] = room_id
        for room_list in room_lists:
            normalized_payload[room_list] = _validate_room_refs(
                payload.get(room_list),
                valid_room_ids,
                f"{label}[{index}].{room_list}",
            )
        normalized_entries.append(normalized_payload)
    return normalized_entries


def validate_geographic_structure(zone_type: object, data: object, room_ids: Sequence[str]) -> dict[str, object]:
    normalized_zone_type = validate_zone_type(zone_type)
    valid_room_ids = {str(room_id or "").strip() for room_id in room_ids if str(room_id or "").strip()}
    payload = dict(data or {}) if isinstance(data, Mapping) else {}
    normalized = empty_geographic_structure(normalized_zone_type)
    normalized.update(payload)

    for key, spec in ZONE_TYPE_SPECS[normalized_zone_type].items():
        normalized[key] = _normalize_named_room_collection(
            normalized.get(key, []),
            valid_room_ids,
            f"geographic_structure.{key}",
            room_fields=spec.get("room_fields", ()),
            room_lists=spec.get("room_lists", ()),
        )

    return normalized