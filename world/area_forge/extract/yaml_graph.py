from __future__ import annotations

from collections import deque
from pathlib import Path

from world.area_forge.extract.ocr import extract_ocr_bundle, is_exit_command, normalize_ocr_text, ocr_available
from world.area_forge.model.confidence import classify_confidence, score_label_confidence

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
}

MARKER_PALETTES = {
    "gray": {
        (153, 128, 153),
        (102, 128, 102),
        (204, 170, 204),
        (204, 213, 204),
        (153, 170, 153),
        (102, 128, 153),
        (153, 128, 102),
        (204, 170, 153),
        (204, 213, 153),
        (153, 213, 153),
    },
    "red": {(255, 0, 0)},
    "green": {(0, 255, 0)},
    "yellow": {(255, 255, 0)},
    "cyan": {(0, 255, 255)},
    "magenta": {(255, 0, 255)},
}

COMPONENT_MIN_SIZE = 8
COMPONENT_MAX_SIZE = 15
NODE_DUPLICATE_TOLERANCE = 3
NODE_LABEL_RADIUS = 84
EDGE_LABEL_RADIUS = 52


def _load_map_image(map_path: str | Path):
    path = Path(map_path)
    if Image is None:
        raise RuntimeError("Pillow is required for YAML graph extraction.")
    if not path.exists():
        raise FileNotFoundError(f"AreaForge map image was not found: {path}")
    return Image.open(path).convert("RGB")


def _detect_components(img, palette):
    pixels = img.load()
    width, height = img.size
    visited = [[False] * width for _ in range(height)]
    components = []

    for y in range(height):
        for x in range(width):
            if visited[y][x] or pixels[x, y] not in palette:
                continue
            queue = deque([(x, y)])
            visited[y][x] = True
            points = []
            while queue:
                cur_x, cur_y = queue.popleft()
                points.append((cur_x, cur_y))
                for next_x, next_y in (
                    (cur_x + 1, cur_y),
                    (cur_x - 1, cur_y),
                    (cur_x, cur_y + 1),
                    (cur_x, cur_y - 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and not visited[next_y][next_x]
                        and pixels[next_x, next_y] in palette
                    ):
                        visited[next_y][next_x] = True
                        queue.append((next_x, next_y))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            if COMPONENT_MIN_SIZE <= box_width <= COMPONENT_MAX_SIZE and COMPONENT_MIN_SIZE <= box_height <= COMPONENT_MAX_SIZE:
                components.append({
                    "x": int(round((min_x + max_x) / 2)),
                    "y": int(round((min_y + max_y) / 2)),
                })

    return components


def _detect_nodes(img, area_slug: str):
    nodes = []
    for kind, palette in MARKER_PALETTES.items():
        for component in _detect_components(img, palette):
            nodes.append({"kind": kind, **component})

    merged = []
    for node in sorted(nodes, key=lambda item: (item["y"], item["x"])):
        duplicate = None
        for existing in merged:
            if abs(node["x"] - existing["x"]) <= NODE_DUPLICATE_TOLERANCE and abs(node["y"] - existing["y"]) <= NODE_DUPLICATE_TOLERANCE:
                duplicate = existing
                break
        if duplicate is None:
            node["id"] = f"{area_slug}_{node['x']}_{node['y']}"
            merged.append(node)
    return merged


def _sample_has_path(img, source, target):
    pixels = img.load()
    width, height = img.size
    steps = int(max(abs(target["x"] - source["x"]), abs(target["y"] - source["y"])))
    if steps <= 2:
        return False

    hit_count = 0
    total_count = 0
    for step in range(2, steps - 1):
        ratio = step / steps
        sample_x = int(round(source["x"] + (target["x"] - source["x"]) * ratio))
        sample_y = int(round(source["y"] + (target["y"] - source["y"]) * ratio))
        seen = False
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                cur_x = sample_x + offset_x
                cur_y = sample_y + offset_y
                if 0 <= cur_x < width and 0 <= cur_y < height:
                    red, green, blue = pixels[cur_x, cur_y]
                    if not (red > 245 and green > 245 and blue > 245):
                        seen = True
                        break
            if seen:
                break
        total_count += 1
        if seen:
            hit_count += 1

    return total_count > 0 and (hit_count / total_count) >= 0.6


def _candidate_direction(source, target):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    abs_x = abs(dx)
    abs_y = abs(dy)
    if abs_y <= 3 and 14 <= abs_x <= 60:
        return ("east" if dx > 0 else "west", abs_x)
    if abs_x <= 3 and 14 <= abs_y <= 60:
        return ("south" if dy > 0 else "north", abs_y)
    if abs(abs_x - abs_y) <= 3 and 14 <= abs_x <= 60:
        if dx > 0 and dy > 0:
            return ("southeast", (abs_x + abs_y) / 2)
        if dx > 0 and dy < 0:
            return ("northeast", (abs_x + abs_y) / 2)
        if dx < 0 and dy > 0:
            return ("southwest", (abs_x + abs_y) / 2)
        return ("northwest", (abs_x + abs_y) / 2)
    return (None, None)


def _derive_spatial_edges(img, nodes):
    edge_map = {node["id"]: {} for node in nodes}
    for source in nodes:
        candidates = {}
        for target in nodes:
            if source["id"] == target["id"]:
                continue
            direction, distance = _candidate_direction(source, target)
            if not direction:
                continue
            current = candidates.get(direction)
            if current is None or distance < current[0]:
                candidates[direction] = (distance, target)

        for direction, (_, target) in candidates.items():
            if _sample_has_path(img, source, target):
                edge_map[source["id"]][direction] = target["id"]

    edges = []
    for source_id, exits in edge_map.items():
        for direction, target_id in exits.items():
            reverse_direction = OPPOSITE_DIRECTIONS[direction]
            if edge_map.get(target_id, {}).get(reverse_direction) == source_id:
                edges.append((source_id, direction, target_id))
    return edges


def _distance(left: dict, right: dict) -> float:
    dx = float(left["x"] - right["x"])
    dy = float(left["y"] - right["y"])
    return (dx * dx + dy * dy) ** 0.5


def _attach_node_labels(nodes, ocr_lines):
    for node in nodes:
        best = None
        best_distance = None
        for line in ocr_lines:
            if line.get("label_type") not in {"landmark", "place", "poi_stub"}:
                continue
            distance = _distance(node, line)
            if distance > NODE_LABEL_RADIUS:
                continue
            if best is None or distance < best_distance:
                best = line
                best_distance = distance
        node["ocr_label"] = best.get("text") if best else None
        node["ocr_label_confidence"] = best.get("confidence", 0.0) if best else 0.0
        node["ocr_label_quality"] = best.get("quality_score", 0.0) if best else 0.0
        node["ocr_label_type"] = best.get("label_type", "none") if best else "none"
        node["ocr_distance"] = best_distance if best else None
        node["ocr_association_score"] = score_label_confidence(best_distance, best.get("confidence", 0.0)) if best else 0.0
        node["ocr_confidence_tier"] = classify_confidence(node.get("ocr_association_score", 0.0))
        node["final_label"] = normalize_ocr_text(best.get("text")) if best else None
        node["needs_label_review"] = not bool(node["final_label"]) or node["ocr_confidence_tier"] in {"low", "none"}
    return nodes


def _attach_edge_labels(edges, nodes, ocr_lines):
    node_lookup = {node["id"]: node for node in nodes}
    enriched = []
    for source_id, direction, target_id in edges:
        source = node_lookup[source_id]
        target = node_lookup[target_id]
        mid = {
            "x": (source["x"] + target["x"]) / 2,
            "y": (source["y"] + target["y"]) / 2,
        }
        best = None
        best_distance = None
        for line in ocr_lines:
            distance = _distance(mid, line)
            if distance > EDGE_LABEL_RADIUS:
                continue
            if best is None or distance < best_distance:
                best = line
                best_distance = distance
        edge_data = {
            "label": best.get("text") if best else None,
            "confidence": best.get("confidence", 0.0) if best else 0.0,
            "distance": best_distance,
            "final_exit_name": direction,
            "exit_type": "directional",
            "confidence_tier": classify_confidence(score_label_confidence(best_distance, best.get("confidence", 0.0))) if best else "none",
            "needs_review": bool(best) and bool(best.get("text")) and is_exit_command(best.get("text", "")),
        }
        enriched.append((source_id, direction, target_id, edge_data))
    return enriched


def _build_special_exit_candidates(nodes, ocr_lines):
    candidates = []
    for line in ocr_lines:
        if not is_exit_command(line.get("text", "")):
            continue
        nearest = None
        nearest_distance = None
        for node in nodes:
            distance = _distance(node, line)
            if nearest is None or distance < nearest_distance:
                nearest = node
                nearest_distance = distance
        candidates.append({
            "label": line.get("text"),
            "x": line.get("x"),
            "y": line.get("y"),
            "nearest_node_id": nearest["id"] if nearest else None,
            "distance": nearest_distance,
            "confidence": line.get("confidence", 0.0),
        })
    return candidates


def extract_yaml_graph_area_spec(map_path, area_id, use_ocr=True, use_ai_adjudication=False, profile=None, style_settings=None):
    del use_ai_adjudication, profile, style_settings
    area_slug = str(area_id or "area").strip().lower().replace("-", "_").replace(" ", "_")
    image = _load_map_image(map_path)
    nodes = _detect_nodes(image, area_slug)
    spatial_edges = _derive_spatial_edges(image, nodes)

    ocr_bundle = None
    ocr_lines = []
    if use_ocr and ocr_available():
        try:
            ocr_bundle = extract_ocr_bundle(map_path)
        except RuntimeError:
            ocr_bundle = None
        else:
            ocr_lines = list(ocr_bundle.get("lines") or [])

    _attach_node_labels(nodes, ocr_lines)
    artifact_edges = _attach_edge_labels(spatial_edges, nodes, ocr_lines)
    return {
        "nodes": nodes,
        "edges": artifact_edges,
        "meta": {
            "area_id": area_id,
            "area_slug": area_slug,
            "area_name": str(area_id or "").replace("_", " ").replace("-", " ").title(),
            "ocr_used": bool(ocr_bundle),
            "node_count": len(nodes),
            "edge_count": len(artifact_edges),
            "pipeline": "yaml_graph",
            "special_exit_candidates": _build_special_exit_candidates(nodes, ocr_lines),
        },
    }