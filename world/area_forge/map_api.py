from collections import deque
import time

from evennia.utils.search import search_tag

from tools.diretest.core.runtime import suppress_client_payloads
from world.area_forge.utils.messages import send_structured


_DIRECTION_VECTORS = {
    "north": (0, -1),
    "n": (0, -1),
    "south": (0, 1),
    "s": (0, 1),
    "east": (1, 0),
    "e": (1, 0),
    "west": (-1, 0),
    "w": (-1, 0),
    "northeast": (1, -1),
    "ne": (1, -1),
    "northwest": (-1, -1),
    "nw": (-1, -1),
    "southeast": (1, 1),
    "se": (1, 1),
    "southwest": (-1, 1),
    "sw": (-1, 1),
    "up": (2, -1),
    "u": (2, -1),
    "down": (2, 1),
    "d": (2, 1),
    "in": (2, 0),
    "out": (-2, 0),
}

_REVERSE_DIRECTIONS = {
    "north": "south",
    "n": "south",
    "south": "north",
    "s": "north",
    "east": "west",
    "e": "west",
    "west": "east",
    "w": "east",
    "northeast": "southwest",
    "ne": "southwest",
    "northwest": "southeast",
    "nw": "southeast",
    "southeast": "northwest",
    "se": "northwest",
    "southwest": "northeast",
    "sw": "northeast",
    "up": "down",
    "u": "down",
    "down": "up",
    "d": "up",
    "in": "out",
    "out": "in",
}

_FALLBACK_VECTORS = [
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    (1, 1),
    (-1, -1),
    (1, -1),
    (-1, 1),
]

_ZONE_MAP_TEMPLATE_CACHE = {}
ZONE_MAP_CACHE_SECONDS = 30.0


def _empty_map_payload():
    return {"rooms": [], "edges": [], "exits": [], "player_room_id": None, "zone": None}


def _get_cached_zone_template(area_tag):
    now = time.time()
    cached = _ZONE_MAP_TEMPLATE_CACHE.get(area_tag)
    if cached and now < cached["expires_at"]:
        return cached["template"]

    tagged_objects = list(search_tag(area_tag, category="build"))
    zone_rooms = [obj for obj in tagged_objects if getattr(obj, "destination", None) is None and getattr(obj, "id", None) is not None]
    if not zone_rooms:
        _ZONE_MAP_TEMPLATE_CACHE.pop(area_tag, None)
        return None

    x_values = [getattr(room.db, "map_x", None) for room in zone_rooms if getattr(room.db, "map_x", None) is not None]
    y_values = [getattr(room.db, "map_y", None) for room in zone_rooms if getattr(room.db, "map_y", None) is not None]
    x_offset = min(x_values) if x_values else 0
    y_offset = min(y_values) if y_values else 0

    rooms_by_id = {room.id: room for room in zone_rooms}
    edges = _collect_room_edges(rooms_by_id)
    serialized_rooms = _serialize_rooms(
        rooms_by_id,
        edges,
        current_room_id=None,
        x_offset=x_offset,
        y_offset=y_offset,
    )
    template = {
        "rooms": [
            {
                "id": room["id"],
                "x": room["x"],
                "y": room["y"],
                "name": room["name"],
            }
            for room in serialized_rooms
        ],
        "edges": edges,
        "zone": area_tag,
    }
    _ZONE_MAP_TEMPLATE_CACHE[area_tag] = {
        "expires_at": now + ZONE_MAP_CACHE_SECONDS,
        "template": template,
    }
    return template


def _area_tag_for_room(room):
    if not room or not hasattr(room, "tags"):
        return None
    build_tags = room.tags.get(category="build", return_list=True) or []
    return build_tags[0] if build_tags else None


def _normalize_direction(direction):
    return (direction or "").strip().lower()


def _direction_vector(direction):
    return _DIRECTION_VECTORS.get(_normalize_direction(direction))


def _reverse_direction(direction):
    normalized = _normalize_direction(direction)
    return _REVERSE_DIRECTIONS.get(normalized)


def _room_relative_coordinates(room, *, x_offset=0, y_offset=0):
    room_x = getattr(room.db, "map_x", None)
    room_y = getattr(room.db, "map_y", None)
    if room_x is None or room_y is None:
        return None
    return room_x - x_offset, room_y - y_offset


def _find_open_position(preferred, used_positions):
    if preferred not in used_positions:
        return preferred

    base_x, base_y = preferred
    for radius in range(1, max(4, len(used_positions) + 2)):
        for offset_x, offset_y in _FALLBACK_VECTORS:
            candidate = (base_x + (offset_x * radius), base_y + (offset_y * radius))
            if candidate not in used_positions:
                return candidate
    return preferred


def _choose_layout_anchor(rooms_by_id, edges):
    if not rooms_by_id:
        return None

    degree_by_room = {room_id: 0 for room_id in rooms_by_id}
    for edge in edges:
        from_id = edge.get("from")
        to_id = edge.get("to")
        if from_id in degree_by_room:
            degree_by_room[from_id] += 1
        if to_id in degree_by_room:
            degree_by_room[to_id] += 1

    return min(
        rooms_by_id,
        key=lambda room_id: (-degree_by_room.get(room_id, 0), room_id),
    )


def _layout_room_positions(rooms_by_id, edges, origin_id, *, x_offset=0, y_offset=0):
    positions = {}
    used_positions = set()

    for room_id, room in rooms_by_id.items():
        coordinates = _room_relative_coordinates(room, x_offset=x_offset, y_offset=y_offset)
        if coordinates is None:
            continue
        positions[room_id] = coordinates
        used_positions.add(coordinates)

    adjacency = {room_id: [] for room_id in rooms_by_id}
    for edge in sorted(edges, key=lambda entry: (entry["from"], entry["to"], entry["dir"])):
        adjacency.setdefault(edge["from"], []).append((edge["to"], edge["dir"]))
        adjacency.setdefault(edge["to"], []).append((edge["from"], _reverse_direction(edge["dir"])))

    queue = deque()
    queued = set()

    def enqueue(room_id):
        if room_id in queued or room_id not in rooms_by_id:
            return
        queue.append(room_id)
        queued.add(room_id)

    anchor_id = _choose_layout_anchor(rooms_by_id, edges)

    if anchor_id in rooms_by_id and anchor_id not in positions:
        anchor_position = _find_open_position((0, 0), used_positions)
        positions[anchor_id] = anchor_position
        used_positions.add(anchor_position)

    enqueue(anchor_id)
    enqueue(origin_id)
    for room_id in sorted(positions):
        enqueue(room_id)

    fallback_column = max((x for x, _ in used_positions), default=0) + 2

    while queue or len(positions) < len(rooms_by_id):
        if not queue:
            next_room_id = next((room_id for room_id in rooms_by_id if room_id not in positions), None)
            if next_room_id is None:
                break
            fallback_position = _find_open_position((fallback_column, 0), used_positions)
            fallback_column = fallback_position[0] + 2
            positions[next_room_id] = fallback_position
            used_positions.add(fallback_position)
            enqueue(next_room_id)

        room_id = queue.popleft()
        current_position = positions.get(room_id)
        if current_position is None:
            fallback_position = _find_open_position((fallback_column, 0), used_positions)
            fallback_column = fallback_position[0] + 2
            positions[room_id] = fallback_position
            used_positions.add(fallback_position)
            current_position = fallback_position
        base_x, base_y = current_position

        for index, (neighbor_id, direction) in enumerate(adjacency.get(room_id, [])):
            if neighbor_id not in rooms_by_id:
                continue

            if neighbor_id in positions:
                enqueue(neighbor_id)
                continue

            step_x, step_y = _direction_vector(direction) or _FALLBACK_VECTORS[index % len(_FALLBACK_VECTORS)]
            candidate = _find_open_position((base_x + step_x, base_y + step_y), used_positions)
            positions[neighbor_id] = candidate
            used_positions.add(candidate)
            enqueue(neighbor_id)

    return positions


def _serialize_room(room, *, x_offset=0, y_offset=0, current_room_id=None, fallback_position=None):
    room_id = getattr(room, "id", None)
    coordinates = _room_relative_coordinates(room, x_offset=x_offset, y_offset=y_offset)
    room_x, room_y = coordinates if coordinates is not None else (fallback_position or (0, 0))
    return {
        "id": room_id,
        "x": room_x,
        "y": room_y,
        "name": room.key,
        "current": room_id == current_room_id,
        "is_player": room_id == current_room_id,
    }


def _serialize_rooms(rooms_by_id, edges, *, current_room_id=None, x_offset=0, y_offset=0):
    positions = _layout_room_positions(rooms_by_id, edges, current_room_id, x_offset=x_offset, y_offset=y_offset)
    serialized_rooms = [
        _serialize_room(
            room,
            x_offset=x_offset,
            y_offset=y_offset,
            current_room_id=current_room_id,
            fallback_position=positions.get(room.id),
        )
        for room in rooms_by_id.values()
    ]
    return sorted(serialized_rooms, key=lambda room: (room["y"], room["x"], room["id"]))


def _collect_room_edges(rooms_by_id):
    edges = []
    seen = set()
    for room_id, room in rooms_by_id.items():
        for exit_obj in getattr(room, "exits", []):
            destination = getattr(exit_obj, "destination", None)
            destination_id = getattr(destination, "id", None)
            if destination_id not in rooms_by_id:
                continue
            signature = (room_id, destination_id, exit_obj.key)
            if signature in seen:
                continue
            seen.add(signature)
            edges.append(
                {
                    "from": room_id,
                    "to": destination_id,
                    "dir": exit_obj.key,
                }
            )
    return sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["dir"]))


def get_local_map(character, radius=3):
    origin = getattr(character, "location", None)
    if not origin:
        return _empty_map_payload()

    visited = set()
    queue = deque([(origin, 0)])
    rooms_by_id = {}
    edges = []

    while queue:
        room, dist = queue.popleft()
        room_id = getattr(room, "id", None)
        if not room or room_id in visited or dist > radius:
            continue

        visited.add(room_id)
        rooms_by_id[room_id] = room

        for exit_obj in getattr(room, "exits", []):
            destination = getattr(exit_obj, "destination", None)
            destination_id = getattr(destination, "id", None)
            if not destination or destination_id is None:
                continue

            edges.append(
                {
                    "from": room_id,
                    "to": destination_id,
                    "dir": exit_obj.key,
                }
            )
            if destination_id not in visited:
                queue.append((destination, dist + 1))

    room_ids = set(rooms_by_id)
    filtered_edges = [edge for edge in edges if edge["from"] in room_ids and edge["to"] in room_ids]
    serialized_rooms = _serialize_rooms(rooms_by_id, filtered_edges, current_room_id=origin.id)

    return {
        "rooms": serialized_rooms,
        "edges": filtered_edges,
        "exits": filtered_edges,
        "player_room_id": origin.id,
        "zone": "local",
    }


def get_zone_map(character):
    origin = getattr(character, "location", None)
    if not origin:
        return _empty_map_payload()

    area_tag = _area_tag_for_room(origin)
    if not area_tag:
        return get_local_map(character)

    template = _get_cached_zone_template(area_tag)
    if not template:
        return get_local_map(character)

    serialized_rooms = [
        {
            "id": room["id"],
            "x": room["x"],
            "y": room["y"],
            "name": room["name"],
            "current": room["id"] == origin.id,
            "is_player": room["id"] == origin.id,
        }
        for room in template["rooms"]
    ]

    return {
        "rooms": serialized_rooms,
        "edges": template["edges"],
        "exits": template["edges"],
        "player_room_id": origin.id,
        "zone": area_tag,
    }


def send_map_update(character, radius=3, session=None, mode="zone"):
    map_data = get_zone_map(character) if mode == "zone" else get_local_map(character, radius=radius)
    sent = 0
    if not suppress_client_payloads():
        sent = send_structured(character, "map", map_data, session=session)
    if sent:
        print(f"[MAP] Sent {len(map_data['rooms'])} rooms to {sent} structured session(s) for {character.key}")
    return map_data