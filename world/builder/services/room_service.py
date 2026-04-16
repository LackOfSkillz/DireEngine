from __future__ import annotations

from collections.abc import Mapping


BUILDER_ROOM_SERVICE_AVAILABLE = False

try:
    from evennia.utils.create import create_object
    from evennia.utils.search import search_tag
    from typeclasses.rooms import Room
except Exception:  # pragma: no cover - optional builder dependency guard
    create_object = None
    search_tag = None
    Room = None
else:
    BUILDER_ROOM_SERVICE_AVAILABLE = True


_ROOM_TAG_CATEGORY = "builder_room_id"
_ZONE_ROOM_TAG_CATEGORY = "builder_zone_room_id"
_ALLOWED_UPDATE_FIELDS = {"name", "description", "desc", "map_x", "map_y", "map_layer", "area_id", "room_type", "zone_id", "no_npc_wander", "guild_area", "npc_boundary"}


def _require_builder_runtime() -> None:
    if not BUILDER_ROOM_SERVICE_AVAILABLE:
        raise RuntimeError("Builder room service is unavailable because the Evennia runtime could not be imported.")


def _require_mapping(data: object, label: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{label} must be an int.")
    return int(value)


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a bool.")
    return bool(value)


def _resolve_zone_id(data: Mapping, current=None) -> str:
    raw_zone_id = data.get("zone_id", None)
    if raw_zone_id not in (None, ""):
        return _require_string(raw_zone_id, "zone_id")
    if data.get("area_id") not in (None, ""):
        return _require_string(data.get("area_id"), "area_id")
    if data.get("region") not in (None, ""):
        return _require_string(data.get("region"), "region")
    if current not in (None, ""):
        return _require_string(current, "zone_id")
    return "default_region"


def _zone_room_tag(zone_id: str, room_id: str) -> str:
    return "%s:%s" % [_require_string(zone_id, "zone_id"), _require_string(room_id, "room_id")]


def _sync_room_tags(room) -> None:
    builder_id = str(getattr(getattr(room, "db", None), "builder_id", "") or "").strip()
    zone_id = str(getattr(getattr(room, "db", None), "zone_id", "") or getattr(getattr(room, "db", None), "zone", "") or getattr(getattr(room, "db", None), "area_id", "") or "").strip()
    if not builder_id:
        return
    room.tags.clear(category=_ROOM_TAG_CATEGORY)
    room.tags.add(builder_id, category=_ROOM_TAG_CATEGORY)
    room.tags.clear(category=_ZONE_ROOM_TAG_CATEGORY)
    if zone_id:
        room.tags.add(_zone_room_tag(zone_id, builder_id), category=_ZONE_ROOM_TAG_CATEGORY)


def _apply_room_fields(room, data: Mapping) -> None:
    if "name" in data:
        room.key = _require_string(data.get("name"), "name")
    if "description" in data:
        room.db.desc = _require_string(data.get("description"), "description")
    elif "desc" in data:
        room.db.desc = _require_string(data.get("desc"), "desc")
    if "map_x" in data:
        room.db.map_x = _require_int(data.get("map_x"), "map_x")
    if "map_y" in data:
        room.db.map_y = _require_int(data.get("map_y"), "map_y")
    if "map_layer" in data:
        room.db.map_layer = _require_int(data.get("map_layer"), "map_layer")
    if "area_id" in data:
        room.db.area_id = _require_string(data.get("area_id"), "area_id")
    if "region" in data:
        room.db.region = _require_string(data.get("region"), "region")
    zone_id = _resolve_zone_id(data, current=getattr(getattr(room, "db", None), "zone_id", None) or getattr(getattr(room, "db", None), "zone", None))
    room.db.zone_id = zone_id
    room.db.zone = zone_id
    if "room_type" in data:
        room.db.room_type = _require_string(data.get("room_type"), "room_type").lower()
    if "no_npc_wander" in data:
        room.db.no_npc_wander = _require_bool(data.get("no_npc_wander"), "no_npc_wander")
    if "guild_area" in data:
        room.db.guild_area = _require_bool(data.get("guild_area"), "guild_area")
    if "npc_boundary" in data:
        room.db.npc_boundary = _require_bool(data.get("npc_boundary"), "npc_boundary")


def normalize_room(room) -> dict[str, object]:
    return {
        "id": str(getattr(getattr(room, "db", None), "builder_id", "") or ""),
        "name": str(getattr(room, "key", "") or ""),
        "room_type": str(getattr(getattr(room, "db", None), "room_type", "") or "room"),
        "zone_id": str(getattr(getattr(room, "db", None), "zone_id", "") or getattr(getattr(room, "db", None), "zone", "") or ""),
    }


def get_room(room_id, zone_id=None):
    _require_builder_runtime()
    normalized_room_id = _require_string(room_id, "room_id")
    normalized_zone_id = str(zone_id or "").strip()
    if normalized_zone_id:
        zoned_matches = [
            candidate
            for candidate in list(search_tag(_zone_room_tag(normalized_zone_id, normalized_room_id), category=_ZONE_ROOM_TAG_CATEGORY) or [])
            if getattr(candidate, "destination", None) is None
        ]
        if zoned_matches:
            return zoned_matches[0]
    matches = [candidate for candidate in list(search_tag(normalized_room_id, category=_ROOM_TAG_CATEGORY) or []) if getattr(candidate, "destination", None) is None]
    return matches[0] if matches else None


def create_room(data: dict):
    _require_builder_runtime()
    payload = _require_mapping(data, "room data")

    builder_id = _require_string(payload.get("id"), "id")
    _require_string(payload.get("name"), "name")
    _require_string(payload.get("description"), "description")
    _require_int(payload.get("map_x"), "map_x")
    _require_int(payload.get("map_y"), "map_y")

    zone_id = _resolve_zone_id(payload)
    room = get_room(builder_id, zone_id=zone_id)
    if room is None:
        room = get_room(builder_id)
    if room is None:
        room = create_object(Room, key=payload["name"])

    _apply_room_fields(room, payload)
    room.db.map_layer = _require_int(payload.get("map_layer", 0), "map_layer")
    room.db.builder_id = builder_id
    room.db.room_type = str(getattr(getattr(room, "db", None), "room_type", "") or payload.get("room_type") or "room").strip().lower() or "room"
    if payload.get("area_id") not in (None, ""):
        room.db.area_id = _require_string(payload.get("area_id"), "area_id")
    room.home = room.home or room
    _sync_room_tags(room)
    return room


def update_room(room, data: dict):
    _require_builder_runtime()
    if room is None:
        raise ValueError("room is required.")

    payload = _require_mapping(data, "room update data")
    unknown_fields = sorted(set(payload.keys()) - _ALLOWED_UPDATE_FIELDS)
    if unknown_fields:
        raise ValueError(f"Unsupported room update fields: {', '.join(unknown_fields)}")

    _apply_room_fields(room, payload)
    _sync_room_tags(room)
    return room