from collections import Counter


LANDING_PRIMARY_IMAGE = None
LANDING_MAP_EDGE_MAX_MANHATTAN = 160

_DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "u": "up",
    "d": "down",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
}

_COMPASS_DIRECTIONS = frozenset(
    {"north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "up", "down"}
)


def _normalize_direction(direction):
    return str(direction or "").strip().lower()


def normalize_exit_direction(direction):
    normalized = _normalize_direction(direction)
    return _DIRECTION_ALIASES.get(normalized, normalized)


def _room_coordinates(room):
    room_map = dict(room.get("map") or {}) if isinstance(room, dict) else {}
    room_x = room.get("x") if isinstance(room, dict) else None
    room_y = room.get("y") if isinstance(room, dict) else None
    if room_x is None:
        room_x = room_map.get("x")
    if room_y is None:
        room_y = room_map.get("y")
    return room_x, room_y


def _room_has_coordinates(room):
    room_x, room_y = _room_coordinates(room)
    return room_x is not None and room_y is not None


def _room_canonical_image(room):
    return str(room.get("canonical_image") or "").strip()


def _room_exit_targets(room):
    exits = dict(room.get("exits") or {}) if isinstance(room, dict) else {}
    targets = []
    for spec in exits.values():
        target = str((spec or {}).get("target") or "").strip()
        if target:
            targets.append(target)
    return targets


def _prune_rooms_without_rendered_destinations(filtered_rooms):
    rendered_ids = {str(room.get("id")) for room in list(filtered_rooms or []) if room.get("id") is not None}
    pruned_rooms = []
    for room in list(filtered_rooms or []):
        exit_targets = _room_exit_targets(room)
        if exit_targets and all(target not in rendered_ids for target in exit_targets):
            continue
        pruned_rooms.append(room)
    return pruned_rooms


def select_zone_rooms(rooms, *, primary_image=LANDING_PRIMARY_IMAGE):
    coordinate_rooms = [room for room in list(rooms or []) if _room_has_coordinates(room)]
    if not coordinate_rooms:
        return list(rooms or [])

    normalized_primary_image = str(primary_image or "").strip()
    image_counts = Counter(_room_canonical_image(room) for room in coordinate_rooms if _room_canonical_image(room))
    resolved_primary_image = normalized_primary_image or (image_counts.most_common(1)[0][0] if image_counts else "")
    has_mixed_coordinate_spaces = len(image_counts) > 1 or any(not _room_canonical_image(room) for room in coordinate_rooms)
    if resolved_primary_image and has_mixed_coordinate_spaces:
        dominant_rooms = [room for room in coordinate_rooms if _room_canonical_image(room) == resolved_primary_image]
        if dominant_rooms:
            return dominant_rooms

    return coordinate_rooms


def edge_renders_on_map(source_room, edge, destination_room, *, max_manhattan=LANDING_MAP_EDGE_MAX_MANHATTAN):
    source_coordinates = _room_coordinates(source_room)
    destination_coordinates = _room_coordinates(destination_room)
    if None in source_coordinates or None in destination_coordinates:
        return True

    source_image = _room_canonical_image(source_room)
    destination_image = _room_canonical_image(destination_room)
    if source_image or destination_image:
        if source_image != destination_image:
            return False

    manhattan_distance = abs(source_coordinates[0] - destination_coordinates[0]) + abs(source_coordinates[1] - destination_coordinates[1])
    return manhattan_distance <= max_manhattan


def filter_zone_rooms_and_edges(rooms, edges, *, primary_image=LANDING_PRIMARY_IMAGE, max_manhattan=LANDING_MAP_EDGE_MAX_MANHATTAN):
    filtered_rooms = select_zone_rooms(rooms, primary_image=primary_image)
    filtered_rooms = _prune_rooms_without_rendered_destinations(filtered_rooms)
    rooms_by_id = {room.get("id"): room for room in filtered_rooms}

    filtered_edges = []
    for edge in list(edges or []):
        source_room = rooms_by_id.get(edge.get("from"))
        destination_room = rooms_by_id.get(edge.get("to"))
        if not source_room or not destination_room:
            continue
        if not edge_renders_on_map(source_room, edge, destination_room, max_manhattan=max_manhattan):
            continue
        filtered_edges.append(edge)

    return filtered_rooms, filtered_edges