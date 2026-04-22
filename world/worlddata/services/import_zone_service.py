from __future__ import annotations

from pathlib import Path

import yaml

from evennia.objects.models import ObjectDB
from evennia.prototypes.spawner import search_prototype, spawn
from evennia.utils.create import create_object

from server.systems import zone_room_item_assignments, zone_room_npc_assignments, zone_runtime_spawn
from world.builder.services.map_exporter import _rooms_for_zone


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

REVERSE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "northwest": "southeast",
    "southeast": "northwest",
    "southwest": "northeast",
    "up": "down",
    "down": "up",
}

MAP_SPREAD_WARNING_THRESHOLD = 2
GENERIC_OBJECT_TYPECLASS = "typeclasses.objects.Object"
DEFAULT_NPC_TYPECLASS = "typeclasses.npcs.NPC"
DEFAULT_ROOM_TYPECLASS = "typeclasses.rooms_extended.ExtendedDireRoom"
DEFAULT_EXIT_TYPECLASS = "typeclasses.exits.Exit"
DEFAULT_SLOW_EXIT_TYPECLASS = "typeclasses.exits_slow.SlowDireExit"
ROOM_STATE_TAG_CATEGORY = "room_state"


def _normalize_string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_text in value.items():
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        normalized[key] = str(raw_text or "")
    return normalized


def _normalize_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value or "").strip() for value in values if str(value or "").strip()]


def _normalize_exit_spec(raw_value: object) -> dict:
    if isinstance(raw_value, dict):
        target = str(raw_value.get("target") or raw_value.get("room_id") or raw_value.get("target_id") or "").strip()
        typeclass = str(raw_value.get("typeclass") or DEFAULT_EXIT_TYPECLASS).strip() or DEFAULT_EXIT_TYPECLASS
        speed = str(raw_value.get("speed") or "").strip().lower()
        try:
            travel_time = int(raw_value.get("travel_time", 0) or 0)
        except (TypeError, ValueError):
            travel_time = 0
        return {
            "target": target,
            "typeclass": typeclass,
            "speed": speed,
            "travel_time": max(0, travel_time),
        }
    return {
        "target": str(raw_value or "").strip(),
        "typeclass": DEFAULT_EXIT_TYPECLASS,
        "speed": "",
        "travel_time": 0,
    }


def _normalize_special_exit_specs(raw_value: object, room_id: str) -> dict[str, dict]:
    normalized: dict[str, dict] = {}
    for raw_direction, raw_target in dict(raw_value or {}).items():
        direction = str(raw_direction or "").strip().lower()
        if not direction:
            continue
        exit_spec = _normalize_exit_spec(raw_target)
        target_id = exit_spec["target"]
        if not target_id:
            raise ValueError(f"Room '{room_id}' special exit '{direction}' is missing a target.")
        normalized[direction] = {
            "target": target_id,
            "typeclass": exit_spec["typeclass"],
            "speed": exit_spec["speed"],
            "travel_time": exit_spec["travel_time"],
        }
    return normalized


def _normalize_ambient(value: object) -> dict:
    if not isinstance(value, dict):
        return {"rate": 0, "messages": []}
    try:
        rate = int(value.get("rate", 0) or 0)
    except (TypeError, ValueError):
        rate = 0
    return {
        "rate": max(0, rate),
        "messages": _normalize_string_list(value.get("messages") or []),
    }


def _apply_extended_room_fields(room, room_data: dict) -> None:
    room.db.desc = room_data.get("desc") or ""
    stateful_descs = _normalize_string_map(room_data.get("stateful_descs") or {})
    details = _normalize_string_map(room_data.get("details") or {})
    room_states = sorted({state.lower() for state in _normalize_string_list(room_data.get("room_states") or [])})
    ambient = _normalize_ambient(room_data.get("ambient") or {})

    room.db.details = details
    room.db.room_messages = ambient["messages"]
    room.db.room_message_rate = ambient["rate"]

    for attr in list(room.db_attributes.filter(db_key__startswith="desc_")):
        room.attributes.remove(attr.key)
    for state, text in stateful_descs.items():
        room.attributes.add(f"desc_{state}", text)

    room.tags.clear(category=ROOM_STATE_TAG_CATEGORY)
    for state in room_states:
        room.tags.add(state, category=ROOM_STATE_TAG_CATEGORY)

    if ambient["rate"] > 0 and ambient["messages"] and hasattr(room, "start_repeat_broadcast_messages"):
        room.start_repeat_broadcast_messages()


def _zones_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlddata" / "zones"


def _load_zone_yaml(zone_id: str) -> dict:
    file_path = _zones_dir() / f"{zone_id}.yaml"
    if not file_path.exists():
        raise ValueError(f"Zone file not found: {file_path}")
    with file_path.open(encoding="utf-8") as file_handle:
        data = yaml.safe_load(file_handle)
    if not isinstance(data, dict):
        raise ValueError("Zone YAML must load to a mapping.")
    return data


def _tag_syncable(obj, zone_id: str) -> None:
    obj.tags.add("world_sync")
    obj.tags.add(f"zone:{zone_id}")


def _tag_room_for_builder(room, zone_id: str) -> None:
    room.tags.add(zone_id, category="build")


def _has_tag(obj, tag_key: str, category: str | None = None) -> bool:
    return bool(obj.tags.get(tag_key, category=category))


def _validate_required_keys(data: dict) -> None:
    if not str(data.get("zone_id") or "").strip():
        raise ValueError("Zone YAML must include zone_id.")
    if "rooms" not in data:
        raise ValueError("Zone YAML must include rooms.")
    if "placements" not in data:
        raise ValueError("Zone YAML must include placements.")


def _normalize_room_specs(zone_id: str, rooms_data: list[dict], warnings: list[str]) -> tuple[list[dict], dict[str, dict], int]:
    room_ids = [str((room_data or {}).get("id") or "").strip() for room_data in rooms_data]
    if any(not room_id for room_id in room_ids):
        raise ValueError("Every room must define a non-empty id.")
    if len(room_ids) != len(set(room_ids)):
        raise ValueError("Room ids must be unique within a zone import.")

    normalized_rooms: list[dict] = []
    rooms_by_id: dict[str, dict] = {}
    overlaps: dict[tuple[int, int], list[str]] = {}
    xs: list[int] = []
    ys: list[int] = []

    for room_data in rooms_data:
        room_id = str(room_data.get("id") or "").strip()
        room_map = dict(room_data.get("map") or {})
        map_x = room_map.get("x")
        map_y = room_map.get("y")
        if map_x is None or map_y is None:
            raise ValueError(f"Room '{room_id}' is missing map.x or map.y.")

        map_layer = int(room_map.get("layer", 0) or 0)
        normalized_room = {
            "id": room_id,
            "name": str(room_data.get("name") or room_id),
            "typeclass": str(room_data.get("typeclass") or DEFAULT_ROOM_TYPECLASS).strip() or DEFAULT_ROOM_TYPECLASS,
            "short_desc": room_data.get("short_desc"),
            "desc": room_data.get("desc"),
            "stateful_descs": _normalize_string_map(room_data.get("stateful_descs") or {}),
            "details": _normalize_string_map(room_data.get("details") or {}),
            "room_states": sorted({state.lower() for state in _normalize_string_list(room_data.get("room_states") or [])}),
            "ambient": _normalize_ambient(room_data.get("ambient") or {}),
            "npcs": zone_room_npc_assignments.normalize_builder_reference_ids(room_data.get("npcs") or []),
            "items": zone_room_item_assignments.normalize_room_item_entries(room_data.get("items") or []),
            "map": {
                "x": int(map_x),
                "y": int(map_y),
                "layer": map_layer,
            },
            "flags": dict(room_data.get("flags") or {}),
            "exits": {},
            "special_exits": _normalize_special_exit_specs(room_data.get("special_exits") or {}, room_id),
        }
        normalized_rooms.append(normalized_room)
        rooms_by_id[room_id] = normalized_room
        overlaps.setdefault((int(map_x), int(map_y)), []).append(room_id)
        xs.append(int(map_x))
        ys.append(int(map_y))

    invalid_directions: list[str] = []
    for room_data in rooms_data:
        room_id = str(room_data.get("id") or "").strip()
        room_spec = rooms_by_id[room_id]
        for raw_direction, raw_target_id in dict(room_data.get("exits") or {}).items():
            direction = str(raw_direction or "").strip().lower()
            exit_spec = _normalize_exit_spec(raw_target_id)
            target_id = exit_spec["target"]
            if not direction:
                continue
            if direction not in ALLOWED_DIRECTIONS:
                invalid_directions.append(f"{room_id}:{direction}")
                continue
            if target_id not in rooms_by_id:
                raise ValueError(f"Room '{room_id}' exit '{direction}' points to missing target '{target_id}'.")
            room_spec["exits"][direction] = {
                "target": target_id,
                "typeclass": exit_spec["typeclass"],
                "speed": exit_spec["speed"],
                "travel_time": exit_spec["travel_time"],
            }

        for direction, exit_spec in dict(room_spec.get("special_exits") or {}).items():
            target_id = str(exit_spec.get("target") or "").strip()
            if target_id not in rooms_by_id:
                raise ValueError(f"Room '{room_id}' special exit '{direction}' points to missing target '{target_id}'.")

    if invalid_directions:
        warnings.append("Skipped invalid directions: " + ", ".join(invalid_directions))

    auto_reverse_exits = 0
    for room_spec in normalized_rooms:
        room_id = room_spec["id"]
        for direction, exit_spec in list(room_spec["exits"].items()):
            target_id = exit_spec["target"]
            reverse_direction = REVERSE_DIRECTIONS.get(direction)
            if not reverse_direction:
                continue
            target_room = rooms_by_id[target_id]
            if reverse_direction in target_room["exits"]:
                continue
            target_room["exits"][reverse_direction] = {
                "target": room_id,
                "typeclass": DEFAULT_EXIT_TYPECLASS,
                "speed": "",
                "travel_time": 0,
            }
            auto_reverse_exits += 1

    orphan_rooms = [room_spec["id"] for room_spec in normalized_rooms if not room_spec["exits"]]
    if orphan_rooms:
        warnings.append("Rooms with no exits: " + ", ".join(orphan_rooms))

    overlapping_rooms = [room_ids for room_ids in overlaps.values() if len(room_ids) > 1]
    if overlapping_rooms:
        warnings.append(
            "Overlapping map coordinates: "
            + "; ".join(", ".join(room_group) for room_group in overlapping_rooms)
        )

    spread_x = max(xs) - min(xs) if xs else 0
    spread_y = max(ys) - min(ys) if ys else 0
    if spread_x <= MAP_SPREAD_WARNING_THRESHOLD or spread_y <= MAP_SPREAD_WARNING_THRESHOLD:
        warnings.append(
            f"Map spread for zone {zone_id} looks compressed (dx={spread_x}, dy={spread_y})."
        )

    return normalized_rooms, rooms_by_id, auto_reverse_exits


def _validate_container_cycles(items: list[dict]) -> None:
    parents = {
        str(item.get("id") or "").strip(): str(item.get("parent") or "").strip()
        for item in items
        if str(item.get("parent") or "").strip()
    }
    visited: set[str] = set()
    active: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in active:
            raise ValueError(f"Circular container reference detected at '{item_id}'.")
        if item_id in visited:
            return
        active.add(item_id)
        parent_id = parents.get(item_id)
        if parent_id:
            visit(parent_id)
        active.remove(item_id)
        visited.add(item_id)

    for item_id in list(parents.keys()):
        visit(item_id)


def _normalize_placements(placements_data: dict, rooms_by_id: dict[str, dict]) -> tuple[dict[str, list[dict]], list[str]]:
    warnings: list[str] = []
    normalized = {
        "npcs": list(placements_data.get("npcs") or []),
        "items": list(placements_data.get("items") or []),
    }

    for placement in normalized["npcs"]:
        room_id = str(placement.get("room") or "").strip()
        if room_id not in rooms_by_id:
            raise ValueError(f"NPC placement '{placement.get('id')}' points to missing room '{room_id}'.")

    item_ids = [str((placement or {}).get("id") or "").strip() for placement in normalized["items"]]
    if any(not item_id for item_id in item_ids):
        raise ValueError("Every item placement must define a non-empty id.")

    item_id_set = set(item_ids)
    for placement in normalized["items"]:
        placement_id = str(placement.get("id") or "").strip()
        parent_id = str(placement.get("parent") or "").strip()
        room_id = str(placement.get("room") or "").strip()
        if parent_id and parent_id not in item_id_set:
            raise ValueError(f"Item placement '{placement_id}' points to missing parent '{parent_id}'.")
        if not parent_id and room_id not in rooms_by_id:
            raise ValueError(f"Item placement '{placement_id}' points to missing room '{room_id}'.")

    _validate_container_cycles(normalized["items"])
    return normalized, warnings


def _safe_prototype_exists(prototype_key: str) -> bool:
    if not prototype_key:
        return False
    return bool(search_prototype(key=prototype_key))


def _resolve_spawn_blueprint(placement: dict, kind: str, warnings: list[str]) -> tuple[str | None, str]:
    prototype = str(placement.get("prototype") or "").strip() or None
    default_typeclass = DEFAULT_NPC_TYPECLASS if str(kind or "").strip().lower() == "npc" else GENERIC_OBJECT_TYPECLASS
    typeclass = str(placement.get("typeclass") or default_typeclass).strip() or default_typeclass
    if prototype and not _safe_prototype_exists(prototype):
        warnings.append(f"Missing {kind} prototype '{prototype}' for '{placement.get('id')}', using {GENERIC_OBJECT_TYPECLASS}.")
        return None, GENERIC_OBJECT_TYPECLASS
    return prototype, typeclass


def _build_import_plan(zone_id: str, data: dict) -> dict:
    _validate_required_keys(data)

    yaml_zone_id = str(data.get("zone_id") or "").strip()
    if yaml_zone_id != zone_id:
        raise ValueError(f"Zone file zone_id '{yaml_zone_id}' does not match requested zone '{zone_id}'.")

    warnings: list[str] = []
    normalized_rooms, rooms_by_id, auto_reverse_exits = _normalize_room_specs(zone_id, list(data.get("rooms") or []), warnings)
    placements, placement_warnings = _normalize_placements(dict(data.get("placements") or {}), rooms_by_id)
    warnings.extend(placement_warnings)

    room_assignment_placements = zone_runtime_spawn.build_room_assignment_placements(normalized_rooms)
    placements["npcs"].extend(room_assignment_placements["npcs"])
    placements["items"].extend(room_assignment_placements["items"])

    for placement in placements["npcs"]:
        prototype, typeclass = _resolve_spawn_blueprint(placement, "npc", warnings)
        placement["resolved_prototype"] = prototype
        placement["resolved_typeclass"] = typeclass
        placement["spawn_key"] = str(placement.get("spawn_key") or placement.get("id") or "").strip()

    for placement in placements["items"]:
        prototype, typeclass = _resolve_spawn_blueprint(placement, "item", warnings)
        placement["resolved_prototype"] = prototype
        placement["resolved_typeclass"] = typeclass
        placement["spawn_key"] = str(placement.get("spawn_key") or placement.get("id") or "").strip()

    exit_count = sum(len(room_spec["exits"]) for room_spec in normalized_rooms)
    special_exit_count = sum(len(room_spec["special_exits"]) for room_spec in normalized_rooms)
    container_links = sum(1 for placement in placements["items"] if str(placement.get("parent") or "").strip())
    return {
        "zone_id": zone_id,
        "name": str(data.get("name") or zone_id),
        "rooms": normalized_rooms,
        "rooms_by_id": rooms_by_id,
        "placements": placements,
        "warnings": warnings,
        "summary": {
            "rooms": len(normalized_rooms),
            "exits": exit_count,
            "special_exits": special_exit_count,
            "npcs": len(placements["npcs"]),
            "items": len(placements["items"]),
            "containers_linked": container_links,
            "auto_reverse_exits": auto_reverse_exits,
        },
    }


def _delete_existing_zone(zone_id: str) -> None:
    queryset = ObjectDB.objects.filter(db_tags__db_key="world_sync").distinct()
    deletable = [obj for obj in queryset if _has_tag(obj, f"zone:{zone_id}")]
    print(f"Deleting {len(deletable)} objects in zone {zone_id}")
    for obj in sorted(deletable, key=lambda candidate: int(getattr(candidate, "id", 0) or 0), reverse=True):
        if bool(getattr(obj, "has_account", False)):
            continue
        obj.delete()


def _delete_existing_zone_runtime_objects(zone_id: str) -> None:
    runtime_objects = []
    for obj in _iter_zone_objects(zone_id):
        if bool(getattr(obj, "has_account", False)):
            continue
        if getattr(obj, "destination", None) is not None:
            continue
        if getattr(obj, "location", None) is None:
            continue
        runtime_objects.append(obj)

    for obj in sorted(runtime_objects, key=lambda candidate: int(getattr(candidate, "id", 0) or 0), reverse=True):
        obj.delete()


def _apply_room_data(room, room_data: dict, zone_id: str) -> None:
    room.key = room_data["name"]
    room.db.world_id = room_data["id"]
    room.db.zone_id = zone_id
    room.db.zone = zone_id
    room.db.area_id = zone_id
    room.db.map_x = room_data["map"]["x"]
    room.db.map_y = room_data["map"]["y"]
    room.db.map_layer = room_data["map"].get("layer", 0)
    room.db.short_desc = room_data.get("short_desc")
    room.db.authored_npcs = list(room_data.get("npcs") or [])
    room.db.authored_items = list(room_data.get("items") or [])
    room.ndb.runtime_npcs = []
    room.ndb.runtime_items = []
    _apply_extended_room_fields(room, room_data)
    flags = room_data.get("flags") or {}
    room.db.safe_zone = bool(flags.get("safe_zone", False))
    room.db.is_shop = bool(flags.get("is_shop", False))
    _tag_syncable(room, zone_id)
    _tag_room_for_builder(room, zone_id)


def _track_room_runtime(room, kind: str, obj) -> None:
    if kind == "npc":
        room.ndb.runtime_npcs = list(getattr(room.ndb, "runtime_npcs", []) or []) + [obj]
        return
    room.ndb.runtime_items = list(getattr(room.ndb, "runtime_items", []) or []) + [obj]


def _spawn_zone_runtime_contents(zone_id: str, plan: dict, room_lookup: dict[str, object]) -> tuple[int, int]:
    item_lookup = {}

    for placement in plan["placements"]["npcs"]:
        npc = _create_spawned_object(placement)
        target_room = room_lookup[placement["room"]]
        npc.location = target_room
        npc.home = npc.location
        definition = dict(placement.get("definition") or {})
        npc.key = str(definition.get("name") or getattr(npc, "key", "") or placement["id"])
        npc.db.world_id = placement["id"]
        npc.db.prototype = placement.get("resolved_prototype") or placement.get("prototype")
        npc.db.runtime_definition_id = placement["id"]
        npc.db.runtime_definition_kind = "npc"
        npc.db.runtime_spawn_source = placement.get("spawn_source") or "zone_placement"
        npc.db.is_npc = True
        zone_runtime_spawn.apply_runtime_npc_definition(npc, definition)
        _tag_syncable(npc, zone_id)
        _track_room_runtime(target_room, "npc", npc)
        print(f"Spawned npc {placement['id']} in {placement['room']}")

    for placement in plan["placements"]["items"]:
        item = _create_spawned_object(placement)
        definition = dict(placement.get("definition") or {})
        count = max(1, int(placement.get("count", 1) or 1))
        base_name = str(definition.get("name") or getattr(item, "key", "") or placement["id"])
        item.key = f"{base_name} (x{count})" if count > 1 else base_name
        item.aliases.add(base_name)
        item.aliases.add(str(placement["id"]))
        item.db.world_id = placement["id"]
        item.db.prototype = placement.get("resolved_prototype") or placement.get("prototype")
        item.db.runtime_definition_id = placement["id"]
        item.db.runtime_definition_kind = "item"
        item.db.runtime_spawn_source = placement.get("spawn_source") or "zone_placement"
        item.db.stack_count = count
        item.db.is_npc = False
        _tag_syncable(item, zone_id)
        item_lookup[placement["spawn_key"]] = item

    spawned_item_count = 0
    for placement in plan["placements"]["items"]:
        item = item_lookup[placement["spawn_key"]]
        parent_key = str(placement.get("parent_spawn_key") or placement.get("parent") or "").strip()
        if parent_key:
            parent = item_lookup.get(parent_key)
            if parent is None:
                raise ValueError(f"Item placement '{placement['id']}' points to missing parent '{parent_key}'.")
            item.location = parent
            item.home = room_lookup.get(placement.get("room")) or item.location
        else:
            target_room = room_lookup[placement["room"]]
            item.location = target_room
            item.home = item.location
            _track_room_runtime(target_room, "item", item)
        spawned_item_count += 1
        print(f"Spawned item {placement['id']} x{item.db.stack_count} in {placement['room']}")

    return len(plan["placements"]["npcs"]), spawned_item_count


def _iter_zone_objects(zone_id: str) -> list[object]:
    queryset = ObjectDB.objects.filter(db_tags__db_key="world_sync").distinct()
    return [obj for obj in queryset if _has_tag(obj, f"zone:{zone_id}")]


def _existing_zone_rooms(zone_id: str) -> dict[str, object]:
    existing: dict[str, object] = {}
    for obj in _iter_zone_objects(zone_id):
        if getattr(obj, "location", None) is not None or getattr(obj, "destination", None) is not None:
            continue
        world_id = str(obj.db.world_id or "").strip()
        if world_id:
            existing[world_id] = obj
    return existing


def _clear_exit_runtime_fields(exit_obj) -> None:
    exit_obj.attributes.remove("move_speed")
    exit_obj.attributes.remove("travel_time")


def _warm_load_zone(zone_id: str, plan: dict) -> dict:
    room_lookup = _existing_zone_rooms(zone_id)
    target_room_ids = {room_data["id"] for room_data in plan["rooms"]}
    stale_room_ids = sorted(set(room_lookup.keys()) - target_room_ids)

    for room_data in plan["rooms"]:
        room = room_lookup.get(room_data["id"])
        if room is None:
            room = create_object(room_data.get("typeclass") or DEFAULT_ROOM_TYPECLASS, key=room_data["name"])
            room_lookup[room_data["id"]] = room
        _apply_room_data(room, room_data, zone_id)

    for room_data in plan["rooms"]:
        room = room_lookup[room_data["id"]]
        desired_exits = {}
        desired_exits.update(dict(room_data.get("exits") or {}))
        desired_exits.update(dict(room_data.get("special_exits") or {}))

        existing_exits = {
            str(exit_obj.key or "").strip().lower(): exit_obj
            for exit_obj in list(room.contents)
            if getattr(exit_obj, "destination", None) is not None and _has_tag(exit_obj, f"zone:{zone_id}")
        }

        for direction, exit_spec in desired_exits.items():
            direction = str(direction or "").strip().lower()
            if not direction:
                continue
            exit_obj = existing_exits.pop(direction, None)
            if exit_obj is None:
                exit_typeclass = str(exit_spec.get("typeclass") or DEFAULT_EXIT_TYPECLASS).strip() or DEFAULT_EXIT_TYPECLASS
                exit_obj = create_object(
                    exit_typeclass,
                    key=direction,
                    location=room,
                    destination=room_lookup[exit_spec["target"]],
                    home=room,
                )
            else:
                exit_obj.key = direction
                exit_obj.location = room
                exit_obj.destination = room_lookup[exit_spec["target"]]
                exit_obj.home = room
            _tag_syncable(exit_obj, zone_id)
            _clear_exit_runtime_fields(exit_obj)
            if exit_spec.get("speed"):
                exit_obj.db.move_speed = exit_spec["speed"]
            if int(exit_spec.get("travel_time", 0) or 0) > 0:
                exit_obj.db.travel_time = int(exit_spec["travel_time"])

        for stale_exit in existing_exits.values():
            stale_exit.delete()

    _delete_existing_zone_runtime_objects(zone_id)
    spawned_npcs, spawned_items = _spawn_zone_runtime_contents(zone_id, plan, room_lookup)

    resolver_rooms = list(_rooms_for_zone(zone_id))
    if len(resolver_rooms) < len(target_room_ids):
        raise RuntimeError(
            f"Builder resolver mismatch for zone {zone_id}: expected at least {len(target_room_ids)} rooms, got {len(resolver_rooms)}."
        )

    warnings = list(plan["warnings"])
    if stale_room_ids:
        warnings.append("Warm load preserved rooms no longer present in YAML: " + ", ".join(stale_room_ids))

    return {
        "zone_id": zone_id,
        "dry_run": False,
        "warnings": warnings,
        "rooms": len(target_room_ids),
        "exits": plan["summary"]["exits"],
        "special_exits": plan["summary"]["special_exits"],
        "npcs": spawned_npcs,
        "items": spawned_items,
        "containers_linked": 0,
        "auto_reverse_exits": plan["summary"]["auto_reverse_exits"],
    }


def _create_spawned_object(placement: dict):
    prototype = placement.get("resolved_prototype")
    if prototype:
        spawned = spawn(str(prototype))
        if spawned:
            return spawned[0]
    typeclass = placement.get("resolved_typeclass") or placement.get("typeclass") or GENERIC_OBJECT_TYPECLASS
    key = placement.get("id") or "unnamed"
    return create_object(typeclass, key=str(key))


def load_zone(zone_id: str, dry_run: bool = False, preserve_existing: bool = False) -> dict:
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        raise ValueError("zone_id is required.")

    data = _load_zone_yaml(normalized_zone_id)
    plan = _build_import_plan(normalized_zone_id, data)

    if dry_run:
        return {
            "zone_id": normalized_zone_id,
            "dry_run": True,
            "warnings": plan["warnings"],
            **plan["summary"],
        }

    if preserve_existing:
        return _warm_load_zone(normalized_zone_id, plan)

    _delete_existing_zone(normalized_zone_id)

    room_lookup = {}
    created_exit_pairs: set[tuple[str, str]] = set()

    for room_data in plan["rooms"]:
        room = create_object(room_data.get("typeclass") or DEFAULT_ROOM_TYPECLASS, key=room_data["name"])
        _apply_room_data(room, room_data, normalized_zone_id)
        room_lookup[room_data["id"]] = room

    for room_data in plan["rooms"]:
        room = room_lookup[room_data["id"]]
        for direction, exit_spec in dict(room_data.get("exits") or {}).items():
            direction = str(direction or "").strip().lower()
            if not direction or direction not in ALLOWED_DIRECTIONS:
                continue
            exit_key = (room_data["id"], direction)
            if exit_key in created_exit_pairs:
                continue
            target_id = exit_spec["target"]
            exit_typeclass = str(exit_spec.get("typeclass") or DEFAULT_EXIT_TYPECLASS).strip() or DEFAULT_EXIT_TYPECLASS
            exit_obj = create_object(
                exit_typeclass,
                key=direction,
                location=room,
                destination=room_lookup[target_id],
                home=room,
            )
            if exit_spec.get("speed"):
                exit_obj.db.move_speed = exit_spec["speed"]
            if int(exit_spec.get("travel_time", 0) or 0) > 0:
                exit_obj.db.travel_time = int(exit_spec["travel_time"])
            _tag_syncable(exit_obj, normalized_zone_id)
            created_exit_pairs.add(exit_key)

        for direction, exit_spec in dict(room_data.get("special_exits") or {}).items():
            direction = str(direction or "").strip().lower()
            if not direction:
                continue
            exit_key = (room_data["id"], direction)
            if exit_key in created_exit_pairs:
                continue
            target_id = exit_spec["target"]
            exit_typeclass = str(exit_spec.get("typeclass") or DEFAULT_EXIT_TYPECLASS).strip() or DEFAULT_EXIT_TYPECLASS
            exit_obj = create_object(
                exit_typeclass,
                key=direction,
                location=room,
                destination=room_lookup[target_id],
                home=room,
            )
            if exit_spec.get("speed"):
                exit_obj.db.move_speed = exit_spec["speed"]
            if int(exit_spec.get("travel_time", 0) or 0) > 0:
                exit_obj.db.travel_time = int(exit_spec["travel_time"])
            _tag_syncable(exit_obj, normalized_zone_id)
            created_exit_pairs.add(exit_key)

    spawned_npcs, spawned_items = _spawn_zone_runtime_contents(normalized_zone_id, plan, room_lookup)

    resolver_rooms = list(_rooms_for_zone(normalized_zone_id))
    if len(resolver_rooms) != len(room_lookup):
        raise RuntimeError(
            f"Builder resolver mismatch for zone {normalized_zone_id}: expected {len(room_lookup)} rooms, got {len(resolver_rooms)}."
        )

    print(f"NPCs placed: {spawned_npcs}")
    print(f"Items placed: {spawned_items}")
    print(f"Containers linked: {plan['summary']['containers_linked']}")

    return {
        "zone_id": normalized_zone_id,
        "dry_run": False,
        "warnings": plan["warnings"],
        "rooms": len(room_lookup),
        "exits": plan["summary"]["exits"],
        "special_exits": plan["summary"]["special_exits"],
        "npcs": spawned_npcs,
        "items": spawned_items,
        "containers_linked": plan["summary"]["containers_linked"],
        "auto_reverse_exits": plan["summary"]["auto_reverse_exits"],
    }