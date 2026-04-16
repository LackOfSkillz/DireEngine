from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import re


ZONE_SCHEMA_VERSION = "v1"
ZONE_ID_RE = re.compile(r"^[a-z0-9_]+$")


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _require_type(value: object, expected_type: type, label: str) -> None:
    if not isinstance(value, expected_type):
        raise ValueError(f"{label} must be of type {expected_type.__name__}.")


def _require_non_empty_string(value: object, label: str) -> str:
    _require_type(value, str, label)
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must be a non-empty string.")
    return normalized


def normalize_zone_id(value: object) -> str:
    normalized = _require_non_empty_string(value, "zone_id").lower().replace(" ", "_")
    if not ZONE_ID_RE.match(normalized):
        raise ValueError("zone_id must contain only lowercase letters, numbers, and underscores.")
    return normalized


def validate_zone_entry(zone_id: str, zone: dict) -> None:
    payload = _require_mapping(zone, f"zones['{zone_id}']")
    _require_non_empty_string(payload.get("name"), f"zones['{zone_id}'].name")
    rooms = payload.get("rooms")
    _require_type(rooms, dict, f"zones['{zone_id}'].rooms")
    for room_id, room in rooms.items():
        _require_type(room_id, str, f"zones['{zone_id}'].rooms key")
        room_payload = _require_mapping(room, f"zones['{zone_id}'].rooms['{room_id}']")
        if "id" in room_payload:
            _require_type(room_payload.get("id"), str, f"zones['{zone_id}'].rooms['{room_id}'].id")
        if "name" in room_payload:
            _require_type(room_payload.get("name"), str, f"zones['{zone_id}'].rooms['{room_id}'].name")


def validate_zone_registry(data: dict) -> None:
    payload = _require_mapping(data, "zone registry")
    if payload.get("version") != ZONE_SCHEMA_VERSION:
        raise ValueError(f"zone registry version must be {ZONE_SCHEMA_VERSION}.")
    zones = payload.get("zones")
    _require_type(zones, dict, "zones")
    for zone_id, zone in zones.items():
        normalized_zone_id = normalize_zone_id(zone_id)
        if normalized_zone_id != zone_id:
            raise ValueError(f"zone id '{zone_id}' is not normalized.")
        validate_zone_entry(zone_id, zone)


def get_zone_registry_path() -> Path:
    return Path(__file__).resolve().parent.parent / "zones" / "zone_registry_v1.json"