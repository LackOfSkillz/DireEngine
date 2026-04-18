import json
import re
from types import SimpleNamespace

from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from web.character_helpers import parse_request_data
from world.area_forge import map_api
from world.builder.services import exit_service, zone_service


ROOM_TYPECLASS = "typeclasses.rooms.Room"
BUILDER_UNASSIGNED_ZONE_SENTINEL = "__unassigned__"
BUILDER_ENVIRONMENT_OPTIONS = {"city", "forest", "swamp", "tavern"}
BUILDER_DIRECTION_ALIASES = {
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
BUILDER_DIRECTIONS = (
    "north",
    "south",
    "east",
    "west",
    "up",
    "down",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "gate",
    "arch",
    "bridge",
    "stair",
    "path",
    "walk",
    "ramp",
    "pier",
    "ferry",
    "dock",
    "guild",
    "in",
    "out",
    "enter",
    "leave",
    "entry",
    "veranda",
    "yard",
)


def _normalize_builder_direction(direction):
    text = str(direction or "").strip().lower()
    if not text:
        return ""
    return BUILDER_DIRECTION_ALIASES.get(text, text)


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
    if str(raw_zone_id or "").strip().lower() == BUILDER_UNASSIGNED_ZONE_SENTINEL:
        return ""
    text = str(raw_zone_id or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _titleize_zone_id(zone_id):
    return str(zone_id or "").replace("_", " ").strip().title() or "Untitled Zone"


def _serialize_builder_zones():
    registry = zone_service.load_zone_registry()
    zones = {}
    for zone_id, zone in dict(registry.get("zones") or {}).items():
        normalized_zone_id = _normalize_zone_id(zone_id)
        zones[normalized_zone_id] = {
            "id": normalized_zone_id,
            "name": str(zone.get("name") or _titleize_zone_id(normalized_zone_id)),
            "area": str(zone.get("area") or normalized_zone_id),
            "rooms": [],
        }

    unassigned_rooms = []
    for room in _room_queryset():
        room_summary = {
            "id": room.id,
            "name": str(room.db_key or f"Room {room.id}"),
        }
        zone_id = _get_room_zone_id(room)
        if not zone_id:
            unassigned_rooms.append(room_summary)
            continue
        zone_entry = zones.setdefault(
            zone_id,
            {
                "id": zone_id,
                "name": _titleize_zone_id(zone_id),
                "area": str(getattr(getattr(room, "db", None), "area_id", None) or zone_id),
                "rooms": [],
            },
        )
        zone_entry["rooms"].append(room_summary)
        if not zone_entry.get("area"):
            zone_entry["area"] = str(getattr(getattr(room, "db", None), "area_id", None) or zone_id)

    serialized = sorted(zones.values(), key=lambda zone: (zone["name"].lower(), zone["id"]))
    if unassigned_rooms:
        serialized.insert(
            0,
            {
                "id": "",
                "name": "Unassigned",
                "area": "",
                "rooms": sorted(unassigned_rooms, key=lambda room: (room["name"].lower(), room["id"])),
            },
        )
    return serialized


def _get_builder_zone_meta(zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    for zone in _serialize_builder_zones():
        if _normalize_zone_id(zone.get("id")) == normalized_zone_id:
            return zone
    return None


def _set_room_zone(room, zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    room.tags.clear(category="build")
    if not normalized_zone_id:
        room.db.zone_id = None
        room.db.zone = None
        room.db.area_id = None
        return ""

    zone_meta = _get_builder_zone_meta(normalized_zone_id)
    area_id = str((zone_meta or {}).get("area") or normalized_zone_id).strip() or normalized_zone_id
    room.tags.add(normalized_zone_id, category="build")
    room.db.zone_id = normalized_zone_id
    room.db.zone = normalized_zone_id
    room.db.area_id = area_id
    return normalized_zone_id


def _validate_room_name_uniqueness(name, zone_id, exclude_room_id=None):
    normalized_name = str(name or "").strip().casefold()
    normalized_zone_id = _normalize_zone_id(zone_id)
    if not normalized_name:
        return
    for room in _room_queryset():
        if exclude_room_id is not None and int(room.id) == int(exclude_room_id):
            continue
        if _get_room_zone_id(room) != normalized_zone_id:
            continue
        if str(room.db_key or "").strip().casefold() == normalized_name:
            raise ValueError("duplicate room name in this zone")


def _get_room_zone_id(room):
    build_tags = room.tags.get(category="build", return_list=True) or []
    if build_tags:
        return _normalize_zone_id(build_tags[0])

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
    direction = _normalize_builder_direction(getattr(exit_obj, "key", "") or "")
    if not direction:
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
    zone_meta = _get_builder_zone_meta(normalized_zone_id) or {
        "id": normalized_zone_id,
        "name": _titleize_zone_id(normalized_zone_id),
        "area": normalized_zone_id,
        "rooms": [],
    }
    zone_rooms = _get_zone_rooms(normalized_zone_id)
    room_payloads = {
        room.id: _serialize_builder_room(room, fallback_index=index)
        for index, room in enumerate(zone_rooms)
    }
    template = map_api._get_cached_zone_template(normalized_zone_id)

    if template:
        serialized_rooms = []
        for map_room in template.get("rooms") or []:
            room_id = int(map_room.get("id") or 0)
            base_room = room_payloads.get(room_id)
            if base_room is None:
                continue
            serialized_rooms.append(
                {
                    **base_room,
                    "name": map_room.get("name") or base_room["name"],
                    "x": map_room.get("x", base_room["map_x"]),
                    "y": map_room.get("y", base_room["map_y"]),
                    "map_color": map_room.get("map_color") or "#5f8f57",
                    "type": map_room.get("type") or "room",
                    "has_poi": bool(map_room.get("has_poi")),
                    "has_guild_entrance": bool(map_room.get("has_guild_entrance")),
                }
            )
        return {
            "zone_id": normalized_zone_id,
            "name": zone_meta["name"],
            "area": zone_meta["area"],
            "zone": template.get("zone") or normalized_zone_id,
            "rooms": serialized_rooms,
            "edges": template.get("edges") or [],
        }

    serialized_rooms = list(room_payloads.values())
    return {
        "zone_id": normalized_zone_id,
        "name": zone_meta["name"],
        "area": zone_meta["area"],
        "rooms": serialized_rooms,
        "edges": [],
    }


def _serialize_builder_local_map_payload(room):
    payload = map_api.get_local_map(SimpleNamespace(location=room))
    return {
        "zone_id": "local",
        "name": f"Local {str(getattr(room, 'db_key', '') or 'Map').strip()}",
        "rooms": payload.get("rooms") or [],
        "edges": payload.get("edges") or payload.get("exits") or [],
        "player_room_id": payload.get("player_room_id"),
        "zone": payload.get("zone") or "local",
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
        direction = _normalize_builder_direction(item.get("direction") or "")
        if not direction:
            raise ValueError("invalid direction: blank")
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


def builder_zone_list(request):
    return JsonResponse(_serialize_builder_zones(), safe=False)


def builder_zone_detail(request, zone_id):
    payload = _serialize_zone_payload(zone_id)
    if not payload["rooms"] and _get_builder_zone_meta(zone_id) is None:
        raise Http404("Zone not found")
    return JsonResponse(payload)


def builder_room_detail(request, room_id):
    room = _get_room(room_id)
    payload = _serialize_builder_room(room)
    payload["map_payload"] = _serialize_builder_local_map_payload(room)
    return JsonResponse(
        payload
    )


@csrf_exempt
@require_http_methods(["POST"])
def builder_zone_create(request):
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    name = str(data.get("name") or "").strip()
    area = _normalize_zone_id(data.get("area") or "")
    if not name:
        return JsonResponse({"status": "error", "error": "name is required"}, status=400)
    if not area:
        return JsonResponse({"status": "error", "error": "area is required"}, status=400)

    try:
        zone = zone_service.create_zone(area, name, area=area)
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    return JsonResponse(
        {
            "status": "ok",
            "zone": {
                "id": zone["zone_id"],
                "name": zone["name"],
                "area": zone.get("area") or zone["zone_id"],
                "rooms": [],
            },
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def builder_room_create(request):
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    name = str(data.get("name") or "").strip()
    desc = str(data.get("desc") or "").strip()
    environment = str(data.get("environment") or "city").strip().lower()
    zone_id = _normalize_zone_id(data.get("zone_id") or "")
    map_x = _coerce_map_coordinate(data.get("map_x", data.get("x")), 0)
    map_y = _coerce_map_coordinate(data.get("map_y", data.get("y")), 0)
    map_layer = _coerce_map_coordinate(data.get("map_layer"), 0)

    if not name:
        return JsonResponse({"status": "error", "error": "name is required"}, status=400)
    if not desc:
        return JsonResponse({"status": "error", "error": "desc is required"}, status=400)
    if not zone_id:
        return JsonResponse({"status": "error", "error": "zone_id is required"}, status=400)
    if _get_builder_zone_meta(zone_id) is None:
        return JsonResponse({"status": "error", "error": "unknown zone_id"}, status=400)

    try:
        _validate_room_name_uniqueness(name, zone_id)
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    with transaction.atomic():
        room = create_object(ROOM_TYPECLASS, key=name, nohome=True)
        room.home = room
        room.db.desc = desc
        room.db.map_x = map_x
        room.db.map_y = map_y
        room.db.map_layer = map_layer
        _set_room_zone(room, zone_id)
        environment = _apply_builder_environment(room, environment)
        room.save()
        room_payload = _serialize_builder_room(room)

    return JsonResponse(
        {
            "status": "ok",
            "id": room.id,
            "environment": environment,
            "zone_id": room_payload["zone_id"],
            "room": room_payload,
            "map_payload": _serialize_builder_local_map_payload(room) if not room_payload["zone_id"] else None,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def builder_room_delete(request, room_id):
    room = _get_room(room_id)
    with transaction.atomic():
        for existing in _get_builder_exits(room):
            exit_service.delete_exit(room, existing["direction"])

        for source_room in _room_queryset():
            if int(source_room.id) == int(room.id):
                continue
            for existing in _get_builder_exits(source_room):
                if int(existing["target_id"]) == int(room.id):
                    exit_service.delete_exit(source_room, existing["direction"])

        room.delete()
    return JsonResponse({"status": "ok", "id": int(room_id)})


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
    raw_zone_id = data["zone_id"] if "zone_id" in data else (_get_room_zone_id(room) or "")
    zone_id = _normalize_zone_id(raw_zone_id)
    map_x = _coerce_map_coordinate(data.get("map_x"), getattr(getattr(room, "db", None), "map_x", 0) or 0)
    map_y = _coerce_map_coordinate(data.get("map_y"), getattr(getattr(room, "db", None), "map_y", 0) or 0)
    map_layer = _coerce_map_coordinate(data.get("map_layer"), getattr(getattr(room, "db", None), "map_layer", 0) or 0)
    try:
        exits = _normalize_builder_exits(data.get("exits") or [])
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    if not name:
        return JsonResponse({"status": "error", "error": "name is required"}, status=400)
    if not desc:
        return JsonResponse({"status": "error", "error": "desc is required"}, status=400)
    if not zone_id:
        return JsonResponse({"status": "error", "error": "zone_id is required"}, status=400)
    if _get_builder_zone_meta(zone_id) is None:
        return JsonResponse({"status": "error", "error": "unknown zone_id"}, status=400)

    try:
        _validate_room_name_uniqueness(name, zone_id, exclude_room_id=room.id)
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    with transaction.atomic():
        room.db_key = name
        room.db.desc = desc
        room.db.map_x = map_x
        room.db.map_y = map_y
        room.db.map_layer = map_layer
        _set_room_zone(room, zone_id)
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
            "map_payload": _serialize_builder_local_map_payload(room) if not room_payload["zone_id"] else None,
        }
    )