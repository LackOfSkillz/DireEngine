from __future__ import annotations

from collections.abc import Mapping


MAP_SCHEMA_VERSION = "v1"

ROOM_SCHEMA = {
    "id": str,
    "name": str,
    "description": str,
    "map_x": int,
    "map_y": int,
    "map_layer": int,
    "exits": dict,
}

MAP_SCHEMA = {
    "area_id": str,
    "rooms": list,
}


def _require_mapping(value: object, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping.")
    return value


def _require_type(value: object, expected_type: type, label: str) -> None:
    if not isinstance(value, expected_type):
        raise ValueError(f"{label} must be of type {expected_type.__name__}.")


def validate_map_schema(data: dict) -> None:
    root = _require_mapping(data, "Map data")

    if "area_id" not in root:
        raise ValueError("Map data must include area_id.")
    if "rooms" not in root:
        raise ValueError("Map data must include rooms.")

    area_id = root.get("area_id")
    rooms = root.get("rooms")

    _require_type(area_id, str, "area_id")
    _require_type(rooms, list, "rooms")

    room_ids: set[str] = set()
    declared_targets: set[str] = set()

    for index, raw_room in enumerate(rooms):
        room = _require_mapping(raw_room, f"rooms[{index}]")
        for required_key, expected_type in ROOM_SCHEMA.items():
            if required_key not in room:
                raise ValueError(f"rooms[{index}] is missing required key '{required_key}'.")
            _require_type(room.get(required_key), expected_type, f"rooms[{index}].{required_key}")

        room_id = room.get("id")
        if room_id in room_ids:
            raise ValueError(f"Duplicate room id '{room_id}' found in map schema.")
        room_ids.add(room_id)

        exits = room.get("exits")
        for direction, target_id in exits.items():
            if not isinstance(direction, str):
                raise ValueError(f"rooms[{index}].exits keys must be strings.")
            if isinstance(target_id, str):
                declared_targets.add(target_id)
                continue
            if not isinstance(target_id, Mapping):
                raise ValueError(f"rooms[{index}].exits['{direction}'] must be a string room id or target mapping.")
            zone_id = target_id.get("zone_id")
            room_id = target_id.get("room_id")
            _require_type(zone_id, str, f"rooms[{index}].exits['{direction}'].zone_id")
            _require_type(room_id, str, f"rooms[{index}].exits['{direction}'].room_id")
            if zone_id == area_id:
                declared_targets.add(room_id)

    missing_targets = sorted(target_id for target_id in declared_targets if target_id not in room_ids)
    if missing_targets:
        raise ValueError(f"Map schema references unknown exit targets: {', '.join(missing_targets)}")