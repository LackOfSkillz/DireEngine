import json
import re
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import yaml
from anthropic import APIConnectionError, APIError, APITimeoutError, AuthenticationError, BadRequestError, PermissionDeniedError, RateLimitError
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from server.systems.zone_room_npc_assignments import normalize_builder_reference_ids
from world.builder.prompting.room_description_prompt import build_room_description_user_message, determine_applicable_state_groups, determine_applicable_states
from world.builder.services.anthropic_client import RoomDescriptionGenerator
from server.systems.zone_room_item_assignments import normalize_room_item_entries
from web.character_helpers import parse_request_data
from world.area_forge import map_api
from world.area_forge.map_filtering import filter_zone_rooms_and_edges
from world.area_forge.paths import artifact_paths
from world.area_forge.serializer import load_review_graph, save_review_graph
from world.builder.schemas.generation_context_schema import load_zone_vocab, normalize_generation_context
from world.builder.schemas.room_tag_schema import load_atmosphere_vocab, load_room_vocab, normalize_room_quest_hooks, normalize_room_tags
from world.builder.scoring.zone_scorer import score_zone
from world.builder.schemas.terrain_schema import load_terrain_vocab as _schema_load_terrain_vocab, normalize_room_terrain
from world.builder.services import exit_service, zone_service
from world.worlddata.services.import_zone_service import DEFAULT_ROOM_TYPECLASS, load_zone


YAML_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


ROOM_TYPECLASS = DEFAULT_ROOM_TYPECLASS
EXIT_TYPECLASS = "typeclasses.exits.Exit"
SLOW_EXIT_TYPECLASS = "typeclasses.exits_slow.SlowDireExit"
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


def _yaml_safe_load(source):
    return yaml.load(source, Loader=YAML_SAFE_LOADER) or {}


def _worlddata_zones_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "worlddata" / "zones"


def _worlddata_zone_path(zone_id):
    normalized_zone_id = _normalize_zone_id(zone_id)
    if not normalized_zone_id:
        raise ValueError("zone_id is required")
    return _worlddata_zones_dir() / f"{normalized_zone_id}.yaml"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _review_graph_path(zone_id) -> Path:
    normalized_zone_id = _normalize_zone_id(zone_id)
    if not normalized_zone_id:
        raise ValueError("zone_id is required")
    return _repo_root() / artifact_paths(normalized_zone_id)["review_graph"]


def _normalize_review_graph_payload(data, fallback_zone_id=""):
    if not isinstance(data, dict):
        raise ValueError("Review graph payload must be an object.")
    zone_id = _normalize_zone_id(data.get("zone_id") or fallback_zone_id)
    if not zone_id:
        raise ValueError("zone_id is required")

    normalized_nodes = []
    seen_node_ids = set()
    for index, node in enumerate(list(data.get("nodes") or []), start=1):
        payload = dict(node or {})
        node_id = str(payload.get("id") or f"node-{index:03d}").strip()
        if not node_id or node_id in seen_node_ids:
            raise ValueError(f"Duplicate or missing node id: {node_id or '<blank>'}")
        seen_node_ids.add(node_id)
        normalized_nodes.append({
            "id": node_id,
            "x": int(payload.get("x") or 0),
            "y": int(payload.get("y") or 0),
            "name": str(payload.get("name") or ""),
        })

    def normalize_edge(edge, fallback_prefix, index):
        payload = dict(edge or {})
        return {
            "id": str(payload.get("id") or f"{fallback_prefix}-{index:03d}").strip(),
            "source": str(payload.get("source") or "").strip(),
            "target": str(payload.get("target") or "").strip(),
            "type": str(payload.get("type") or fallback_prefix).strip().lower(),
            "label": str(payload.get("label") or "").strip().lower(),
        }

    normalized_edges = [normalize_edge(edge, "spatial", index) for index, edge in enumerate(list(data.get("edges") or []), start=1)]
    normalized_special_edges = [normalize_edge(edge, "special", index) for index, edge in enumerate(list(data.get("special_edges") or []), start=1)]

    node_id_set = {node["id"] for node in normalized_nodes}
    for edge in normalized_edges + normalized_special_edges:
        if edge["source"] not in node_id_set or edge["target"] not in node_id_set:
            raise ValueError(f"Edge '{edge['id']}' points to missing node(s).")

    payload = {
        "zone_id": zone_id,
        "source_image": str(data.get("source_image") or "").replace("\\", "/"),
        "nodes": sorted(normalized_nodes, key=lambda node: str(node["id"])),
        "edges": sorted([
            {
                "id": edge["id"],
                "source": edge["source"],
                "target": edge["target"],
                "type": "spatial",
            }
            for edge in normalized_edges
        ], key=lambda edge: str(edge["id"])),
        "special_edges": sorted([
            {
                "id": edge["id"],
                "source": edge["source"],
                "target": edge["target"],
                "label": edge["label"],
            }
            for edge in normalized_special_edges
        ], key=lambda edge: str(edge["id"])),
    }
    payload["source_image_url"] = f"/builder/api/review-graph/{zone_id}/image/" if payload["source_image"] else ""
    return payload


def _load_review_graph_artifact(zone_id):
    file_path = _review_graph_path(zone_id)
    payload = load_review_graph(file_path)
    if not payload:
        raise Http404("Review graph not found")
    return _normalize_review_graph_payload(payload, fallback_zone_id=zone_id)


def _write_review_graph_artifact(zone_id, payload):
    normalized = _normalize_review_graph_payload(payload, fallback_zone_id=zone_id)
    file_path = _review_graph_path(normalized["zone_id"])
    save_review_graph(file_path, normalized)
    return normalized


def _normalize_population_storage_choice(value):
    choice = str(value or "").strip().lower()
    if choice in {"placements", "rooms"}:
        return choice
    return "unknown"


def _detect_population_storage(raw_zone_data, kind):
    placements = dict(raw_zone_data.get("placements") or {}) if isinstance(raw_zone_data, dict) else {}
    rooms = list(raw_zone_data.get("rooms") or []) if isinstance(raw_zone_data, dict) else []
    placement_entries = list(placements.get(kind) or []) if kind in placements else []
    room_entries = []
    room_has_key = False
    for room in rooms:
        if not isinstance(room, dict):
            continue
        if kind in room:
            room_has_key = True
            room_entries.extend(list(room.get(kind) or []))

    if placement_entries:
        return "placements"
    if room_entries:
        return "rooms"
    if room_has_key:
        return "rooms"
    if kind in placements:
        return "placements"
    return "unknown"


def _build_direbuilder_metadata(raw_zone_data):
    return {
        "population_storage": {
            "npcs": _detect_population_storage(raw_zone_data, "npcs"),
            "items": _detect_population_storage(raw_zone_data, "items"),
        },
    }


def _serialize_review_graphs():
    build_root = _repo_root() / "build"
    review_graphs = []
    for file_path in sorted(build_root.glob("*/review_graph.json")):
        payload = load_review_graph(file_path)
        if not payload:
            continue
        normalized = _normalize_review_graph_payload(payload, fallback_zone_id=file_path.parent.name)
        review_graphs.append(
            {
                "id": normalized["zone_id"],
                "name": str(normalized["zone_id"]).replace("_", " ").title(),
                "area": normalized["zone_id"],
                "rooms": [
                    {"id": node["id"], "name": node["name"] or node["id"]}
                    for node in normalized["nodes"]
                ],
            }
        )
    return review_graphs


def _builder_room_sort_key(room_data):
    room_map = dict(room_data.get("map") or {})
    return (
        int(room_map.get("layer", 0) or 0),
        int(room_map.get("y", 0) or 0),
        int(room_map.get("x", 0) or 0),
        str(room_data.get("name") or room_data.get("id") or "").lower(),
    )


def _normalize_builder_room_tags(tag_data):
    tags = dict(tag_data or {}) if isinstance(tag_data, dict) else {}
    atmosphere = tags.get("atmosphere")
    if atmosphere not in (None, "") and not isinstance(atmosphere, dict):
        raise ValueError("room atmosphere must be a mapping.")
    normalized = normalize_room_tags({**tags, "atmosphere": {}})
    atmosphere_payload = dict(atmosphere or {})
    for field in ("materials", "social_character", "surroundings", "sensory"):
        value = atmosphere_payload.get(field)
        if value in (None, ""):
            normalized["atmosphere"][field] = []
            continue
        if not isinstance(value, list):
            raise ValueError(f"room_tags.atmosphere.{field} must be a list of strings.")
        normalized["atmosphere"][field] = list(dict.fromkeys(str(item or "").strip() for item in value if str(item or "").strip()))
    normalized["atmosphere"]["upkeep"] = str(atmosphere_payload.get("upkeep") or "").strip() or None
    return normalized


def _normalize_builder_yaml_room(room_data, fallback_index=0):
    room_data = dict(room_data or {})
    room_map = dict(room_data.get("map") or {})
    normalized_room_id = str(room_data.get("id") or f"room_{fallback_index + 1}").strip()
    stateful_descs = room_data.get("stateful_descs") if isinstance(room_data.get("stateful_descs"), dict) else {}
    details = room_data.get("details") if isinstance(room_data.get("details"), dict) else {}
    room_states = room_data.get("room_states") if isinstance(room_data.get("room_states"), list) else []
    ambient = dict(room_data.get("ambient") or {}) if isinstance(room_data.get("ambient"), dict) else {}
    raw_exits = {
        **dict(room_data.get("special_exits") or {}),
        **dict(room_data.get("exits") or {}),
    }
    return {
        "id": normalized_room_id,
        "name": str(room_data.get("name") or normalized_room_id),
        "typeclass": str(room_data.get("typeclass") or DEFAULT_ROOM_TYPECLASS).strip() or DEFAULT_ROOM_TYPECLASS,
        "canonical_image": str(room_data.get("canonical_image") or "").strip(),
        "short_desc": room_data.get("short_desc"),
        "desc": str(room_data.get("desc") or ""),
        "stateful_descs": {
            str(key or "").strip().lower(): str(value or "")
            for key, value in stateful_descs.items()
            if str(key or "").strip()
        },
        "details": {
            str(key or "").strip().lower(): str(value or "")
            for key, value in details.items()
            if str(key or "").strip()
        },
        "room_states": [
            str(state or "").strip().lower()
            for state in room_states
            if str(state or "").strip()
        ],
        "ambient": {
            "rate": max(0, _coerce_map_coordinate(ambient.get("rate"), 0)),
            "messages": [
                str(message or "")
                for message in list(ambient.get("messages") or [])
                if str(message or "")
            ],
        },
        "environment": str(room_data.get("environment") or "city").strip().lower() or "city",
        "terrain": normalize_room_terrain(room_data.get("terrain")),
        "quest_hooks": normalize_room_quest_hooks(room_data.get("quest_hooks")),
        "npcs": normalize_builder_reference_ids(room_data.get("npcs") or []),
        "tags": _normalize_builder_room_tags(room_data.get("tags")),
        "items": normalize_room_item_entries(room_data.get("items") or []),
        "zone_id": "",
        "map": {
            "x": _coerce_optional_map_coordinate(room_map.get("x", room_data.get("map_x", room_data.get("x")))),
            "y": _coerce_optional_map_coordinate(room_map.get("y", room_data.get("map_y", room_data.get("y")))),
            "layer": _coerce_map_coordinate(room_map.get("layer"), 0),
        },
        "exits": {
            str(direction or "").strip().lower(): (
                {
                    "target": str((spec or {}).get("target") or (spec or {}).get("room_id") or (spec or {}).get("target_id") or "").strip(),
                    "typeclass": str((spec or {}).get("typeclass") or EXIT_TYPECLASS).strip() or EXIT_TYPECLASS,
                    "speed": str((spec or {}).get("speed") or "").strip().lower(),
                    "travel_time": max(0, _coerce_map_coordinate((spec or {}).get("travel_time"), 0)),
                }
                if isinstance(spec, dict)
                else {
                    "target": str(spec or "").strip(),
                    "typeclass": EXIT_TYPECLASS,
                    "speed": "",
                    "travel_time": 0,
                }
            )
            for direction, spec in raw_exits.items()
            if str(direction or "").strip()
            and (
                str((spec or {}).get("target") or (spec or {}).get("room_id") or (spec or {}).get("target_id") or "").strip()
                if isinstance(spec, dict)
                else str(spec or "").strip()
            )
        },
    }


def _filter_builder_zone_payload(payload):
    rooms = [dict(room_data or {}) for room_data in list((payload or {}).get("rooms") or [])]
    edges = []
    edge_specs = {}

    for room_data in rooms:
        room_id = str(room_data.get("id") or "").strip()
        exits = dict(room_data.get("exits") or {})
        for direction, spec in exits.items():
            normalized_direction = str(direction or "").strip().lower()
            target_id = str((spec or {}).get("target") or "").strip()
            if not normalized_direction or not target_id:
                continue
            edge_key = (room_id, target_id, normalized_direction)
            edges.append({"from": room_id, "to": target_id, "dir": normalized_direction})
            edge_specs[edge_key] = dict(spec or {})

    filtered_rooms, filtered_edges = filter_zone_rooms_and_edges(rooms, edges)
    filtered_rooms_by_id = {room_data["id"]: room_data for room_data in filtered_rooms}
    for room_data in filtered_rooms:
        room_data["exits"] = {}
    for edge in filtered_edges:
        edge_key = (edge.get("from"), edge.get("to"), edge.get("dir"))
        source_room = filtered_rooms_by_id.get(edge.get("from"))
        if not source_room:
            continue
        source_room.setdefault("exits", {})[edge.get("dir")] = dict(edge_specs.get(edge_key) or {})

    for room_data in filtered_rooms:
        room_data["exits"] = dict(sorted((room_data.get("exits") or {}).items()))

    return {**payload, "rooms": filtered_rooms}


def _normalize_builder_zone_payload(data, fallback_zone_id="", direbuilder_metadata=None):
    if not isinstance(data, dict):
        raise ValueError("Zone payload must be an object.")
    zone_id = _normalize_zone_id(data.get("zone_id") or fallback_zone_id)
    if not zone_id:
        raise ValueError("zone_id is required")
    placements = dict(data.get("placements") or {})
    rooms = [
        _normalize_builder_yaml_room(room_data, fallback_index=index)
        for index, room_data in enumerate(list(data.get("rooms") or []))
    ]
    rooms.sort(key=_builder_room_sort_key)
    for room_data in rooms:
        room_data["zone_id"] = zone_id
    metadata = dict(direbuilder_metadata or _build_direbuilder_metadata(data))
    population_storage = dict(metadata.get("population_storage") or {})
    return {
        "schema_version": str(data.get("schema_version") or "v1"),
        "zone_id": zone_id,
        "name": str(data.get("name") or _titleize_zone_id(zone_id)),
        "zone_type": str(data.get("zone_type") or "").strip() or None,
        "generation_context": normalize_generation_context(data.get("generation_context")),
        "geographic_structure": dict(data.get("geographic_structure") or {}),
        "rooms": rooms,
        "placements": {
            "npcs": list(placements.get("npcs") or []),
            "items": list(placements.get("items") or []),
        },
        "_direbuilder": {
            "population_storage": {
                "npcs": _normalize_population_storage_choice(population_storage.get("npcs")),
                "items": _normalize_population_storage_choice(population_storage.get("items")),
            },
        },
    }


def _load_builder_zone_yaml(zone_id):
    file_path = _worlddata_zone_path(zone_id)
    if not file_path.exists():
        raise Http404("Zone not found")
    with file_path.open(encoding="utf-8") as file_handle:
        data = _yaml_safe_load(file_handle)
    payload = _normalize_builder_zone_payload(
        data,
        fallback_zone_id=zone_id,
        direbuilder_metadata=_build_direbuilder_metadata(data),
    )
    payload = _filter_builder_zone_payload(payload)
    payload["area"] = payload["zone_id"]
    return payload


def _prepare_builder_zone_yaml_for_dump(zone_id, payload):
    metadata = dict((payload or {}).get("_direbuilder") or {}) if isinstance(payload, dict) else {}
    normalized_payload = _normalize_builder_zone_payload(
        payload,
        fallback_zone_id=zone_id,
        direbuilder_metadata=metadata,
    )
    population_storage = dict((normalized_payload.get("_direbuilder") or {}).get("population_storage") or {})
    for kind in ("npcs", "items"):
        storage_choice = _normalize_population_storage_choice(population_storage.get(kind))
        if storage_choice == "placements":
            for room_data in normalized_payload["rooms"]:
                room_data.pop(kind, None)
        else:
            for room_data in normalized_payload["rooms"]:
                room_data[kind] = list(room_data.get(kind) or [])
    return normalized_payload


def _write_builder_zone_yaml(zone_id, payload):
    normalized_payload = _prepare_builder_zone_yaml_for_dump(zone_id, payload)
    yaml_payload = dict(normalized_payload)
    yaml_payload.pop("_direbuilder", None)
    file_path = _worlddata_zone_path(normalized_payload["zone_id"])
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file_handle:
        # YAML formatting normalization is intentional for DireBuilder saves.
        yaml.safe_dump(yaml_payload, file_handle, sort_keys=False)
    canonical_payload = _load_builder_zone_yaml(normalized_payload["zone_id"])
    canonical_payload["area"] = canonical_payload["zone_id"]
    return canonical_payload


def _serialize_yaml_builder_zones():
    zones = []
    for file_path in sorted(_worlddata_zones_dir().glob("*.yaml")):
        if file_path.name.endswith(".raw.yaml"):
            continue
        with file_path.open(encoding="utf-8") as file_handle:
            data = _yaml_safe_load(file_handle)
        payload = _normalize_builder_zone_payload(data, fallback_zone_id=file_path.stem)
        zones.append(
            {
                "id": payload["zone_id"],
                "name": payload["name"],
                "area": payload["zone_id"],
                "rooms": [
                    {"id": room_data["id"], "name": room_data["name"]}
                    for room_data in payload["rooms"]
                ],
            }
        )
    return zones


def _normalize_builder_direction(direction):
    text = str(direction or "").strip().lower()
    if not text:
        return ""
    return BUILDER_DIRECTION_ALIASES.get(text, text)


def _direbuilder_label(value):
    text = str(value or "").strip()
    if not text:
        return "(not set)"
    return re.sub(r"[_\-]+", " ", text).strip().title()


def _direbuilder_summary_list(values):
    cleaned = [
        _direbuilder_label(value)
        for value in (list(values or []) if isinstance(values, (list, tuple)) else [values])
        if str(value or "").strip()
    ]
    return cleaned or ["(not set)"]


def _direbuilder_room_exits(room):
    exits = []
    for direction, spec in dict(room.get("exits") or {}).items():
        payload = dict(spec or {}) if isinstance(spec, dict) else {"target": spec}
        target = str(payload.get("target") or payload.get("target_id") or "").strip()
        if not target:
            continue
        exits.append(
            {
                "direction": _direbuilder_label(direction),
                "target": target,
                "type": _direbuilder_label(payload.get("label") or payload.get("typeclass") or "spatial"),
            }
        )
    return exits


def _direbuilder_room_tag_sections(room):
    tags = dict(room.get("tags") or {})
    atmosphere = dict(tags.get("atmosphere") or {})
    return [
        {"title": "Structure", "values": _direbuilder_summary_list(tags.get("structure") or "")},
        {"title": "Function", "values": _direbuilder_summary_list(tags.get("specific_function") or "")},
        {"title": "Feature", "values": _direbuilder_summary_list(tags.get("named_feature") or "")},
        {"title": "Condition", "values": _direbuilder_summary_list(tags.get("condition") or "")},
        {"title": "Custom Tags", "values": _direbuilder_summary_list(tags.get("custom") or [])},
        {"title": "Atmosphere: Materials", "values": _direbuilder_summary_list(atmosphere.get("materials") or [])},
        {"title": "Atmosphere: Social Character", "values": _direbuilder_summary_list(atmosphere.get("social_character") or [])},
        {"title": "Atmosphere: Surroundings", "values": _direbuilder_summary_list(atmosphere.get("surroundings") or [])},
        {"title": "Atmosphere: Sensory", "values": _direbuilder_summary_list(atmosphere.get("sensory") or [])},
        {"title": "Atmosphere: Upkeep", "values": _direbuilder_summary_list(atmosphere.get("upkeep") or "")},
    ]


@lru_cache(maxsize=1)
def _load_direbuilder_tooltips() -> dict[str, dict[str, object]]:
    path = _repo_root() / "world" / "builder" / "content" / "tooltips.yaml"
    if not path.exists():
        return {}
    payload = _yaml_safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for key, value in payload.items():
        field_path = str(key or "").strip()
        if not field_path or not isinstance(value, dict):
            continue
        normalized[field_path] = value
    return normalized


@lru_cache(maxsize=1)
def _load_terrain_vocab() -> dict[str, list[str]]:
    return _schema_load_terrain_vocab()


@lru_cache(maxsize=1)
def _load_forage_catalog() -> dict[str, object]:
    path = _repo_root() / "world" / "builder" / "content" / "forage_catalog.yaml"
    with path.open(encoding="utf-8") as handle:
        payload = _yaml_safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("forage catalog must be a mapping.")
    return payload


@lru_cache(maxsize=1)
def _build_terrain_summary() -> dict[str, dict[str, object]]:
    terrain_vocab = _load_terrain_vocab()
    summary_keys = [*terrain_vocab.get("primary", []), *terrain_vocab.get("secondary", [])]
    summaries: dict[str, dict[str, object]] = {
        key: {"total": 0, "healing": 0, "items": [], "_healing_items": []}
        for key in summary_keys
    }

    for group_entries in _load_forage_catalog().values():
        if not isinstance(group_entries, dict):
            continue
        for payload in group_entries.values():
            if not isinstance(payload, dict) or not str(payload.get("display_name") or "").strip():
                continue
            display_name = str(payload.get("display_name") or "").strip()
            healing = bool(payload.get("healing"))
            for terrain_key in [str(value or "").strip() for value in list(payload.get("terrain") or []) if str(value or "").strip()]:
                if terrain_key not in summaries:
                    continue
                summaries[terrain_key]["total"] += 1
                summaries[terrain_key]["items"].append(display_name)
                if healing:
                    summaries[terrain_key]["healing"] += 1
                    summaries[terrain_key]["_healing_items"].append(display_name)

    normalized: dict[str, dict[str, object]] = {}
    for key, value in summaries.items():
        preferred_items = value["_healing_items"] or value["items"]
        normalized[key] = {
            "total": value["total"],
            "healing": value["healing"],
            "items": preferred_items[:5],
        }
    return normalized


def _build_direbuilder_context(request):
    zones = _serialize_yaml_builder_zones()
    zone_lookup = {str(zone.get("id") or "").strip(): zone for zone in zones}
    requested_zone_id = _normalize_zone_id(request.GET.get("zone") or "")
    current_zone_id = requested_zone_id if requested_zone_id in zone_lookup else ""
    if not current_zone_id and zones:
        current_zone_id = str(zones[0].get("id") or "").strip()

    current_zone = _load_builder_zone_yaml(current_zone_id) if current_zone_id else None
    generation_context = dict((current_zone or {}).get("generation_context") or {})
    zone_vocab = load_zone_vocab()
    room_tag_vocab = {
        "room": load_room_vocab(),
        "atmosphere": load_atmosphere_vocab(),
    }
    sample_room = dict(((current_zone or {}).get("rooms") or [None])[0] or {}) if current_zone else None

    if sample_room:
        sample_room.setdefault("short_desc", sample_room.get("name") or sample_room.get("id") or "")
        sample_room.setdefault("desc", "")
        sample_room.setdefault("details", {})
        sample_room.setdefault("stateful_descs", {})
        sample_room.setdefault("room_states", [])
        sample_room.setdefault("ambient", {"rate": 0, "messages": []})
        sample_room.setdefault("items", [])
        sample_room.setdefault("npcs", [])

    return {
        "application_name": "DireBuilder",
        "zones": zones,
        "current_zone": current_zone,
        "current_zone_id": current_zone_id,
        "current_zone_prefix": str(current_zone_id or "ZONE").upper(),
        "zone_context_raw": normalize_generation_context(generation_context),
        "zone_vocab_raw": zone_vocab,
        "room_tag_vocab_raw": room_tag_vocab,
        "terrain_vocab_data": json.dumps(_load_terrain_vocab()),
        "forage_catalog_summary": json.dumps(_build_terrain_summary()),
        "tooltips_data": json.dumps(_load_direbuilder_tooltips()),
        "zone_context": {
            "setting_type": _direbuilder_label(generation_context.get("setting_type") or ""),
            "era_feel": _direbuilder_label(generation_context.get("era_feel") or ""),
            "culture": _direbuilder_summary_list(generation_context.get("culture") or []),
            "mood": _direbuilder_summary_list(generation_context.get("mood") or []),
            "climate": _direbuilder_label(generation_context.get("climate") or ""),
            "voice": str(generation_context.get("voice") or "").strip(),
        },
        "sample_room": sample_room,
        "sample_room_exits": _direbuilder_room_exits(sample_room or {}),
        "sample_room_tag_sections": _direbuilder_room_tag_sections(sample_room or {}),
    }


def builder_view(request):
    return render(request, "webclient/builder.html", {})


def direbuilder_view(request):
    return render(request, "webclient/direbuilder.html", _build_direbuilder_context(request))


def test_builder_mockup_view(request):
    mockup_path = _repo_root() / "tmp" / "mt507_builder_mockup.html"
    if not mockup_path.exists():
        raise Http404("Builder mockup not found")
    return HttpResponse(mockup_path.read_text(encoding="utf-8"), content_type="text/html")


def _room_queryset():
    room_ids = [
        int(getattr(room, "id", 0) or 0)
        for room in ObjectDB.objects.filter(db_location__isnull=True).order_by("db_key", "id")
        if str(getattr(room, "db_typeclass_path", "") or "").startswith("typeclasses.rooms")
    ]
    return ObjectDB.objects.filter(id__in=room_ids).order_by("db_key", "id")


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


def _coerce_optional_map_coordinate(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _serialize_builder_stateful_descs(room):
    stateful_descs = {}
    for attr in list(room.db_attributes.filter(db_key__startswith="desc_").order_by("db_key")):
        state = str(getattr(attr, "key", "") or "")[5:].strip().lower()
        if state:
            stateful_descs[state] = str(getattr(attr, "value", "") or "")
    return stateful_descs


def _serialize_builder_room(room, fallback_index=0):
    zone_id = _get_room_zone_id(room)
    map_x = getattr(getattr(room, "db", None), "map_x", None)
    map_y = getattr(getattr(room, "db", None), "map_y", None)
    map_layer = getattr(getattr(room, "db", None), "map_layer", None)
    return {
        "id": room.id,
        "name": room.db_key,
        "typeclass": getattr(room, "db_typeclass_path", ROOM_TYPECLASS),
        "short_desc": _derive_builder_short_desc(room),
        "desc": str(getattr(room.db, "desc", "") or ""),
        "stateful_descs": _serialize_builder_stateful_descs(room),
        "details": {
            str(key or "").strip().lower(): str(value or "")
            for key, value in dict(getattr(room.db, "details", {}) or {}).items()
            if str(key or "").strip()
        },
        "room_states": sorted({
            str(state or "").strip().lower()
            for state in (room.tags.get(category="room_state", return_list=True) or [])
            if str(state or "").strip()
        }),
        "tags": normalize_room_tags(getattr(room.db, "room_tags", None)),
        "ambient": {
            "rate": _coerce_map_coordinate(getattr(room.db, "room_message_rate", 0), 0),
            "messages": [
                str(message or "")
                for message in list(getattr(room.db, "room_messages", []) or [])
                if str(message or "")
            ],
        },
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
    return JsonResponse(_serialize_yaml_builder_zones(), safe=False)


def builder_review_graph_list(request):
    return JsonResponse(_serialize_review_graphs(), safe=False)


def builder_zone_detail(request, zone_id):
    payload = _load_builder_zone_yaml(zone_id)
    return JsonResponse(payload)


def builder_review_graph_detail(request, zone_id):
    payload = _load_review_graph_artifact(zone_id)
    return JsonResponse(payload)


def builder_review_graph_image(request, zone_id):
    payload = _load_review_graph_artifact(zone_id)
    source_image = str(payload.get("source_image") or "").strip()
    if not source_image:
        raise Http404("Review graph source image not found")
    image_path = (_repo_root() / source_image).resolve()
    if not image_path.exists() or _repo_root() not in image_path.parents:
        raise Http404("Review graph source image not found")
    return FileResponse(image_path.open("rb"))


@csrf_exempt
@require_http_methods(["POST"])
def builder_zone_save(request):
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    try:
        payload = _write_builder_zone_yaml(data.get("zone_id") or "", data)
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    return JsonResponse({"status": "ok", "zone": payload})


def _direbuilder_error_response(code, message, status):
    return JsonResponse({"ok": False, "error": code, "message": message}, status=status)


def _direbuilder_generation_error_response(error: Exception):
    retriable = isinstance(error, (RateLimitError, APIConnectionError, APITimeoutError))
    return JsonResponse(
        {
            "ok": False,
            "error": "generation_failed",
            "message": str(error) or "Description generation failed.",
            "retriable": retriable,
        },
        status=500,
    )


def _read_json_object_request(request):
    data = parse_request_data(request)
    if isinstance(data, dict):
        return data
    try:
        parsed = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, UnicodeDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_valid_direbuilder_room_payload(room: dict) -> bool:
    if not isinstance(room, dict):
        return False
    room_id = str(room.get("id") or "").strip()
    name = str(room.get("name") or "").strip()
    environment = str(room.get("environment") or "").strip()
    tags = room.get("tags")
    return bool(room_id and name and environment and isinstance(tags, dict))


def _iter_direbuilder_runtime_zone_objects(zone_id):
    queryset = ObjectDB.objects.filter(db_tags__db_key="world_sync").distinct()
    zone_tag = f"zone:{zone_id}"
    return [obj for obj in queryset if bool(obj.tags.get(zone_tag))]


def _collect_direbuilder_live_room_ids(zone_id):
    room_ids = set()
    for obj in _iter_direbuilder_runtime_zone_objects(zone_id):
        if getattr(obj, "location", None) is not None or getattr(obj, "destination", None) is not None:
            continue
        world_id = str(getattr(getattr(obj, "db", None), "world_id", "") or "").strip()
        if world_id:
            room_ids.add(world_id)
    return room_ids


def _collect_direbuilder_live_exit_keys(zone_id, allowed_room_ids=None):
    exit_keys = set()
    allowed_room_ids = set(allowed_room_ids or [])
    for obj in _iter_direbuilder_runtime_zone_objects(zone_id):
        if getattr(obj, "destination", None) is None:
            continue
        source_room = getattr(obj, "location", None)
        if source_room is None:
            continue
        source_room_id = str(getattr(getattr(source_room, "db", None), "world_id", "") or "").strip()
        if not source_room_id:
            continue
        if allowed_room_ids and source_room_id not in allowed_room_ids:
            continue
        direction = str(getattr(obj, "key", "") or "").strip().lower()
        if not direction:
            continue
        exit_keys.add((source_room_id, direction))
    return exit_keys


def _load_direbuilder_hot_load_target(zone_id):
    file_path = _worlddata_zone_path(zone_id)
    if not file_path.exists():
        raise Http404("Zone not found")
    with file_path.open(encoding="utf-8") as file_handle:
        data = _yaml_safe_load(file_handle)
    if not isinstance(data, dict):
        raise ValueError("Zone YAML must load to a mapping.")

    room_ids = set()
    exit_keys = set()
    for room_data in list(data.get("rooms") or []):
        if not isinstance(room_data, dict):
            continue
        room_id = str(room_data.get("id") or "").strip()
        if not room_id:
            continue
        room_ids.add(room_id)
        for exits_key in ("exits", "special_exits"):
            for direction in dict(room_data.get(exits_key) or {}).keys():
                normalized_direction = str(direction or "").strip().lower()
                if normalized_direction:
                    exit_keys.add((room_id, normalized_direction))

    return {
        "room_ids": room_ids,
        "exit_keys": exit_keys,
    }


def _build_direbuilder_hot_load_summary(zone_id, live_before, target_graph, result):
    target_room_ids = set(target_graph.get("room_ids") or [])
    existing_room_ids = set(live_before.get("room_ids") or [])
    existing_exit_keys = set(live_before.get("exit_keys") or [])
    target_exit_keys = set(target_graph.get("exit_keys") or [])
    target_existing_exit_keys = {key for key in existing_exit_keys if key[0] in target_room_ids}
    warnings = list(result.get("warnings") or [])

    return {
        "zone_id": zone_id,
        "rooms_updated": len(target_room_ids & existing_room_ids),
        "rooms_created": len(target_room_ids - existing_room_ids),
        "rooms_preserved_stale": len(existing_room_ids - target_room_ids),
        "exits_updated": len(target_exit_keys & target_existing_exit_keys),
        "exits_created": len(target_exit_keys - target_existing_exit_keys),
        "exits_deleted": len(target_existing_exit_keys - target_exit_keys),
        "npcs_respawned": int(result.get("npcs") or 0),
        "items_respawned": int(result.get("items") or 0),
        "warnings": warnings,
    }


@require_http_methods(["GET"])
def direbuilder_zone_detail(request, zone_id):
    requested_zone_id = _normalize_zone_id(zone_id)
    if not requested_zone_id:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)

    try:
        payload = _load_builder_zone_yaml(requested_zone_id)
    except Http404:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)
    except Exception:
        return _direbuilder_error_response("internal_error", "Couldn't reload this zone from disk. Try again. If this persists, check the server logs.", 500)

    return JsonResponse(payload)


@require_http_methods(["GET"])
def direbuilder_zone_score(request, zone_id):
    requested_zone_id = _normalize_zone_id(zone_id)
    if not requested_zone_id:
        return JsonResponse({"error": "This zone no longer exists on disk. Reload the page to recover."}, status=500)

    try:
        payload = _load_builder_zone_yaml(requested_zone_id)
        return JsonResponse(score_zone(payload))
    except Http404:
        return JsonResponse({"error": "This zone no longer exists on disk. Reload the page to recover."}, status=500)
    except Exception as error:
        message = str(error).strip() or "Zone score failed unexpectedly. Try again. If this persists, check the server logs."
        return JsonResponse({"error": message}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def direbuilder_generate_description(request, zone_id, room_id):
    requested_zone_id = _normalize_zone_id(zone_id)
    requested_room_id = str(room_id or "").strip()
    if not requested_zone_id or not requested_room_id:
        return _direbuilder_error_response("validation_failed", "Generation request was malformed.", 400)

    try:
        zone_payload = _load_builder_zone_yaml(requested_zone_id)
    except Http404:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)
    except Exception:
        return _direbuilder_error_response("internal_error", "Couldn't load this zone from disk. Try again. If this persists, check the server logs.", 500)

    data = _read_json_object_request(request)
    room_payload = data.get("room") if isinstance(data, dict) else None
    if not _is_valid_direbuilder_room_payload(room_payload):
        return _direbuilder_error_response("validation_failed", "Generation request was malformed.", 400)

    body_room_id = str(room_payload.get("id") or "").strip()
    if body_room_id != requested_room_id:
        return _direbuilder_error_response("validation_failed", "Generation request was malformed.", 400)

    generation_context = dict(zone_payload.get("generation_context") or {})
    applicable_groups = determine_applicable_state_groups(room_payload, zone_payload, generation_context)
    applicable_states = determine_applicable_states(applicable_groups)
    generator = RoomDescriptionGenerator()

    try:
        result = generator.generate(
            {
                "room": room_payload,
                "zone": zone_payload,
                "generation_context": generation_context,
                "pass_1_user_message": build_room_description_user_message(room_payload, generation_context),
            },
            applicable_groups,
            applicable_states,
        )
    except ValueError:
        return _direbuilder_error_response("validation_failed", "Generation request was malformed.", 400)
    except (AuthenticationError, PermissionDeniedError, BadRequestError, APIError) as error:
        return _direbuilder_generation_error_response(error)
    except Exception:
        return _direbuilder_error_response("internal_error", "Description generation failed unexpectedly. Try again. If this persists, check the server logs.", 500)

    return JsonResponse(
        {
            "pass_1": result["pass_1"],
            "pass_2": result["pass_2"],
            "applicable_groups": applicable_groups,
            "applicable_states": applicable_states,
            "telemetry": {
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "elapsed_ms": result["elapsed_ms"],
                "approximate_cost_usd": result["approximate_cost_usd"],
            },
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def direbuilder_zone_save(request, zone_id):
    requested_zone_id = _normalize_zone_id(zone_id)
    if not requested_zone_id:
        return _direbuilder_error_response("validation_failed", "Save was rejected. Some fields may be invalid. Please check your edits and try again.", 400)

    file_path = _worlddata_zone_path(requested_zone_id)
    if not file_path.exists():
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)

    data = _read_json_object_request(request)
    if not isinstance(data, dict):
        return _direbuilder_error_response("validation_failed", "Save was rejected. Some fields may be invalid. Please check your edits and try again.", 400)

    body_zone_id = _normalize_zone_id(data.get("zone_id") or requested_zone_id)
    if body_zone_id and body_zone_id != requested_zone_id:
        return _direbuilder_error_response("validation_failed", "Save was rejected. Some fields may be invalid. Please check your edits and try again.", 400)

    try:
        canonical_payload = _write_builder_zone_yaml(requested_zone_id, {**data, "zone_id": requested_zone_id})
    except Http404:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)
    except ValueError as error:
        return _direbuilder_error_response("validation_failed", str(error) or "Save was rejected. Some fields may be invalid. Please check your edits and try again.", 400)
    except OSError:
        return _direbuilder_error_response("write_failed", "Couldn't write to disk. Try again, or check the server logs.", 500)
    except Exception:
        return _direbuilder_error_response("internal_error", "Save failed unexpectedly. Try again. If this persists, check the server logs.", 500)

    return JsonResponse(canonical_payload)


@csrf_exempt
@require_http_methods(["POST"])
def direbuilder_zone_hot_load(request, zone_id):
    requested_zone_id = _normalize_zone_id(zone_id)
    if not requested_zone_id:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)

    file_path = _worlddata_zone_path(requested_zone_id)
    if not file_path.exists():
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)

    try:
        target_graph = _load_direbuilder_hot_load_target(requested_zone_id)
        load_zone(requested_zone_id, dry_run=True)
    except Http404:
        return _direbuilder_error_response("zone_not_found", "This zone no longer exists on disk. Reload the page to recover.", 404)
    except ValueError:
        return _direbuilder_error_response("validation_failed", "Zone YAML is invalid. Fix the zone file on disk and try again.", 400)
    except Exception:
        return _direbuilder_error_response("internal_error", "Hot load failed unexpectedly. Try again. If this persists, check the server logs.", 500)

    live_before = {
        "room_ids": _collect_direbuilder_live_room_ids(requested_zone_id),
        "exit_keys": _collect_direbuilder_live_exit_keys(requested_zone_id, allowed_room_ids=target_graph["room_ids"]),
    }

    try:
        result = load_zone(requested_zone_id, dry_run=False, preserve_existing=True)
    except Exception:
        return _direbuilder_error_response(
            "runtime_error",
            "Hot load failed mid-operation. Live game state may be partially updated. Consider reloading the running server if behavior becomes unexpected.",
            500,
        )

    summary = _build_direbuilder_hot_load_summary(requested_zone_id, live_before, target_graph, result)
    return JsonResponse({"ok": True, "summary": summary})


@csrf_exempt
@require_http_methods(["POST"])
def builder_review_graph_save(request):
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    try:
        payload = _write_review_graph_artifact(data.get("zone_id") or "", data)
    except ValueError as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)

    return JsonResponse({"status": "ok", "review_graph": payload})


@csrf_exempt
@require_http_methods(["POST"])
def builder_zone_reload(request):
    data = parse_request_data(request)
    if not isinstance(data, dict):
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError, UnicodeDecodeError):
            data = {}

    zone_id = _normalize_zone_id(data.get("zone_id") or "")
    if not zone_id:
        return JsonResponse({"status": "error", "error": "zone_id is required"}, status=400)

    try:
        result = load_zone(zone_id, dry_run=False, preserve_existing=True)
    except Exception as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)
    return JsonResponse({"status": "ok", "result": result})


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

    file_path = _worlddata_zone_path(area)
    if file_path.exists():
        return JsonResponse({"status": "error", "error": "zone already exists"}, status=400)

    zone = _write_builder_zone_yaml(
        area,
        {
            "schema_version": "v1",
            "zone_id": area,
            "name": name,
            "rooms": [],
            "placements": {"npcs": [], "items": []},
        },
    )

    return JsonResponse(
        {
            "status": "ok",
            "zone": {
                "id": zone["zone_id"],
                "name": zone["name"],
                "area": zone.get("area") or zone["zone_id"],
                "generation_context": zone.get("generation_context"),
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
    typeclass = str(data.get("typeclass") or ROOM_TYPECLASS).strip() or ROOM_TYPECLASS
    zone_id = _normalize_zone_id(data.get("zone_id") or "")
    stateful_descs = {
        str(key or "").strip().lower(): str(value or "")
        for key, value in dict(data.get("stateful_descs") or {}).items()
        if str(key or "").strip()
    }
    details = {
        str(key or "").strip().lower(): str(value or "")
        for key, value in dict(data.get("details") or {}).items()
        if str(key or "").strip()
    }
    room_states = sorted({
        str(state or "").strip().lower()
        for state in list(data.get("room_states") or [])
        if str(state or "").strip()
    })
    ambient = dict(data.get("ambient") or {}) if isinstance(data.get("ambient"), dict) else {}
    room_tags = normalize_room_tags(data.get("tags"))
    ambient_messages = [
        str(message or "")
        for message in list(ambient.get("messages") or [])
        if str(message or "")
    ]
    ambient_rate = max(0, _coerce_map_coordinate(ambient.get("rate"), 0))

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
        room = create_object(typeclass, key=name, nohome=True)
        room.home = room
        room.db.desc = desc
        room.db.details = details
        room.db.room_messages = ambient_messages
        room.db.room_message_rate = ambient_rate
        room.db.room_tags = room_tags
        room.tags.clear(category="room_state")
        for state in room_states:
            room.tags.add(state, category="room_state")
        for state, text in stateful_descs.items():
            room.attributes.add(f"desc_{state}", text)
        if ambient_rate > 0 and ambient_messages and hasattr(room, "start_repeat_broadcast_messages"):
            room.start_repeat_broadcast_messages()
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
    typeclass = str(data.get("typeclass") or getattr(room, "db_typeclass_path", ROOM_TYPECLASS)).strip() or ROOM_TYPECLASS
    raw_zone_id = data["zone_id"] if "zone_id" in data else (_get_room_zone_id(room) or "")
    zone_id = _normalize_zone_id(raw_zone_id)
    stateful_descs = {
        str(key or "").strip().lower(): str(value or "")
        for key, value in dict(data.get("stateful_descs") or {}).items()
        if str(key or "").strip()
    }
    details = {
        str(key or "").strip().lower(): str(value or "")
        for key, value in dict(data.get("details") or {}).items()
        if str(key or "").strip()
    }
    room_states = sorted({
        str(state or "").strip().lower()
        for state in list(data.get("room_states") or [])
        if str(state or "").strip()
    })
    ambient = dict(data.get("ambient") or {}) if isinstance(data.get("ambient"), dict) else {}
    room_tags = normalize_room_tags(data.get("tags"))
    ambient_messages = [
        str(message or "")
        for message in list(ambient.get("messages") or [])
        if str(message or "")
    ]
    ambient_rate = max(0, _coerce_map_coordinate(ambient.get("rate"), 0))

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
        if getattr(room, "db_typeclass_path", "") != typeclass:
            room.swap_typeclass(typeclass, clean_attributes=False, run_start_hooks=True)
        room.db_key = name
        room.db.desc = desc
        room.db.details = details
        room.db.room_messages = ambient_messages
        room.db.room_message_rate = ambient_rate
        room.db.room_tags = room_tags
        for attr in list(room.db_attributes.filter(db_key__startswith="desc_")):
            room.attributes.remove(attr.key)
        for state, text in stateful_descs.items():
            room.attributes.add(f"desc_{state}", text)
        room.tags.clear(category="room_state")
        for state in room_states:
            room.tags.add(state, category="room_state")
        if ambient_rate > 0 and ambient_messages and hasattr(room, "start_repeat_broadcast_messages"):
            room.start_repeat_broadcast_messages()
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