from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from world.builder.schemas.zone_schema_v1 import ZONE_SCHEMA_VERSION, get_zone_registry_path, normalize_zone_id, validate_zone_registry


BUILDER_ZONE_SERVICE_AVAILABLE = False

try:
    from evennia.objects.models import ObjectDB
except Exception:  # pragma: no cover - optional builder dependency guard
    ObjectDB = None
else:
    BUILDER_ZONE_SERVICE_AVAILABLE = True


def _require_builder_service() -> None:
    if not BUILDER_ZONE_SERVICE_AVAILABLE:
        raise RuntimeError("Builder zone service is unavailable.")


def _normalize_registry(data: dict) -> dict:
    validate_zone_registry(data)
    normalized_zones = {}
    for zone_id, zone in dict(data.get("zones") or {}).items():
        normalized_zone_id = normalize_zone_id(zone_id)
        area = str(zone.get("area") or normalized_zone_id).strip() or normalized_zone_id
        rooms = {}
        for room_id, room in dict(zone.get("rooms") or {}).items():
            normalized_room_id = str(room_id or "").strip()
            if not normalized_room_id:
                continue
            room_payload = dict(room or {})
            rooms[normalized_room_id] = {
                "id": str(room_payload.get("id", normalized_room_id) or normalized_room_id),
                "name": str(room_payload.get("name", normalized_room_id) or normalized_room_id),
            }
        normalized_zones[normalized_zone_id] = {
            "name": str(zone.get("name") or normalized_zone_id),
            "area": area,
            "rooms": rooms,
        }
    return {"version": ZONE_SCHEMA_VERSION, "zones": normalized_zones}


def load_zone_registry() -> dict:
    _require_builder_service()
    registry_path = get_zone_registry_path()
    if not registry_path.exists():
        return {"version": ZONE_SCHEMA_VERSION, "zones": {}}
    with registry_path.open("r", encoding="utf-8") as registry_file:
        data = json.load(registry_file)
    return _normalize_registry(data)


def save_zone_registry(data: dict) -> None:
    _require_builder_service()
    normalized_registry = _normalize_registry(data)
    registry_path = get_zone_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
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


def _titleize_zone_id(zone_id: str) -> str:
    return str(zone_id or "").replace("_", " ").strip().title() or "Untitled Zone"


def _discover_live_zone_rooms() -> dict[str, dict]:
    zones: dict[str, dict] = {}
    for room in ObjectDB.objects.filter(db_location__isnull=True, db_typeclass_path="typeclasses.rooms.Room").order_by("id"):
        builder_id = str(getattr(getattr(room, "db", None), "builder_id", "") or "").strip()
        if not builder_id:
            continue
        raw_zone_id = getattr(getattr(room, "db", None), "zone_id", None) or getattr(getattr(room, "db", None), "zone", None) or getattr(getattr(room, "db", None), "area_id", None)
        if raw_zone_id in (None, ""):
            continue
        zone_id = normalize_zone_id(raw_zone_id)
        zone_entry = zones.setdefault(zone_id, {"name": _titleize_zone_id(zone_id), "area": zone_id, "rooms": {}})
        zone_entry["rooms"][builder_id] = {
            "id": builder_id,
            "name": str(getattr(room, "key", builder_id) or builder_id),
        }
    return zones


def list_zones() -> dict[str, dict]:
    _require_builder_service()
    registry = load_zone_registry()
    zones = dict(registry.get("zones") or {})
    live_zones = _discover_live_zone_rooms()
    for zone_id, live_zone in live_zones.items():
        if zone_id not in zones:
            zones[zone_id] = live_zone
            continue
        merged_zone = dict(zones[zone_id])
        merged_zone.setdefault("name", live_zone.get("name") or _titleize_zone_id(zone_id))
        merged_zone.setdefault("area", live_zone.get("area") or zone_id)
        merged_rooms = dict(merged_zone.get("rooms") or {})
        merged_rooms.update(dict(live_zone.get("rooms") or {}))
        merged_zone["rooms"] = dict(sorted(merged_rooms.items(), key=lambda entry: entry[0]))
        zones[zone_id] = merged_zone
    return dict(sorted(zones.items(), key=lambda entry: entry[0]))


def get_zone(zone_id: str) -> dict | None:
    normalized_zone_id = normalize_zone_id(zone_id)
    zones = list_zones()
    zone = zones.get(normalized_zone_id)
    if zone is None:
        return None
    return {
        "zone_id": normalized_zone_id,
        "name": str(zone.get("name") or _titleize_zone_id(normalized_zone_id)),
        "area": str(zone.get("area") or normalized_zone_id),
        "rooms": dict(zone.get("rooms") or {}),
    }


def require_zone(zone_id: str) -> dict:
    zone = get_zone(zone_id)
    if zone is None:
        raise ValueError(f"Unknown zone_id: {zone_id}")
    return zone


def create_zone(zone_id: str, name: str, area: str | None = None) -> dict:
    _require_builder_service()
    normalized_zone_id = normalize_zone_id(zone_id)
    normalized_name = str(name or "").strip()
    normalized_area = str(area or normalized_zone_id).strip() or normalized_zone_id
    if not normalized_name:
        raise ValueError("name must be a non-empty string.")
    registry = load_zone_registry()
    zones = dict(registry.get("zones") or {})
    if normalized_zone_id in zones:
        raise ValueError(f"duplicate zone_id: {normalized_zone_id}")
    zones[normalized_zone_id] = {"name": normalized_name, "area": normalized_area, "rooms": {}}
    save_zone_registry({"version": ZONE_SCHEMA_VERSION, "zones": zones})
    return {
        "zone_id": normalized_zone_id,
        "name": normalized_name,
        "area": normalized_area,
        "rooms": {},
    }