from __future__ import annotations

# REVIEW PASS CONTRACT
# AreaForge creates first-pass YAML.
# This module reviews and corrects YAML against the original source map image.
# Final truth is reviewed YAML on disk.
# No direct DB writes are allowed here.

from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches
import math
from pathlib import Path
import json
import re
import shutil
import statistics

import yaml

from world.area_forge.serializer import load_review_graph, save_json

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


GRID_SIZE = 40
SPATIAL_DIRECTIONS = {
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
}
KNOWN_SPECIAL_EXIT_LABELS = [
    "go gate",
    "go bridge",
    "go path",
    "go arch",
    "go stair",
    "go stairs",
    "go ramp",
    "go dock",
    "go pier",
    "go ferry",
    "go square",
    "go lawn",
    "go walk",
    "go plaza",
    "go hovel",
    "go haz",
    "go gate to the bottom line",
]
LANDMARK_RE = re.compile(r"\b(gate|bridge|arch|dock|pier|ferry|square|lawn|walk|plaza|map\s*[a-z0-9]+|hub|circle)\b", re.IGNORECASE)
MAP_TRANSITION_RE = re.compile(r"\bto\s+map\s*[a-z0-9]+\b", re.IGNORECASE)


@dataclass(slots=True)
class SourceImageInfo:
    path: str
    width: int
    height: int


def review_generated_zone(source_image_path: str, yaml_path: str, output_path: str | None = None) -> dict:
    """
    Load source image + first-pass YAML.
    Compare them.
    Return corrected zone data.
    """
    yaml_file = Path(yaml_path)
    project_root = _project_root_from_yaml(yaml_file)
    source_image = _load_source_image(source_image_path)
    raw_yaml = _load_yaml_bytes(yaml_file)
    first_pass_zone = _load_yaml_data(raw_yaml, yaml_file)
    zone_id = str(first_pass_zone.get("zone_id") or yaml_file.stem).strip().lower()
    backup_paths = _create_raw_backup(yaml_file, project_root, zone_id)
    review_graph = _load_optional_review_graph(project_root, zone_id, yaml_file)
    review_model = _build_review_model(
        zone_data=first_pass_zone,
        review_graph=review_graph,
        source_image=source_image,
        project_root=project_root,
    )
    report = _apply_review_pass(review_model)
    corrected_zone = _serialize_zone(review_model)
    _validate_zone_schema(corrected_zone)

    resolved_output = Path(output_path) if output_path else yaml_file
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    with resolved_output.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(corrected_zone, file_handle, sort_keys=False, allow_unicode=False)

    report_path = project_root / "build" / zone_id / "review_report.json"
    report_payload = {
        "zone_id": zone_id,
        "source_image": source_image.path,
        "yaml_path": str(yaml_file),
        "output_path": str(resolved_output),
        "review_graph_path": review_model.get("review_graph_path"),
        "backup_paths": {key: str(value) for key, value in backup_paths.items()},
        **report,
    }
    save_json(report_path, report_payload)

    return {
        "zone_id": zone_id,
        "output_path": str(resolved_output),
        "report_path": str(report_path),
        "review_graph_path": review_model.get("review_graph_path"),
        "zone_data": corrected_zone,
        "report": report_payload,
    }


def _project_root_from_yaml(yaml_file: Path) -> Path:
    for parent in yaml_file.parents:
        if parent.name == "zones" and parent.parent.name == "worlddata":
            return parent.parent.parent
    return Path(__file__).resolve().parents[3]


def _load_source_image(source_image_path: str) -> SourceImageInfo:
    image_path = Path(source_image_path)
    if Image is None:
        raise RuntimeError("Pillow is required for generated YAML review.")
    if not image_path.exists():
        raise FileNotFoundError(f"Source map image was not found: {image_path}")
    with Image.open(image_path) as image_handle:
        width, height = image_handle.size
    return SourceImageInfo(path=str(image_path), width=int(width), height=int(height))


def _load_yaml_bytes(yaml_file: Path) -> bytes:
    if not yaml_file.exists():
        raise FileNotFoundError(f"Zone YAML was not found: {yaml_file}")
    return yaml_file.read_bytes()


def _load_yaml_data(raw_yaml: bytes, yaml_file: Path) -> dict[str, object]:
    data = yaml.safe_load(raw_yaml.decode("utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"Zone YAML is not a mapping: {yaml_file}")
    return dict(data)


def _create_raw_backup(yaml_file: Path, project_root: Path, zone_id: str) -> dict[str, Path]:
    sibling_backup = yaml_file.with_suffix(".raw.yaml")
    sibling_backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(yaml_file, sibling_backup)

    artifact_backup = project_root / "build" / zone_id / "review_backup" / yaml_file.name
    artifact_backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(yaml_file, artifact_backup)
    return {
        "raw_yaml": sibling_backup,
        "artifact_backup": artifact_backup,
    }


def _load_optional_review_graph(project_root: Path, zone_id: str, yaml_file: Path) -> dict[str, object] | None:
    candidates = [
        project_root / "build" / zone_id / "review_graph.json",
        yaml_file.parent.parent.parent / "build" / zone_id / "review_graph.json" if len(yaml_file.parents) >= 3 else None,
        yaml_file.with_name("review_graph.json"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            payload = _load_review_graph_payload(candidate)
            if isinstance(payload, Mapping):
                review_graph = dict(payload)
                review_graph["__path__"] = str(candidate)
                return review_graph
    return None


def _load_review_graph_payload(path: Path) -> dict[str, object] | None:
    try:
        payload = load_review_graph(path)
    except json.JSONDecodeError:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping):
        return dict(payload)
    return None


def _build_review_model(
    zone_data: Mapping[str, object],
    review_graph: Mapping[str, object] | None,
    source_image: SourceImageInfo,
    project_root: Path,
) -> dict[str, object]:
    zone_id = str(zone_data.get("zone_id") or "").strip().lower()
    rooms = [_normalize_room(room, zone_id) for room in list(zone_data.get("rooms") or [])]
    room_by_id = {room["id"]: room for room in rooms}
    room_by_coord = {(room["map_x"], room["map_y"]): room["id"] for room in rooms}
    spatial_exits, special_exits = _collect_yaml_exits(rooms)
    adjacency, adjacency_tags = _build_yaml_graph(rooms)
    source_nodes, source_edges, source_labels, source_positions = _build_source_graph(review_graph, rooms)

    model = {
        "zone_id": zone_id,
        "schema_version": zone_data.get("schema_version", "v1"),
        "name": zone_data.get("name") or zone_id,
        "rooms": rooms,
        "room_lookup": room_by_id,
        "room_by_id": room_by_id,
        "room_by_coord": room_by_coord,
        "spatial_exits": spatial_exits,
        "special_exits": special_exits,
        "adjacency": adjacency,
        "adjacency_tags": adjacency_tags,
        "source_nodes": source_nodes,
        "source_edges": source_edges,
        "source_labels": source_labels,
        "source_positions": source_positions,
        "review_graph": dict(review_graph or {}),
        "review_graph_path": None if not review_graph else review_graph.get("__path__"),
        "source_image": {
            "path": source_image.path,
            "width": source_image.width,
            "height": source_image.height,
        },
        "project_root": str(project_root),
        "anchor_room_ids": set(),
        "cluster_groups": [],
        "chain_groups": [],
        "source_spatial_pairs": set(),
        "source_special_pairs": {},
    }
    _attach_room_review_metadata(model)
    return model


def _normalize_room(raw_room: object, zone_id: str) -> dict[str, object]:
    room = deepcopy(dict(raw_room or {}))
    room_id = str(room.get("id") or "").strip()
    if not room_id:
        raise ValueError("Every room must define an id.")
    room_map = dict(room.get("map") or {})
    room["zone_id"] = str(room.get("zone_id") or zone_id).strip().lower() or zone_id
    room["map"] = room_map
    room["map_x"] = int(room_map.get("x", 0) or 0)
    room["map_y"] = int(room_map.get("y", 0) or 0)
    room["map_layer"] = int(room_map.get("layer", 0) or 0)
    room["exits"] = dict(room.get("exits") or {})
    room["special_exits"] = dict(room.get("special_exits") or {})
    room["name"] = str(room.get("name") or room_id).strip() or room_id
    room["review"] = {
        "review_confidence": 1.0,
        "suspected_layout_drift": False,
        "suspected_missing_exit": False,
        "suspected_bad_label": False,
    }
    return room


def _collect_yaml_exits(rooms: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    spatial = []
    special = []
    for room in rooms:
        for direction, spec in sorted(room["exits"].items()):
            spatial.append({
                "source": room["id"],
                "target": str((spec or {}).get("target") or "").strip(),
                "direction": str(direction).strip().lower(),
                "spec": dict(spec or {}),
            })
        for label, spec in sorted(room["special_exits"].items()):
            special.append({
                "source": room["id"],
                "target": str((spec or {}).get("target") or "").strip(),
                "label": str(label).strip(),
                "spec": dict(spec or {}),
            })
    return spatial, special


def _build_yaml_graph(rooms: list[dict[str, object]]) -> tuple[dict[str, set[str]], dict[str, dict[str, set[str]]]]:
    adjacency = {room["id"]: set() for room in rooms}
    adjacency_tags = {
        room["id"]: {
            "spatial": set(),
            "special": set(),
        }
        for room in rooms
    }
    for room in rooms:
        for direction, spec in room["exits"].items():
            target = str((spec or {}).get("target") or "").strip()
            if target:
                adjacency[room["id"]].add(target)
                adjacency_tags[room["id"]]["spatial"].add(target)
        for _, spec in room["special_exits"].items():
            target = str((spec or {}).get("target") or "").strip()
            if target:
                adjacency[room["id"]].add(target)
                adjacency_tags[room["id"]]["special"].add(target)
    return adjacency, adjacency_tags


def _build_source_graph(
    review_graph: Mapping[str, object] | None,
    rooms: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, tuple[int, int]]]:
    nodes = []
    edges = []
    labels = []
    source_positions: dict[str, tuple[int, int]] = {}
    if not review_graph:
        return nodes, edges, labels, source_positions

    room_id_lookup = {str(room["id"]).strip().lower(): str(room["id"]).strip() for room in rooms if str(room.get("id") or "").strip()}
    raw_nodes = [dict(node) for node in list(review_graph.get("nodes") or []) if str(node.get("id") or "").strip()]
    source_positions = _normalize_source_positions(raw_nodes)
    for node in raw_nodes:
        node_id = _resolve_room_id(str(node.get("id") or "").strip(), room_id_lookup)
        if not node_id:
            continue
        label = str(node.get("name") or "").strip()
        nodes.append({
            "id": node_id,
            "name": label,
            "x": int(node.get("x") or 0),
            "y": int(node.get("y") or 0),
            "map_x": source_positions.get(node_id, (0, 0))[0],
            "map_y": source_positions.get(node_id, (0, 0))[1],
        })
        if label:
            labels.append({"kind": "room", "room_id": node_id, "text": label})

    for edge in list(review_graph.get("edges") or []):
        source = _resolve_room_id(str(edge.get("source") or "").strip(), room_id_lookup)
        target = _resolve_room_id(str(edge.get("target") or "").strip(), room_id_lookup)
        if not source or not target:
            continue
        edges.append({
            "source": source,
            "target": target,
            "kind": "spatial",
            "label": str(edge.get("label") or "").strip().lower(),
        })

    for edge in list(review_graph.get("special_edges") or []):
        source = _resolve_room_id(str(edge.get("source") or "").strip(), room_id_lookup)
        target = _resolve_room_id(str(edge.get("target") or "").strip(), room_id_lookup)
        label = str(edge.get("label") or "").strip()
        if not source or not target or not label:
            continue
        corrected_label = _correct_special_label(label)
        edges.append({
            "source": source,
            "target": target,
            "kind": "special",
            "label": corrected_label,
        })
        labels.append({"kind": "exit", "source": source, "target": target, "text": corrected_label})

    for candidate in list(review_graph.get("ocr_label_candidates") or []):
        text = str(candidate.get("text") or candidate.get("label") or "").strip()
        if text:
            labels.append({"kind": "ocr", "text": text})

    room_ids = {room["id"] for room in rooms}
    nodes = [node for node in nodes if node["id"] in room_ids]
    edges = [edge for edge in edges if edge["source"] in room_ids and edge["target"] in room_ids]
    return nodes, edges, labels, source_positions


def _resolve_room_id(raw_room_id: str, room_id_lookup: Mapping[str, str]) -> str:
    normalized = str(raw_room_id or "").strip()
    if not normalized:
        return ""
    return str(room_id_lookup.get(normalized.lower()) or normalized)


def _normalize_source_positions(raw_nodes: list[dict[str, object]]) -> dict[str, tuple[int, int]]:
    if not raw_nodes:
        return {}
    xs = [int(node.get("x") or 0) for node in raw_nodes]
    ys = [int(node.get("y") or 0) for node in raw_nodes]
    x_positions = _diagrammatic_axis_positions(xs)
    y_positions = _diagrammatic_axis_positions(ys, invert=True)
    positions = {}
    for node in raw_nodes:
        node_id = str(node.get("id") or "").strip()
        raw_x = int(node.get("x") or 0)
        raw_y = int(node.get("y") or 0)
        map_x = x_positions[raw_x]
        map_y = y_positions[raw_y]
        positions[node_id] = (map_x, map_y)
    return positions


def _diagrammatic_axis_positions(values: list[int], invert: bool = False) -> dict[int, int]:
    unique_values = sorted(set(int(value) for value in values))
    if not unique_values:
        return {}
    clustered_values = _cluster_axis_values(unique_values)
    mapped_centers = _map_axis_centers(clustered_values)
    positions = {}
    for group in clustered_values:
        center = group["center"]
        position = mapped_centers[center]
        if invert:
            position *= -1
        for value in group["values"]:
            positions[value] = position
    return positions


def _cluster_axis_values(values: list[int]) -> list[dict[str, object]]:
    if not values:
        return []
    groups: list[list[int]] = [[values[0]]]
    for value in values[1:]:
        if value - groups[-1][-1] <= 1:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [{"values": group, "center": int(round(statistics.mean(group)))} for group in groups]


def _map_axis_centers(groups: list[dict[str, object]]) -> dict[int, int]:
    if not groups:
        return {}
    centers = [int(group["center"]) for group in groups]
    mapped = {centers[0]: 0}
    current = 0
    previous = centers[0]
    for center in centers[1:]:
        current += _diagrammatic_step(center - previous)
        mapped[center] = current
        previous = center
    midpoint = int(round((min(mapped.values()) + max(mapped.values())) / 2))
    return {center: position - midpoint for center, position in mapped.items()}


def _diagrammatic_step(raw_gap: int) -> int:
    gap = abs(int(raw_gap))
    if gap <= 2:
        return 3
    if gap <= 6:
        return 6
    if gap <= 10:
        return 9
    if gap <= 16:
        return 14
    if gap <= 24:
        return 20
    if gap <= 40:
        return 28
    return max(30, int(round(gap * 0.8)))


def _median_gap(values: list[int]) -> float:
    unique_values = sorted(set(int(value) for value in values))
    gaps = [b - a for a, b in zip(unique_values, unique_values[1:]) if (b - a) > 0]
    if not gaps:
        return GRID_SIZE
    return max(1.0, float(statistics.median(gaps)))


def _attach_room_review_metadata(model: dict[str, object]) -> None:
    source_positions = model["source_positions"]
    adjacency = model["adjacency"]
    room_lookup = model["room_lookup"]
    source_neighbors = defaultdict(set)
    source_labels = {entry.get("room_id"): entry.get("text") for entry in model["source_labels"] if entry.get("kind") == "room"}
    for edge in model["source_edges"]:
        source_neighbors[edge["source"]].add(edge["target"])
        if edge["kind"] == "spatial":
            source_neighbors[edge["target"]].add(edge["source"])

    for room_id, room in room_lookup.items():
        desired = source_positions.get(room_id)
        current = (room["map_x"], room["map_y"])
        layout_drift = False if desired is None else _manhattan_distance(current, desired) >= GRID_SIZE * 2
        missing_exit = bool(source_neighbors.get(room_id, set()) - adjacency.get(room_id, set()))
        bad_label = False
        source_label = str(source_labels.get(room_id) or "").strip()
        if source_label and source_label.lower() != room["name"].strip().lower() and not _looks_like_generated_room_name(room["name"]):
            bad_label = True
        review_confidence = 1.0
        if layout_drift:
            review_confidence -= 0.25
        if missing_exit:
            review_confidence -= 0.35
        if bad_label:
            review_confidence -= 0.15
        room["review"] = {
            "review_confidence": max(0.0, round(review_confidence, 2)),
            "suspected_layout_drift": layout_drift,
            "suspected_missing_exit": missing_exit,
            "suspected_bad_label": bad_label,
        }


def _looks_like_generated_room_name(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]+_\d+_\d+", str(value or "").strip().lower()))


def _apply_review_pass(model: dict[str, object]) -> dict[str, object]:
    report = {
        "moved_rooms": [],
        "added_exits": [],
        "removed_exits": [],
        "corrected_special_exits": [],
        "corrected_labels": [],
        "unresolved_ambiguities": [],
    }
    _index_source_edges(model)
    _anchor_landmarks(model)
    _detect_long_street_chains(model)
    _detect_district_clusters(model)
    _correct_room_labels(model, report)
    _apply_source_alignment(model, report)
    _straighten_chains(model, report)
    _reposition_clusters(model, report)
    _rebuild_around_anchors(model, report)
    _correct_special_exit_labels(model, report)
    _sync_connectivity(model, report)
    _resolve_coordinate_collisions(model, report)
    _refresh_indexes(model)
    return report


def _index_source_edges(model: dict[str, object]) -> None:
    spatial_pairs = set()
    special_pairs = {}
    for edge in model["source_edges"]:
        pair = (edge["source"], edge["target"])
        if edge["kind"] == "spatial":
            spatial_pairs.add(tuple(sorted(pair)))
        else:
            special_pairs[pair] = edge["label"]
    model["source_spatial_pairs"] = spatial_pairs
    model["source_special_pairs"] = special_pairs


def _anchor_landmarks(model: dict[str, object]) -> None:
    anchors = set()
    adjacency = model["adjacency"]
    for room in model["rooms"]:
        source_label = _source_room_label(model, room["id"])
        if room["special_exits"]:
            anchors.add(room["id"])
            continue
        if LANDMARK_RE.search(room["name"]) or LANDMARK_RE.search(source_label):
            anchors.add(room["id"])
            continue
        if len(adjacency.get(room["id"], set())) >= 4:
            anchors.add(room["id"])
    model["anchor_room_ids"] = anchors


def _source_room_label(model: Mapping[str, object], room_id: str) -> str:
    for label in model["source_labels"]:
        if label.get("kind") == "room" and label.get("room_id") == room_id:
            return str(label.get("text") or "")
    return ""


def _detect_long_street_chains(model: dict[str, object]) -> None:
    room_lookup = model["room_lookup"]
    adjacency = {
        room_id: {neighbor for neighbor in neighbors if neighbor in room_lookup}
        for room_id, neighbors in model["adjacency"].items()
    }
    spatial_neighbors = defaultdict(set)
    for room in model["rooms"]:
        for direction, spec in room["exits"].items():
            if direction in SPATIAL_DIRECTIONS:
                target = str((spec or {}).get("target") or "").strip()
                if target in room_lookup:
                    spatial_neighbors[room["id"]].add(target)

    visited_edges = set()
    chains = []
    for room_id, neighbors in spatial_neighbors.items():
        if len(neighbors) != 2:
            for neighbor in neighbors:
                edge_key = tuple(sorted((room_id, neighbor)))
                if edge_key in visited_edges:
                    continue
                chain = _walk_chain(room_id, neighbor, spatial_neighbors)
                for a, b in zip(chain, chain[1:]):
                    visited_edges.add(tuple(sorted((a, b))))
                if len(chain) >= 4:
                    chains.append({
                        "room_ids": chain,
                        "source_orientation": _source_chain_orientation(model, chain),
                    })
    model["chain_groups"] = chains


def _walk_chain(start: str, next_room: str, spatial_neighbors: Mapping[str, set[str]]) -> list[str]:
    chain = [start, next_room]
    previous = start
    current = next_room
    while True:
        candidates = [neighbor for neighbor in spatial_neighbors.get(current, set()) if neighbor != previous]
        if len(candidates) != 1:
            break
        following = candidates[0]
        chain.append(following)
        previous, current = current, following
        if len(spatial_neighbors.get(current, set())) != 2:
            break
    return chain


def _source_chain_orientation(model: Mapping[str, object], chain: list[str]) -> str:
    coords = [model["source_positions"].get(room_id) for room_id in chain if room_id in model["source_positions"]]
    if len(coords) < 3:
        return "unknown"
    xs = [coord[0] for coord in coords]
    ys = [coord[1] for coord in coords]
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    if dx >= dy * 2 and _max_deviation(ys) <= GRID_SIZE:
        return "horizontal"
    if dy >= dx * 2 and _max_deviation(xs) <= GRID_SIZE:
        return "vertical"
    return "bent"


def _max_deviation(values: list[int]) -> int:
    if not values:
        return 0
    median_value = int(statistics.median(values))
    return max(abs(value - median_value) for value in values)


def _detect_district_clusters(model: dict[str, object]) -> None:
    adjacency = model["adjacency"]
    source_positions = model["source_positions"]
    visited = set()
    groups = []
    for room in model["rooms"]:
        room_id = room["id"]
        if room_id in visited:
            continue
        component = _connected_component(room_id, adjacency)
        visited.update(component)
        if len(component) < 4:
            continue
        groups.append({
            "room_ids": sorted(component),
            "motif": _classify_cluster_motif(component, adjacency, source_positions),
        })
    model["cluster_groups"] = groups


def _connected_component(start: str, adjacency: Mapping[str, set[str]]) -> set[str]:
    queue = deque([start])
    visited = {start}
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


def _classify_cluster_motif(
    component: set[str],
    adjacency: Mapping[str, set[str]],
    source_positions: Mapping[str, tuple[int, int]],
) -> str:
    degrees = sorted(len(adjacency.get(room_id, set())) for room_id in component)
    if degrees and degrees[-1] >= 4:
        return "hub_spoke"
    component_coords = [source_positions.get(room_id) for room_id in component if room_id in source_positions]
    unique_xs = {coord[0] for coord in component_coords}
    unique_ys = {coord[1] for coord in component_coords}
    if len(component) >= 6 and len(unique_xs) >= 3 and len(unique_ys) >= 2:
        return "block"
    edge_count = sum(len(adjacency.get(room_id, set())) for room_id in component) // 2
    if edge_count >= len(component):
        return "loop"
    if len(component) >= 6:
        return "block"
    return "cluster"


def _correct_room_labels(model: dict[str, object], report: dict[str, object]) -> None:
    for room in model["rooms"]:
        source_label = _source_room_label(model, room["id"]).strip()
        if not source_label:
            continue
        if _looks_like_generated_room_name(room["name"]) and not _looks_like_generated_room_name(source_label):
            report["corrected_labels"].append({
                "room_id": room["id"],
                "old": room["name"],
                "new": source_label,
                "reason": "source_room_label",
            })
            room["name"] = source_label
            room["review"]["suspected_bad_label"] = False


def _apply_source_alignment(model: dict[str, object], report: dict[str, object]) -> None:
    for room in model["rooms"]:
        desired = model["source_positions"].get(room["id"])
        if desired is None:
            continue
        if room["id"] in model["anchor_room_ids"] or room["review"]["suspected_layout_drift"]:
            _move_room(room, desired, report, "source_alignment")


def _straighten_chains(model: dict[str, object], report: dict[str, object]) -> None:
    for chain in model["chain_groups"]:
        if chain["source_orientation"] not in {"horizontal", "vertical"}:
            if chain["source_orientation"] == "bent":
                report["unresolved_ambiguities"].append({
                    "kind": "chain",
                    "room_ids": chain["room_ids"],
                    "reason": "source_preserves_real_bend",
                })
            continue
        rooms = [model["room_lookup"][room_id] for room_id in chain["room_ids"]]
        desired_coords = [model["source_positions"].get(room["id"], (room["map_x"], room["map_y"])) for room in rooms]
        if chain["source_orientation"] == "horizontal":
            y_value = int(round(statistics.median(coord[1] for coord in desired_coords) / GRID_SIZE) * GRID_SIZE)
            direction = 1 if desired_coords[-1][0] >= desired_coords[0][0] else -1
            start_x = desired_coords[0][0]
            for index, room in enumerate(rooms):
                _move_room(room, (start_x + direction * index * GRID_SIZE, y_value), report, "straighten_chain")
        else:
            x_value = int(round(statistics.median(coord[0] for coord in desired_coords) / GRID_SIZE) * GRID_SIZE)
            direction = 1 if desired_coords[-1][1] >= desired_coords[0][1] else -1
            start_y = desired_coords[0][1]
            for index, room in enumerate(rooms):
                _move_room(room, (x_value, start_y + direction * index * GRID_SIZE), report, "straighten_chain")


def _reposition_clusters(model: dict[str, object], report: dict[str, object]) -> None:
    motif_layout_room_ids = model.setdefault("motif_layout_room_ids", set())
    for cluster in model["cluster_groups"]:
        room_ids = cluster["room_ids"]
        rooms = [model["room_lookup"][room_id] for room_id in room_ids]
        source_coords = [model["source_positions"].get(room_id) for room_id in room_ids if room_id in model["source_positions"]]
        if len(source_coords) < max(3, len(room_ids) // 2):
            report["unresolved_ambiguities"].append({
                "kind": "cluster",
                "room_ids": room_ids,
                "reason": "insufficient_source_positions",
            })
            continue
        cluster_layout = _build_cluster_layout(model, cluster)
        if cluster_layout:
            motif_layout_room_ids.update(cluster_layout)
            for room_id, coord in cluster_layout.items():
                _move_room(model["room_lookup"][room_id], coord, report, f"cluster_{cluster['motif']}")
            continue
        current_centroid = _centroid([(room["map_x"], room["map_y"]) for room in rooms])
        desired_centroid = _centroid(source_coords)
        dx = int(round((desired_centroid[0] - current_centroid[0]) / GRID_SIZE) * GRID_SIZE)
        dy = int(round((desired_centroid[1] - current_centroid[1]) / GRID_SIZE) * GRID_SIZE)
        if abs(dx) < GRID_SIZE and abs(dy) < GRID_SIZE:
            continue
        if any(room_id in model["anchor_room_ids"] for room_id in room_ids):
            continue
        for room in rooms:
            _move_room(room, (room["map_x"] + dx, room["map_y"] + dy), report, f"cluster_{cluster['motif']}")


def _build_cluster_layout(model: dict[str, object], cluster: Mapping[str, object]) -> dict[str, tuple[int, int]]:
    motif = str(cluster.get("motif") or "")
    room_ids = list(cluster.get("room_ids") or [])
    if motif == "loop":
        return _layout_loop_cluster(model, room_ids)
    if motif == "hub_spoke":
        return _layout_hub_spoke_cluster(model, room_ids)
    if motif == "block":
        return _layout_block_cluster(model, room_ids)
    return {}


def _layout_loop_cluster(model: Mapping[str, object], room_ids: list[str]) -> dict[str, tuple[int, int]]:
    if len(room_ids) < 4:
        return {}
    center = _cluster_layout_center(model, room_ids)
    ordered_ids = _order_room_ids_by_source_angle(model, room_ids, center)
    columns, rows = _rectangle_dimensions(len(ordered_ids))
    slots = _perimeter_slots(columns, rows)
    if len(slots) < len(ordered_ids):
        return {}
    ordered_slots = _best_slot_rotation(model, ordered_ids, slots[: len(ordered_ids)], center)
    return {
        room_id: (center[0] + slot[0], center[1] + slot[1])
        for room_id, slot in zip(ordered_ids, ordered_slots)
    }


def _layout_hub_spoke_cluster(model: Mapping[str, object], room_ids: list[str]) -> dict[str, tuple[int, int]]:
    if len(room_ids) < 5:
        return {}
    adjacency = model["adjacency"]
    hub_id = max(room_ids, key=lambda room_id: (len(adjacency.get(room_id, set())), room_id))
    center = _source_or_current_coord(model, hub_id)
    spoke_ids = [room_id for room_id in room_ids if room_id != hub_id]
    ordered_spokes = _order_room_ids_by_source_angle(model, spoke_ids, center)
    axis_sequence = [
        (1, 0),
        (0, -1),
        (-1, 0),
        (0, 1),
    ]
    layout = {hub_id: center}
    for index, room_id in enumerate(ordered_spokes):
        direction_x, direction_y = axis_sequence[index % len(axis_sequence)]
        distance = (index // len(axis_sequence)) + 1
        layout[room_id] = (
            center[0] + direction_x * distance * GRID_SIZE,
            center[1] + direction_y * distance * GRID_SIZE,
        )
    return layout


def _layout_block_cluster(model: Mapping[str, object], room_ids: list[str]) -> dict[str, tuple[int, int]]:
    if len(room_ids) < 4:
        return {}
    ordered_ids = sorted(
        room_ids,
        key=lambda room_id: (
            _source_or_current_coord(model, room_id)[1],
            _source_or_current_coord(model, room_id)[0],
            room_id,
        ),
    )
    columns = max(2, int(math.ceil(math.sqrt(len(ordered_ids)))))
    rows = max(2, int(math.ceil(len(ordered_ids) / columns)))
    center = _cluster_layout_center(model, ordered_ids)
    x_slots = _centered_slots(columns)
    y_slots = _centered_slots(rows)
    layout = {}
    for index, room_id in enumerate(ordered_ids):
        row_index, column_index = divmod(index, columns)
        if row_index >= len(y_slots):
            break
        layout[room_id] = (
            center[0] + x_slots[column_index] * GRID_SIZE,
            center[1] + y_slots[row_index] * GRID_SIZE,
        )
    return layout


def _cluster_layout_center(model: Mapping[str, object], room_ids: list[str]) -> tuple[int, int]:
    anchors = sorted(set(model.get("anchor_room_ids") or set()).intersection(room_ids))
    if anchors:
        return _source_or_current_coord(model, anchors[0])
    coords = [_source_or_current_coord(model, room_id) for room_id in room_ids]
    centroid = _centroid(coords)
    return (_snap_to_grid(centroid[0]), _snap_to_grid(centroid[1]))


def _source_or_current_coord(model: Mapping[str, object], room_id: str) -> tuple[int, int]:
    desired = model["source_positions"].get(room_id)
    if desired is not None:
        return (int(desired[0]), int(desired[1]))
    room = model["room_lookup"].get(room_id)
    if room is None:
        return (0, 0)
    return (int(room["map_x"]), int(room["map_y"]))


def _order_room_ids_by_source_angle(
    model: Mapping[str, object], room_ids: list[str], center: tuple[int, int]
) -> list[str]:
    return sorted(
        room_ids,
        key=lambda room_id: (
            math.atan2(
                _source_or_current_coord(model, room_id)[1] - center[1],
                _source_or_current_coord(model, room_id)[0] - center[0],
            ),
            room_id,
        ),
    )


def _rectangle_dimensions(count: int) -> tuple[int, int]:
    best = None
    for rows in range(2, count + 1):
        columns = max(2, (count + rows - 1) // rows)
        capacity = (columns * 2) + (rows * 2) - 4
        if capacity < count:
            continue
        candidate = (abs(columns - rows), capacity, columns * rows, columns, rows)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        return (count, 2)
    return (best[3], best[4])


def _perimeter_slots(columns: int, rows: int) -> list[tuple[int, int]]:
    x_slots = _centered_slots(columns)
    y_slots = _centered_slots(rows)
    coords = []
    for column_index in range(columns):
        coords.append((x_slots[column_index] * GRID_SIZE, y_slots[0] * GRID_SIZE))
    for row_index in range(1, rows):
        coords.append((x_slots[-1] * GRID_SIZE, y_slots[row_index] * GRID_SIZE))
    if rows > 1:
        for column_index in range(columns - 2, -1, -1):
            coords.append((x_slots[column_index] * GRID_SIZE, y_slots[-1] * GRID_SIZE))
    if columns > 1:
        for row_index in range(rows - 2, 0, -1):
            coords.append((x_slots[0] * GRID_SIZE, y_slots[row_index] * GRID_SIZE))
    return coords


def _centered_slots(count: int) -> list[int]:
    if count <= 0:
        return []
    negatives = list(range(-(count // 2), 0))
    positives = list(range(1, (count // 2) + 1))
    if count % 2:
        return negatives + [0] + positives
    return negatives + positives


def _best_slot_rotation(
    model: Mapping[str, object],
    ordered_ids: list[str],
    slots: list[tuple[int, int]],
    center: tuple[int, int],
) -> list[tuple[int, int]]:
    if not ordered_ids or not slots:
        return slots
    candidates = []
    for direction in (slots, list(reversed(slots))):
        for offset in range(len(direction)):
            candidates.append(direction[offset:] + direction[:offset])
    best_slots = slots
    best_score = None
    for candidate in candidates:
        score = 0
        for room_id, slot in zip(ordered_ids, candidate):
            target = (center[0] + slot[0], center[1] + slot[1])
            score += _manhattan_distance(_source_or_current_coord(model, room_id), target)
        if best_score is None or score < best_score:
            best_score = score
            best_slots = candidate
    return best_slots


def _centroid(coords: list[tuple[int, int]]) -> tuple[float, float]:
    return (
        sum(coord[0] for coord in coords) / max(1, len(coords)),
        sum(coord[1] for coord in coords) / max(1, len(coords)),
    )


def _rebuild_around_anchors(model: dict[str, object], report: dict[str, object]) -> None:
    protected_room_ids = set(model.get("motif_layout_room_ids") or set())
    for anchor_id in sorted(model["anchor_room_ids"]):
        for neighbor_id in sorted(model["adjacency"].get(anchor_id, set())):
            if neighbor_id in protected_room_ids:
                continue
            desired = model["source_positions"].get(neighbor_id)
            if desired is None:
                continue
            room = model["room_lookup"].get(neighbor_id)
            if room is None:
                continue
            _move_room(room, desired, report, "anchor_rebuild")


def _correct_special_exit_labels(model: dict[str, object], report: dict[str, object]) -> None:
    source_special_pairs = model["source_special_pairs"]
    for room in model["rooms"]:
        updated = {}
        for label, spec in room["special_exits"].items():
            target = str((spec or {}).get("target") or "").strip()
            corrected = source_special_pairs.get((room["id"], target), _correct_special_label(label))
            if corrected != label:
                report["corrected_special_exits"].append({
                    "room_id": room["id"],
                    "target": target,
                    "old": label,
                    "new": corrected,
                })
            updated[corrected] = dict(spec or {})
        room["special_exits"] = updated


def _correct_special_label(label: str) -> str:
    normalized = re.sub(r"\s+", " ", str(label or "").strip().lower())
    if not normalized:
        return normalized
    if MAP_TRANSITION_RE.search(normalized):
        return normalized
    match = get_close_matches(normalized, KNOWN_SPECIAL_EXIT_LABELS, n=1, cutoff=0.82)
    if match:
        return match[0]
    if normalized.startswith("go "):
        tail = normalized[3:]
        tail_match = get_close_matches(f"go {tail}", KNOWN_SPECIAL_EXIT_LABELS, n=1, cutoff=0.84)
        if tail_match:
            return tail_match[0]
    return normalized


def _sync_connectivity(model: dict[str, object], report: dict[str, object]) -> None:
    room_lookup = model["room_lookup"]
    source_spatial_pairs = model["source_spatial_pairs"]
    source_special_pairs = model["source_special_pairs"]

    for edge in model["source_edges"]:
        source_room = room_lookup.get(edge["source"])
        target_room = room_lookup.get(edge["target"])
        if not source_room or not target_room:
            report["unresolved_ambiguities"].append({
                "kind": "edge",
                "source": edge["source"],
                "target": edge["target"],
                "reason": "source_edge_missing_room",
            })
            continue
        if edge["kind"] == "special":
            label = edge["label"] or _fallback_special_label(source_room["id"], target_room["id"])
            if not _has_special_exit(source_room, label, target_room["id"]):
                source_room["special_exits"][label] = _exit_spec(target_room["id"])
                report["added_exits"].append({
                    "kind": "special",
                    "source": source_room["id"],
                    "target": target_room["id"],
                    "label": label,
                })
            continue

        direction = _direction_between_rooms(source_room, target_room)
        if direction is None:
            label = _fallback_special_label(source_room["id"], target_room["id"])
            if not _has_special_exit(source_room, label, target_room["id"]):
                source_room["special_exits"][label] = _exit_spec(target_room["id"])
                report["added_exits"].append({
                    "kind": "special",
                    "source": source_room["id"],
                    "target": target_room["id"],
                    "label": label,
                    "reason": "irregular_connector",
                })
            continue
        if not _has_spatial_exit(source_room, direction, target_room["id"]):
            source_room["exits"][direction] = _exit_spec(target_room["id"])
            report["added_exits"].append({
                "kind": "spatial",
                "source": source_room["id"],
                "target": target_room["id"],
                "direction": direction,
            })
        reverse_direction = REVERSE_DIRECTIONS.get(direction)
        if reverse_direction:
            if not _has_spatial_exit(target_room, reverse_direction, source_room["id"]):
                target_room["exits"][reverse_direction] = _exit_spec(source_room["id"])
                report["added_exits"].append({
                    "kind": "spatial",
                    "source": target_room["id"],
                    "target": source_room["id"],
                    "direction": reverse_direction,
                    "reason": "reverse_traversal",
                })

    for room in model["rooms"]:
        for direction, spec in list(room["exits"].items()):
            target = str((spec or {}).get("target") or "").strip()
            if tuple(sorted((room["id"], target))) not in source_spatial_pairs:
                room["exits"].pop(direction, None)
                report["removed_exits"].append({
                    "kind": "spatial",
                    "source": room["id"],
                    "target": target,
                    "direction": direction,
                })
        for label, spec in list(room["special_exits"].items()):
            target = str((spec or {}).get("target") or "").strip()
            supported = source_special_pairs.get((room["id"], target))
            if supported is None and tuple(sorted((room["id"], target))) not in source_spatial_pairs:
                room["special_exits"].pop(label, None)
                report["removed_exits"].append({
                    "kind": "special",
                    "source": room["id"],
                    "target": target,
                    "label": label,
                })


def _fallback_special_label(source_id: str, target_id: str) -> str:
    return f"to_{source_id}_to_{target_id}".lower()


def _exit_spec(target_id: str) -> dict[str, object]:
    return {
        "target": target_id,
        "typeclass": "typeclasses.exits.Exit",
        "speed": "",
        "travel_time": 0,
    }


def _has_special_exit(room: Mapping[str, object], label: str, target_id: str) -> bool:
    spec = dict(room.get("special_exits") or {}).get(label)
    return bool(spec) and str(spec.get("target") or "").strip() == target_id


def _has_spatial_exit(room: Mapping[str, object], direction: str, target_id: str) -> bool:
    spec = dict(room.get("exits") or {}).get(direction)
    return bool(spec) and str(spec.get("target") or "").strip() == target_id


def _direction_between_rooms(source_room: Mapping[str, object], target_room: Mapping[str, object]) -> str | None:
    dx = int(target_room["map_x"]) - int(source_room["map_x"])
    dy = int(target_room["map_y"]) - int(source_room["map_y"])
    if dx == 0 and dy < 0:
        return "north"
    if dx == 0 and dy > 0:
        return "south"
    if dy == 0 and dx > 0:
        return "east"
    if dy == 0 and dx < 0:
        return "west"
    return None


def _resolve_coordinate_collisions(model: dict[str, object], report: dict[str, object]) -> None:
    occupied = {}
    for room in sorted(model["rooms"], key=lambda entry: entry["id"]):
        coord = (room["map_x"], room["map_y"])
        if coord not in occupied:
            occupied[coord] = room["id"]
            continue
        desired = coord
        for radius in range(1, 7):
            for dx, dy in _spiral_offsets(radius):
                candidate = (desired[0] + dx * GRID_SIZE, desired[1] + dy * GRID_SIZE)
                if candidate not in occupied:
                    _move_room(room, candidate, report, "collision_resolution")
                    occupied[candidate] = room["id"]
                    break
            else:
                continue
            break
        else:
            report["unresolved_ambiguities"].append({
                "kind": "collision",
                "room_id": room["id"],
                "coord": list(desired),
            })


def _spiral_offsets(radius: int) -> list[tuple[int, int]]:
    offsets = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if max(abs(dx), abs(dy)) == radius:
                offsets.append((dx, dy))
    return offsets


def _refresh_indexes(model: dict[str, object]) -> None:
    model["room_by_coord"] = {(room["map_x"], room["map_y"]): room["id"] for room in model["rooms"]}
    model["spatial_exits"], model["special_exits"] = _collect_yaml_exits(model["rooms"])
    model["adjacency"], model["adjacency_tags"] = _build_yaml_graph(model["rooms"])


def _move_room(room: dict[str, object], new_coord: tuple[int, int], report: dict[str, object], reason: str) -> None:
    old_coord = (room["map_x"], room["map_y"])
    if old_coord == new_coord:
        return
    room["map_x"], room["map_y"] = int(new_coord[0]), int(new_coord[1])
    room["map"]["x"] = int(new_coord[0])
    room["map"]["y"] = int(new_coord[1])
    report["moved_rooms"].append({
        "room_id": room["id"],
        "from": [int(old_coord[0]), int(old_coord[1])],
        "to": [int(new_coord[0]), int(new_coord[1])],
        "reason": reason,
    })
    room["review"]["suspected_layout_drift"] = False


def _serialize_zone(model: Mapping[str, object]) -> dict[str, object]:
    rooms = []
    for room in model["rooms"]:
        serialized = deepcopy(room)
        serialized["map"] = {
            "x": int(room["map_x"]),
            "y": int(room["map_y"]),
            "layer": int(room["map_layer"]),
        }
        serialized.pop("map_x", None)
        serialized.pop("map_y", None)
        serialized.pop("map_layer", None)
        serialized.pop("review", None)
        rooms.append(serialized)
    return {
        "schema_version": model["schema_version"],
        "zone_id": model["zone_id"],
        "name": model["name"],
        "rooms": rooms,
    }


def _validate_zone_schema(zone_data: Mapping[str, object]) -> None:
    room_ids = []
    for room in list(zone_data.get("rooms") or []):
        room_id = str(room.get("id") or "").strip()
        if not room_id:
            raise ValueError("Reviewed YAML contains a room without an id.")
        room_ids.append(room_id)
    duplicates = [room_id for room_id, count in Counter(room_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Reviewed YAML contains duplicate room ids: {duplicates}")
    known_ids = set(room_ids)
    for room in list(zone_data.get("rooms") or []):
        for bucket_name in ("exits", "special_exits"):
            for label, spec in dict(room.get(bucket_name) or {}).items():
                target = str((spec or {}).get("target") or "").strip()
                if target not in known_ids:
                    raise ValueError(
                        f"Reviewed YAML contains {bucket_name} target '{target}' missing from rooms for room {room.get('id')} ({label})."
                    )


def _manhattan_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(int(a[0]) - int(b[0])) + abs(int(a[1]) - int(b[1]))


def _snap_to_grid(value: float | int) -> int:
    return int(round(float(value) / GRID_SIZE) * GRID_SIZE)