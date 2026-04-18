from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

import yaml
from django.utils.text import slugify

from evennia.objects.models import ObjectDB

from world.builder.services.map_exporter import _rooms_for_zone


SCHEMA_VERSION = "v1"
ROOM_STATE_TAG_CATEGORY = "room_state"
DEFAULT_EXIT_TYPECLASS = "typeclasses.exits.Exit"
ALLOWED_DIRECTIONS = {
    "north",
    "south",
    "east",
    "west",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "up",
    "down",
}


def _normalize_stateful_descs(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_text in value.items():
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        normalized[key] = str(raw_text or "")
    return normalized


def _normalize_details(value) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_text in dict(value).items():
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        normalized[key] = str(raw_text or "")
    return normalized


def _normalize_room_states(room) -> list[str]:
    tag_handler = getattr(room, "tags", None)
    if not tag_handler:
        return []
    states = tag_handler.get(category=ROOM_STATE_TAG_CATEGORY, return_list=True) or []
    return sorted({str(state or "").strip().lower() for state in states if str(state or "").strip()})


def _extract_stateful_descs(room) -> dict[str, str]:
    attributes = getattr(room, "attributes", None)
    backend = getattr(room, "db_attributes", None)
    if backend is None:
        return {}
    stateful_descs: dict[str, str] = {}
    for attr in backend.filter(db_key__startswith="desc_").order_by("db_key"):
        state = str(getattr(attr, "key", "") or "")[5:].strip().lower()
        if not state:
            continue
        value = getattr(attr, "value", None)
        if value is None and attributes:
            value = attributes.get(str(getattr(attr, "key", "") or ""), default="")
        stateful_descs[state] = str(value or "")
    return stateful_descs


def _extract_ambient(room) -> dict:
    db = getattr(room, "db", None)
    raw_rate = getattr(db, "room_message_rate", 0) if db else 0
    try:
        rate = int(raw_rate or 0)
    except (TypeError, ValueError):
        rate = 0
    raw_messages = getattr(db, "room_messages", []) if db else []
    messages = [str(message or "") for message in list(raw_messages or []) if str(message or "")]
    return {
        "rate": rate,
        "messages": messages,
    }


def _zones_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlddata" / "zones"


def _titleize_zone_id(zone_id: str) -> str:
    return str(zone_id or "").replace("_", " ").strip().title() or "Untitled Zone"


def _ensure_world_id(obj) -> str:
    world_id = str(getattr(getattr(obj, "db", None), "world_id", "") or "").strip()
    if not world_id:
        world_id = slugify(str(getattr(obj, "key", "") or "")) or f"obj_{getattr(obj, 'id', 'unknown')}"
        obj.db.world_id = world_id
    return world_id


def _ensure_unique_world_id(obj, used_ids: set[str]) -> str:
    world_id = _ensure_world_id(obj)
    if world_id in used_ids:
        object_id = int(getattr(obj, "id", 0) or 0)
        world_id = f"{world_id}-{object_id}" if object_id else f"{world_id}-dup"
        obj.db.world_id = world_id
    used_ids.add(world_id)
    return world_id


def _tag_syncable(obj, zone_id: str) -> None:
    obj.tags.add("world_sync")
    obj.tags.add(f"zone:{zone_id}")


def _is_exit(obj) -> bool:
    return bool(getattr(obj, "destination", None))


def _is_npc(obj) -> bool:
    return bool(getattr(getattr(obj, "db", None), "is_npc", False))


def _is_character(obj) -> bool:
    typeclass_path = str(getattr(obj, "db_typeclass_path", "") or "")
    return "typeclasses.characters.Character" in typeclass_path or "typeclasses.npcs.NPC" in typeclass_path or "typeclasses._guard_npc_impl.GuardNPC" in typeclass_path


def _extract_room_data(room) -> dict:
    return {
        "id": _ensure_world_id(room),
        "name": room.key,
        "typeclass": getattr(room, "db_typeclass_path", None),
        "short_desc": getattr(getattr(room, "db", None), "short_desc", None),
        "desc": getattr(getattr(room, "db", None), "desc", None),
        "stateful_descs": _extract_stateful_descs(room),
        "details": _normalize_details(getattr(getattr(room, "db", None), "details", {}) or {}),
        "room_states": _normalize_room_states(room),
        "ambient": _extract_ambient(room),
        "map": {
            "x": getattr(getattr(room, "db", None), "map_x", None),
            "y": getattr(getattr(room, "db", None), "map_y", None),
            "layer": getattr(getattr(room, "db", None), "map_layer", 0) or 0,
        },
        "flags": {
            "safe_zone": bool(getattr(getattr(room, "db", None), "safe_zone", False)),
            "is_shop": bool(getattr(getattr(room, "db", None), "is_shop", False)),
        },
        "exits": {},
        "special_exits": {},
    }


def _extract_npc_placement(obj, room_world_id: str) -> dict:
    return {
        "id": obj.db.world_id,
        "prototype": getattr(getattr(obj, "db", None), "prototype", None),
        "typeclass": getattr(obj, "db_typeclass_path", None),
        "room": room_world_id,
    }


def _extract_exit_data(exit_obj, target_id: str) -> dict:
    db = getattr(exit_obj, "db", None)
    raw_travel_time = getattr(db, "travel_time", 0) if db else 0
    try:
        travel_time = int(raw_travel_time or 0)
    except (TypeError, ValueError):
        travel_time = 0
    return {
        "target": target_id,
        "typeclass": str(getattr(exit_obj, "db_typeclass_path", "") or DEFAULT_EXIT_TYPECLASS),
        "speed": str(getattr(db, "move_speed", "") or "").strip().lower(),
        "travel_time": max(0, travel_time),
    }


def export_zone(zone_id: str) -> dict:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        raise ValueError("zone_id is required.")

    rooms = list(_rooms_for_zone(normalized_zone_id))
    rooms.sort(key=lambda room: (int(getattr(room, "id", 0) or 0), str(getattr(room, "key", "") or "")))
    if not rooms:
        raise ValueError(f"No rooms found for zone '{normalized_zone_id}'.")

    rooms_data = []
    npcs = []
    items = []
    used_ids: set[str] = set()
    seen_item_ids: set[str] = set()
    room_world_ids = {}

    for room in rooms:
        room_world_ids[int(getattr(room, "id", 0) or 0)] = _ensure_unique_world_id(room, used_ids)

    def walk_items(obj, room_id: str, parent: str | None = None) -> None:
        if _is_exit(obj) or _is_npc(obj) or _is_character(obj):
            return
        if bool(getattr(obj, "has_account", False)):
            return
        item_world_id = _ensure_unique_world_id(obj, used_ids)
        if item_world_id in seen_item_ids:
            return
        seen_item_ids.add(item_world_id)
        _tag_syncable(obj, normalized_zone_id)
        data = {
            "id": item_world_id,
            "prototype": getattr(getattr(obj, "db", None), "prototype", None),
            "typeclass": getattr(obj, "db_typeclass_path", None),
        }
        if parent:
            data["parent"] = parent
        else:
            data["room"] = room_id
        items.append(data)
        for child in list(getattr(obj, "contents", []) or []):
            walk_items(child, room_id, item_world_id)

    for room in rooms:
        room_world_id = room_world_ids[int(getattr(room, "id", 0) or 0)]
        _tag_syncable(room, normalized_zone_id)
        room_data = _extract_room_data(room)
        room_data["id"] = room_world_id

        for obj in sorted(
            list(getattr(room, "contents", []) or []),
            key=lambda entry: (int(getattr(entry, "id", 0) or 0), str(getattr(entry, "key", "") or "")),
        ):
            if _is_exit(obj):
                direction = str(getattr(obj, "key", "") or "").strip().lower()
                target = getattr(obj, "destination", None)
                target_id = room_world_ids.get(int(getattr(target, "id", 0) or 0)) if target else None
                if direction and target_id:
                    target_bucket = "exits" if direction in ALLOWED_DIRECTIONS else "special_exits"
                    room_data[target_bucket][direction] = _extract_exit_data(obj, target_id)
                continue

            if _is_npc(obj):
                _ensure_unique_world_id(obj, used_ids)
                _tag_syncable(obj, normalized_zone_id)
                npcs.append(_extract_npc_placement(obj, room_world_id))
                continue

            if _is_character(obj):
                continue

            walk_items(obj, room_world_id)

        rooms_data.append(room_data)
    room_data["exits"] = dict(sorted(room_data["exits"].items()))
    room_data["special_exits"] = dict(sorted(room_data["special_exits"].items()))

    zone_name = str(getattr(getattr(rooms[0], "db", None), "zone_name", "") or getattr(getattr(rooms[0], "db", None), "zone", "") or _titleize_zone_id(normalized_zone_id))
    return {
        "schema_version": SCHEMA_VERSION,
        "zone_id": normalized_zone_id,
        "name": zone_name,
        "rooms": rooms_data,
        "placements": {
            "npcs": npcs,
            "items": items,
        },
    }


def write_zone_export(zone_id: str) -> Path:
    zone_data = export_zone(zone_id)
    output_path = _zones_dir() / f"{zone_id}.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(zone_data, file_handle, sort_keys=False)
    return output_path