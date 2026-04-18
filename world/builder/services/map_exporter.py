from __future__ import annotations

import re
from collections.abc import Mapping


BUILDER_MAP_EXPORT_AVAILABLE = False

try:
    from evennia.objects.models import ObjectDB
    from evennia.utils.search import search_tag

    from world.builder.schemas.map_schema_v1 import validate_map_schema
    from world.builder.services import zone_service
except Exception:  # pragma: no cover - optional builder dependency guard
    ObjectDB = None
    search_tag = None
    validate_map_schema = None
    zone_service = None
else:
    BUILDER_MAP_EXPORT_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not BUILDER_MAP_EXPORT_AVAILABLE:
        raise RuntimeError("Builder map exporter is unavailable because the Evennia runtime could not be imported.")


def _infer_object_type(obj) -> str:
    db = getattr(obj, "db", None)
    typeclass_path = str(getattr(obj, "typeclass_path", "") or "")
    if bool(getattr(db, "is_npc", False)) or "typeclasses.npcs" in typeclass_path:
        return "npc"
    if bool(getattr(db, "is_container", False)) or bool(getattr(db, "is_surface", False)):
        return "container"
    return "item"


def _normalized_object_attributes(obj) -> dict:
    raw_attributes = getattr(getattr(obj, "db", None), "builder_attributes", {}) or {}
    if not isinstance(raw_attributes, Mapping):
        raw_attributes = {}
    normalized = {}
    for raw_key, raw_value in dict(raw_attributes).items():
        attribute_name = str(raw_key or "").strip().lower()
        if not attribute_name or not isinstance(raw_value, (int, float)):
            continue
        normalized[attribute_name] = raw_value
    return normalized


def _normalized_object_flags(obj) -> list[str]:
    raw_flags = getattr(getattr(obj, "db", None), "builder_flags", []) or []
    if not isinstance(raw_flags, (list, tuple, set)):
        raw_flags = []
    normalized: list[str] = []
    for raw_flag in list(raw_flags):
        flag_name = str(raw_flag or "").strip().lower()
        if flag_name and flag_name not in normalized:
            normalized.append(flag_name)
    if bool(getattr(getattr(obj, "db", None), "aggressive", False)) and "aggressive" not in normalized:
        normalized.append("aggressive")
    if bool(getattr(getattr(obj, "db", None), "patrol", False)) and "patrol" not in normalized:
        normalized.append("patrol")
    return normalized


def _object_item_kind(obj, object_type: str) -> str:
    explicit_item_kind = str(getattr(getattr(obj, "db", None), "builder_item_kind", "") or "").strip().lower()
    if explicit_item_kind:
        return explicit_item_kind
    if object_type == "container":
        return "container"
    return "item"


def _normalize_content_object(obj, depth: int = 0) -> dict:
    object_type = _infer_object_type(obj)
    placement_type = str(getattr(getattr(obj, "db", None), "placement_type", "") or "container")
    placement_relation = str(getattr(getattr(obj, "db", None), "placement_relation", "") or "in")
    is_surface = bool(getattr(getattr(obj, "db", None), "is_surface", False))
    children = []
    if depth < 8:
        for child in list(getattr(obj, "contents", []) or []):
            if getattr(child, "destination", None) is not None:
                continue
            children.append(_normalize_content_object(child, depth + 1))
    return {
        "id": str(getattr(obj, "id", "") or ""),
        "object_id": str(getattr(obj, "id", "") or ""),
        "name": str(getattr(obj, "key", "") or ""),
        "description": str(getattr(getattr(obj, "db", None), "desc", "") or ""),
        "type": object_type,
        "item_kind": _object_item_kind(obj, object_type),
        "template_id": str(getattr(getattr(obj, "db", None), "template_id", "") or ""),
        "attributes": _normalized_object_attributes(obj),
        "flags": _normalized_object_flags(obj),
        "weight": float(getattr(getattr(obj, "db", None), "weight", 0.0) or 0.0),
        "value": float(getattr(getattr(obj, "db", None), "value", 0.0) or 0.0),
        "is_surface": is_surface,
        "placement_type": placement_type,
        "placement_relation": placement_relation,
        "contents": children,
    }


def _room_export_id(room) -> str:
    builder_id = str(getattr(getattr(room, "db", None), "builder_id", "") or "").strip()
    return builder_id or str(getattr(room, "id", "") or "")


def _room_zone_id(room, fallback: str = "") -> str:
    return str(getattr(getattr(room, "db", None), "zone_id", "") or getattr(getattr(room, "db", None), "zone", "") or getattr(getattr(room, "db", None), "area_id", "") or fallback)


def _exit_aliases(exit_obj) -> list[str]:
    aliases = getattr(exit_obj, "aliases", None)
    if aliases is None or not hasattr(aliases, "all"):
        return []
    normalized: list[str] = []
    for raw_alias in list(aliases.all() or []):
        alias = str(raw_alias or "").strip()
        if alias and alias not in normalized:
            normalized.append(alias)
    return normalized


_NON_ALNUM_TAG_RE = re.compile(r"[^a-z0-9]+")


def _append_semantic_tag(semantic_tags: list[str], raw_value) -> None:
    normalized = _NON_ALNUM_TAG_RE.sub("_", str(raw_value or "").strip().lower()).strip("_")
    if normalized and normalized not in semantic_tags:
        semantic_tags.append(normalized)


def _is_guild_marker(tag: str) -> bool:
    normalized = str(tag or "").strip().lower()
    if not normalized:
        return False
    return (
        normalized == "guild"
        or normalized.startswith("guild_access_")
        or normalized.startswith("guild_")
        or normalized.startswith("poi_guild_")
        or normalized.endswith("_guild")
        or normalized.endswith("_guildhall")
    )


def _prefetch_room_tags(rooms: list) -> list:
    room_ids = [int(getattr(room, "id", 0) or 0) for room in list(rooms or []) if getattr(room, "id", None) is not None]
    if not room_ids:
        return []
    prefetched_rooms = ObjectDB.objects.filter(id__in=room_ids).prefetch_related("db_tags")
    rooms_by_id = {int(getattr(room, "id", 0) or 0): room for room in prefetched_rooms}
    return [rooms_by_id[room_id] for room_id in room_ids if room_id in rooms_by_id]


def _semantic_room_tags(room) -> list[str]:
    semantic_tags: list[str] = []
    for tag in list(getattr(room, "db_tags", None).all() or []):
        raw_tag = str(getattr(tag, "db_key", "") or "").strip()
        normalized_category = str(getattr(tag, "db_category", "") or "").strip().lower()
        if normalized_category.endswith("_node") and "__" in raw_tag:
            _, raw_tag = raw_tag.split("__", 1)
        _append_semantic_tag(semantic_tags, raw_tag)

    _append_semantic_tag(semantic_tags, getattr(getattr(room, "db", None), "guild_tag", None))

    if any(_is_guild_marker(tag) for tag in semantic_tags):
        _append_semantic_tag(semantic_tags, "guild")
    if any("training" in tag for tag in semantic_tags):
        _append_semantic_tag(semantic_tags, "training")
    if any("bank" in tag for tag in semantic_tags):
        _append_semantic_tag(semantic_tags, "bank")
    if any("shop" in tag for tag in semantic_tags):
        _append_semantic_tag(semantic_tags, "shop")

    return semantic_tags


def _room_type(room, semantic_tags: list[str]) -> str:
    room_type = str(getattr(getattr(room, "db", None), "room_type", "") or "").strip().lower()
    if room_type:
        return room_type
    return "room"


def _append_room_npc(npcs: list[dict], obj, room_id: str) -> None:
    if _infer_object_type(obj) != "npc":
        return
    npcs.append(
        {
            "id": str(getattr(obj, "id", "") or ""),
            "room_id": room_id,
            "name": str(getattr(obj, "key", "") or ""),
        }
    )


def _room_occupants_by_id(rooms: list) -> dict[int, list]:
    room_object_map = {
        int(getattr(room, "id", 0) or 0): room
        for room in list(rooms or [])
        if getattr(room, "id", None) is not None
    }
    if not room_object_map:
        return {}
    occupants_by_room_id: dict[int, list] = {room_object_id: [] for room_object_id in room_object_map.keys()}
    for obj in ObjectDB.objects.filter(db_location__in=list(room_object_map.values())).order_by("id"):
        location = getattr(obj, "location", None)
        room_object_id = int(getattr(location, "id", 0) or 0)
        if room_object_id not in occupants_by_room_id:
            continue
        if getattr(obj, "destination", None) is not None:
            continue
        occupants_by_room_id[room_object_id].append(obj)
    return occupants_by_room_id


def _rooms_for_zone(zone_id: str) -> list:
    rooms_by_zone_id = []
    for candidate in ObjectDB.objects.filter(db_location__isnull=True).order_by("id"):
        typeclass_path = str(getattr(candidate, "db_typeclass_path", "") or "")
        if not typeclass_path.startswith("typeclasses.rooms"):
            continue
        if str(_room_zone_id(candidate, fallback="") or "").strip() != zone_id:
            continue
        if not str(getattr(getattr(candidate, "db", None), "builder_id", "") or "").strip():
            continue
        rooms_by_zone_id.append(candidate)
    if rooms_by_zone_id:
        return rooms_by_zone_id

    if search_tag is None:
        return []

    tagged_objects = list(search_tag(zone_id, category="build"))
    zone_rooms = [
        obj
        for obj in tagged_objects
        if getattr(obj, "destination", None) is None
        and getattr(obj, "id", None) is not None
        and str(getattr(obj, "db_typeclass_path", "") or "").startswith("typeclasses.rooms")
    ]
    ordered_rooms = sorted(zone_rooms, key=lambda room: getattr(room, "id", 0))
    return _prefetch_room_tags(ordered_rooms)


def export_map(area_id: str) -> dict:
    _require_builder_runtime()
    normalized_area_id = str(area_id or "").strip()
    if not normalized_area_id:
        raise ValueError("area_id is required.")

    rooms = []
    npcs = []
    rooms_by_id = _rooms_for_zone(normalized_area_id)
    if not rooms_by_id and zone_service is not None:
        zone_service.require_zone(normalized_area_id)
    export_ids = {_room_export_id(room) for room in rooms_by_id}
    occupants_by_room_id = _room_occupants_by_id(rooms_by_id)

    for room in rooms_by_id:
        semantic_tags = _semantic_room_tags(room)
        room_data = {
            "id": _room_export_id(room),
            "object_id": str(getattr(room, "id", "") or ""),
            "name": str(getattr(room, "key", "") or ""),
            "description": str(getattr(getattr(room, "db", None), "desc", "") or ""),
            "map_x": int(getattr(getattr(room, "db", None), "map_x", 0) or 0),
            "map_y": int(getattr(getattr(room, "db", None), "map_y", 0) or 0),
            "map_layer": int(getattr(getattr(room, "db", None), "map_layer", 0) or 0),
            "zone_id": str(getattr(getattr(room, "db", None), "zone_id", "") or getattr(getattr(room, "db", None), "zone", "") or normalized_area_id),
            "room_type": _room_type(room, semantic_tags),
            "tags": semantic_tags,
            "no_npc_wander": bool(getattr(getattr(room, "db", None), "no_npc_wander", False)),
            "guild_area": bool(getattr(getattr(room, "db", None), "guild_area", False)),
            "npc_boundary": bool(getattr(getattr(room, "db", None), "npc_boundary", False)),
            "exits": {},
            "exit_details": [],
            "contents": [],
        }
        for candidate in occupants_by_room_id.get(int(getattr(room, "id", 0) or 0), []):
            room_data["contents"].append(_normalize_content_object(candidate))
            _append_room_npc(npcs, candidate, room_data["id"])
        for candidate in list(getattr(room, "contents", []) or []):
            destination = getattr(candidate, "destination", None)
            if destination is None:
                continue
            target_room_id = _room_export_id(destination)
            target_zone_id = _room_zone_id(destination, fallback=normalized_area_id).strip() or normalized_area_id
            if not target_room_id:
                continue
            direction = str(getattr(candidate, "key", "") or "")
            if target_zone_id == normalized_area_id and target_room_id in export_ids:
                room_data["exits"][direction] = {
                    "zone_id": target_zone_id,
                    "room_id": target_room_id,
                }
            room_data["exit_details"].append(
                {
                    "id": str(getattr(candidate, "id", "") or ""),
                    "direction": direction,
                    "target": {
                        "zone_id": target_zone_id,
                        "room_id": target_room_id,
                    },
                    "label": str(getattr(getattr(candidate, "db", None), "exit_display_name", "") or ""),
                    "aliases": _exit_aliases(candidate),
                }
            )
        room_data["exit_details"].sort(key=lambda entry: (str(entry.get("direction", "") or ""), str(entry.get("id", "") or "")))
        rooms.append(room_data)

    exported = {"area_id": normalized_area_id, "zone_id": normalized_area_id, "rooms": rooms, "npcs": npcs}
    validate_map_schema(exported)
    return exported