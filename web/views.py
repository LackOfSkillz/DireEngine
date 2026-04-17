import json
import re

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from evennia.objects.models import ObjectDB

from web.character_helpers import parse_request_data
from world.builder.services import exit_service


ROOM_TYPECLASS = "typeclasses.rooms.Room"
BUILDER_ENVIRONMENT_OPTIONS = {"city", "forest", "swamp", "tavern"}
BUILDER_DIRECTIONS = ("north", "south", "east", "west", "up", "down")


def builder_view(request):
    return render(request, "webclient/builder.html", {})


def _room_queryset():
    return ObjectDB.objects.filter(
        db_typeclass_path=ROOM_TYPECLASS,
        db_location__isnull=True,
    ).order_by("db_key", "id")


def _get_room(room_id):
    room = _room_queryset().filter(id=room_id).first()
    if room is None:
        raise Http404("Room not found")
    return room


def _normalize_zone_id(raw_zone_id):
    text = str(raw_zone_id or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _titleize_zone_id(zone_id):
    return str(zone_id or "").replace("_", " ").strip().title() or "Untitled Zone"


def _get_room_zone_id(room):
    raw_zone_id = (
        getattr(getattr(room, "db", None), "zone_id", None)
        or getattr(getattr(room, "db", None), "zone", None)
        or getattr(getattr(room, "db", None), "area_id", None)
    )
    return _normalize_zone_id(raw_zone_id)


def _derive_builder_environment(room):
    terrain = str(getattr(room.db, "terrain_type", "") or "").strip().lower()
    if terrain == "swamp":
        return "swamp"

    key_text = str(getattr(room, "key", "") or "").strip().lower()
    desc_text = str(getattr(room.db, "desc", "") or "").strip().lower()
    if any(token in f"{key_text} {desc_text}" for token in ("tavern", "inn", "alehouse", "taproom")):
        return "tavern"

    environment_type = "urban"
    if hasattr(room, "get_environment_type"):
        environment_type = str(room.get_environment_type() or "urban").strip().lower() or "urban"
    else:
        environment_type = str(getattr(room.db, "environment_type", "urban") or "urban").strip().lower() or "urban"
    if environment_type == "wilderness":
        return "forest"
    return "city"


def _apply_builder_environment(room, builder_environment):
    value = str(builder_environment or "city").strip().lower()
    if value not in BUILDER_ENVIRONMENT_OPTIONS:
        value = "city"

    if value == "forest":
        environment_type = "wilderness"
        terrain_type = "forest"
    elif value == "swamp":
        environment_type = "wilderness"
        terrain_type = "swamp"
    else:
        environment_type = "urban"
        terrain_type = "urban"

    if hasattr(room, "set_environment_type"):
        room.set_environment_type(environment_type)
    else:
        room.db.environment_type = environment_type

    if hasattr(room, "set_terrain_type"):
        room.set_terrain_type(terrain_type)
    else:
        room.db.terrain_type = terrain_type

    room.db.builder_environment = value
    return value


def _coerce_map_coordinate(value, fallback=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(fallback)


def _serialize_room_exit(exit_obj):
    direction = str(getattr(exit_obj, "key", "") or "").strip().lower()
    if direction not in BUILDER_DIRECTIONS:
        return None
    target = getattr(exit_obj, "destination", None)
    target_id = getattr(target, "id", None)
    if not target_id:
        return None
    return {
        "id": getattr(exit_obj, "id", None),
        "direction": direction,
        "target_id": int(target_id),
        "target_name": str(getattr(target, "db_key", "") or getattr(target, "key", "") or f"Room {target_id}"),
    }


def _get_builder_exits(room):
    serialized = []
    for exit_obj in list(room.contents_get(content_type="exit") or []):
        payload = _serialize_room_exit(exit_obj)
        if payload:
            serialized.append(payload)
    order = {direction: index for index, direction in enumerate(BUILDER_DIRECTIONS)}
    serialized.sort(key=lambda item: (order.get(item["direction"], 999), item["target_name"], item["target_id"]))
    return serialized


def _derive_builder_short_desc(room):
    description = str(getattr(room.db, "desc", "") or "").strip()
    if not description:
        return str(room.db_key or "").strip()
    first_line = next((line.strip() for line in description.splitlines() if line.strip()), "")
    first_sentence = str(first_line or description).split(".")[0].strip()
    return first_sentence or str(room.db_key or "").strip()


def _serialize_builder_room(room, fallback_index=0):
    zone_id = _get_room_zone_id(room)
    map_x = getattr(getattr(room, "db", None), "map_x", None)
    map_y = getattr(getattr(room, "db", None), "map_y", None)
    map_layer = getattr(getattr(room, "db", None), "map_layer", None)
    return {
        "id": room.id,
        "name": room.db_key,
        "short_desc": _derive_builder_short_desc(room),
        "desc": str(getattr(room.db, "desc", "") or ""),
        "environment": _derive_builder_environment(room),
        "zone_id": zone_id,
        "map_x": _coerce_map_coordinate(map_x, fallback_index % 12),
        "map_y": _coerce_map_coordinate(map_y, fallback_index // 12),
        "map_layer": _coerce_map_coordinate(map_layer, 0),
        "exits": _get_builder_exits(room),
    }


def _get_zone_rooms(zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    rooms = []
    for room in _room_queryset():
        if _get_room_zone_id(room) == normalized_zone_id:
            rooms.append(room)
    return rooms


def _serialize_zone_payload(zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    zone_rooms = _get_zone_rooms(normalized_zone_id)
    serialized_rooms = [_serialize_builder_room(room, fallback_index=index) for index, room in enumerate(zone_rooms)]
    return {
        "zone_id": normalized_zone_id,
        "name": _titleize_zone_id(normalized_zone_id),
        "rooms": serialized_rooms,
    }


def _normalize_builder_exits(raw_exits):
    if raw_exits is None:
        return []
    if not isinstance(raw_exits, list):
        raise ValueError("exits must be a list.")

    normalized = []
    seen_directions = set()
    for item in raw_exits:
        if not isinstance(item, dict):
            raise ValueError("each exit must be an object.")
        direction = str(item.get("direction") or "").strip().lower()
        if direction not in BUILDER_DIRECTIONS:
            raise ValueError(f"invalid direction: {direction or 'blank'}")
        if direction in seen_directions:
            raise ValueError(f"duplicate exit direction: {direction}")
        target_id = int(item.get("target_id") or 0)
        if target_id <= 0:
            raise ValueError(f"target room is required for {direction}")
        target_room = _get_room(target_id)
        normalized.append({"direction": direction, "target_room": target_room})
        seen_directions.add(direction)
    return normalized


def builder_room_list(request):
    rooms = [
        {
            "id": room.id,
            "db_key": room.db_key,
            "zone_id": _get_room_zone_id(room),
        }
        for room in _room_queryset()
    ]
    return JsonResponse(rooms, safe=False)


def builder_zone_detail(request, zone_id):
    payload = _serialize_zone_payload(zone_id)
    if not payload["rooms"]:
        raise Http404("Zone not found")
    return JsonResponse(payload)


def builder_room_detail(request, room_id):
    room = _get_room(room_id)
    payload = _serialize_builder_room(room)
    return JsonResponse(
        payload
    )


@csrf_exempt
@require_http_methods(["POST"])
def builder_room_save(request, room_id):
    room = _get_room(room_id)
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    name = str(data.get("name") or "").strip()
    desc = str(data.get("desc") or "").strip()
    environment = str(data.get("environment") or "city").strip().lower()
    try:
        exits = _normalize_builder_exits(data.get("exits") or [])
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    if not name:
        return JsonResponse({"status": "error", "error": "name is required"}, status=400)
    if not desc:
        return JsonResponse({"status": "error", "error": "desc is required"}, status=400)

    room.db_key = name
    room.db.desc = desc
    environment = _apply_builder_environment(room, environment)
    requested_directions = {item["direction"] for item in exits}
    for existing in _get_builder_exits(room):
        if existing["direction"] not in requested_directions:
            exit_service.delete_exit(room, existing["direction"])
    for exit_data in exits:
        exit_service.ensure_exit(room, exit_data["direction"], exit_data["target_room"])
    room.save()
    room_payload = _serialize_builder_room(room)

    return JsonResponse(
        {
            "status": "ok",
            "id": room.id,
            "environment": environment,
            "zone_id": room_payload["zone_id"],
            "room": room_payload,
            "exits": room_payload["exits"],
        }
    )