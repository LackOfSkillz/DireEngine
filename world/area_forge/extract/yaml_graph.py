from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
import re

from world.area_forge.extract.ocr import extract_ocr_bundle, is_exit_command, normalize_ocr_text, ocr_available
from world.area_forge.model.confidence import classify_confidence, score_label_confidence
from world.area_forge.normalize import assign_lane_clusters, audit_graph, detect_long_edges, normalize_edges, validate_direction_consistency
from world.area_forge.serializer import save_json

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


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

MARKER_COLOR_THRESHOLDS = {
    "gray": 64,
    "red": 36,
    "green": 36,
    "yellow": 40,
    "cyan": 40,
    "magenta": 40,
}

DEFAULT_EXTRACT_CONFIG = {
    "debug_markers": False,
    "debug_lines": False,
    "debug_ocr": False,
    "debug_corridors": False,
    "min_marker_w": 5,
    "max_marker_w": 22,
    "min_marker_h": 5,
    "max_marker_h": 22,
    "node_duplicate_tolerance": 2,
    "marker_merge_centroid_tolerance": 12,
    "marker_merge_gap": 8,
    "marker_bbox_expand": 2,
    "marker_relaxed_size_margin": 6,
    "marker_confidence_min": 0.18,
    "marker_merge_source_limit": 4,
    "marker_merge_union_limit": 28,
    "marker_merge_center_spacing_limit": 10,
    "gray_saturation_max": 22,
    "gray_intensity_min": 120,
    "gray_intensity_max": 220,
    "square_aspect_min": 0.6,
    "square_aspect_max": 1.4,
    "square_area_min": 20,
    "square_area_max": 700,
    "grid_spacing_min": 12,
    "grid_spacing_max": 18,
    "grid_gap_support_threshold": 12,
    "grid_adjacency_tolerance": 2,
    "grid_axis_tolerance": 3,
    "line_dark_intensity_max": 188,
    "line_dark_channel_delta_max": 92,
    "line_thicken_passes": 1,
    "line_merge_alignment_tolerance": 3,
    "line_merge_gap": 10,
    "line_min_length": 6,
    "line_attach_distance": 20,
    "line_attach_soft_distance": 28,
    "junction_attach_distance": 16,
    "node_label_radius": 42,
    "edge_label_radius": 52,
    "min_room_label_confidence": 0.58,
    "min_room_label_quality": 0.62,
    "max_room_label_words": 3,
    "max_room_label_box": 110,
    "room_label_area_max": 9000,
    "junction_tolerance": 2,
    "fallback_sampling": True,
    "fallback_sampling_isolated_only": True,
    "fallback_sampling_hit_ratio": 0.55,
    "isolated_recovery_max_distance": 110,
    "allow_diagonal_edges": False,
    "diagonal_distance_max": 48,
    "orthogonal_distance_max": 72,
}

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

BOXED_TRAVEL_RE = re.compile(r"\bto\s+map[a-z0-9]*\b", re.IGNORECASE)


def color_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def _load_map_image(map_path: str | Path):
    path = Path(map_path)
    if Image is None:
        raise RuntimeError("Pillow is required for YAML graph extraction.")
    if not path.exists():
        raise FileNotFoundError(f"AreaForge map image was not found: {path}")
    return Image.open(path).convert("RGB")


def _slugify_area_id(area_id: object) -> str:
    return str(area_id or "area").strip().lower().replace("-", "_").replace(" ", "_")


def _extract_config(style_settings=None):
    config = dict(DEFAULT_EXTRACT_CONFIG)
    config["marker_color_thresholds"] = dict(MARKER_COLOR_THRESHOLDS)
    payload = dict(style_settings or {})
    debug_payload = payload.get("debug") if isinstance(payload.get("debug"), dict) else {}
    for key in ("debug_markers", "debug_lines", "debug_ocr", "debug_corridors"):
        if key in payload:
            config[key] = bool(payload[key])
        if key in debug_payload:
            config[key] = bool(debug_payload[key])
    for key in config:
        if key in payload and key not in {"debug_markers", "debug_lines", "debug_ocr", "debug_corridors"}:
            config[key] = payload[key]
    if isinstance(payload.get("marker_color_thresholds"), dict):
        config["marker_color_thresholds"].update(payload["marker_color_thresholds"])
    return config


def _artifact_dir(area_slug: str) -> Path:
    return Path(__file__).resolve().parents[3] / "build" / area_slug


def _write_debug_json(area_slug: str, filename: str, payload, enabled: bool):
    if enabled:
        save_json(_artifact_dir(area_slug) / filename, payload)


def _write_debug_mask(area_slug: str, filename: str, mask, enabled: bool):
    if not enabled or Image is None:
        return
    output_path = _artifact_dir(area_slug) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    height = len(mask)
    width = len(mask[0]) if height else 0
    image = Image.new("L", (width, height), color=0)
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = 255 if mask[y][x] else 0
    image.save(output_path)


def _dilate(mask):
    height = len(mask)
    width = len(mask[0]) if height else 0
    output = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            value = False
            for offset_y in (-1, 0, 1):
                for offset_x in (-1, 0, 1):
                    check_x = x + offset_x
                    check_y = y + offset_y
                    if 0 <= check_x < width and 0 <= check_y < height and mask[check_y][check_x]:
                        value = True
                        break
                if value:
                    break
            output[y][x] = value
    return output


def _erode(mask):
    height = len(mask)
    width = len(mask[0]) if height else 0
    output = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            value = True
            for offset_y in (-1, 0, 1):
                for offset_x in (-1, 0, 1):
                    check_x = x + offset_x
                    check_y = y + offset_y
                    if not (0 <= check_x < width and 0 <= check_y < height and mask[check_y][check_x]):
                        value = False
                        break
                if not value:
                    break
            output[y][x] = value
    return output


def _cleanup_mask(mask):
    return _erode(_dilate(_dilate(_erode(mask))))


def _subtract_mask(base_mask, subtract_mask):
    if not base_mask:
        return []
    height = len(base_mask)
    width = len(base_mask[0]) if height else 0
    output = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            output[y][x] = bool(base_mask[y][x]) and not bool(subtract_mask[y][x])
    return output


def _mask_from_candidates(image_size, candidates, expand=0):
    width, height = image_size
    mask = [[False] * width for _ in range(height)]
    for candidate in list(candidates or []):
        bbox = candidate.get("bbox") or {}
        start_x = max(0, int(bbox.get("x", 0)) - expand)
        start_y = max(0, int(bbox.get("y", 0)) - expand)
        end_x = min(width - 1, int(bbox.get("x", 0)) + int(bbox.get("w", 0)) - 1 + expand)
        end_y = min(height - 1, int(bbox.get("y", 0)) + int(bbox.get("h", 0)) - 1 + expand)
        for y in range(start_y, end_y + 1):
            for x in range(start_x, end_x + 1):
                mask[y][x] = True
    return mask


def _pixel_intensity_and_saturation(pixel):
    red, green, blue = pixel
    return (red + green + blue) // 3, max(red, green, blue) - min(red, green, blue)


def _is_gray_square_pixel(pixel, config):
    intensity, saturation = _pixel_intensity_and_saturation(pixel)
    return (
        saturation <= int(config.get("gray_saturation_max", 22))
        and int(config.get("gray_intensity_min", 120)) <= intensity <= int(config.get("gray_intensity_max", 220))
    )


def _pixel_matches_bucket(pixel, bucket_name, config):
    if bucket_name == "gray" and _is_gray_square_pixel(pixel, config):
        return True, 0, int((config.get("marker_color_thresholds") or {}).get(bucket_name, MARKER_COLOR_THRESHOLDS.get(bucket_name, 48)))
    thresholds = config.get("marker_color_thresholds") if isinstance(config, dict) else None
    threshold = int((thresholds or {}).get(bucket_name, MARKER_COLOR_THRESHOLDS.get(bucket_name, 48)))
    best = min(color_distance(pixel, candidate) for candidate in MARKER_PALETTES[bucket_name])
    return best <= threshold, best, threshold


def _build_marker_masks(img, config):
    pixels = img.load()
    width, height = img.size
    masks = {}
    for bucket_name in MARKER_PALETTES:
        mask = [[False] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                matched, _distance_value, _threshold = _pixel_matches_bucket(pixels[x, y], bucket_name, config)
                if matched:
                    mask[y][x] = True
        masks[bucket_name] = mask
    return masks


def _component_candidates_from_mask(img, bucket_name, mask, config):
    pixels = img.load()
    width, height = img.size
    visited = [[False] * width for _ in range(height)]
    candidates = []
    min_w = int(config["min_marker_w"])
    max_w = int(config["max_marker_w"])
    min_h = int(config["min_marker_h"])
    max_h = int(config["max_marker_h"])
    relaxed_margin = int(config.get("marker_relaxed_size_margin", 6))
    threshold = int(config.get("marker_color_thresholds", {}).get(bucket_name, MARKER_COLOR_THRESHOLDS.get(bucket_name, 48)))
    next_cluster_id = 0
    for y in range(height):
        for x in range(width):
            if visited[y][x] or not mask[y][x]:
                continue
            queue = deque([(x, y)])
            visited[y][x] = True
            points = []
            distances = []
            while queue:
                cur_x, cur_y = queue.popleft()
                points.append((cur_x, cur_y))
                distances.append(min(color_distance(pixels[cur_x, cur_y], candidate) for candidate in MARKER_PALETTES[bucket_name]))
                for next_x, next_y in ((cur_x + 1, cur_y), (cur_x - 1, cur_y), (cur_x, cur_y + 1), (cur_x, cur_y - 1)):
                    if 0 <= next_x < width and 0 <= next_y < height and not visited[next_y][next_x] and mask[next_y][next_x]:
                        visited[next_y][next_x] = True
                        queue.append((next_x, next_y))
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            if box_width > max_w + relaxed_margin or box_height > max_h + relaxed_margin:
                continue
            confidence = max(0.05, 1.0 - (sum(distances) / max(len(distances), 1)) / max(threshold, 1))
            mean_distance = sum(distances) / max(len(distances), 1)
            next_cluster_id += 1
            candidates.append({
                "cluster_id": f"{bucket_name}-{next_cluster_id:04d}",
                "x": int(round((min_x + max_x) / 2)),
                "y": int(round((min_y + max_y) / 2)),
                "w": box_width,
                "h": box_height,
                "bbox": {"x": min_x, "y": min_y, "w": box_width, "h": box_height},
                "color_bucket": bucket_name,
                "confidence": round(confidence, 4),
                "pixel_count": len(points),
                "mean_color_distance": round(mean_distance, 4),
                "size_in_bounds": min_w <= box_width <= max_w and min_h <= box_height <= max_h,
                "source_cluster_ids": [f"{bucket_name}-{next_cluster_id:04d}"],
            })
    return candidates


def _bbox_union(left, right):
    min_x = min(left["bbox"]["x"], right["bbox"]["x"])
    min_y = min(left["bbox"]["y"], right["bbox"]["y"])
    max_x = max(left["bbox"]["x"] + left["bbox"]["w"] - 1, right["bbox"]["x"] + right["bbox"]["w"] - 1)
    max_y = max(left["bbox"]["y"] + left["bbox"]["h"] - 1, right["bbox"]["y"] + right["bbox"]["h"] - 1)
    return {"x": min_x, "y": min_y, "w": max_x - min_x + 1, "h": max_y - min_y + 1}


def _bbox_gaps(left, right):
    left_box = left["bbox"]
    right_box = right["bbox"]
    gap_x = max(0, max(left_box["x"], right_box["x"]) - min(left_box["x"] + left_box["w"], right_box["x"] + right_box["w"]))
    gap_y = max(0, max(left_box["y"], right_box["y"]) - min(left_box["y"] + left_box["h"], right_box["y"] + right_box["h"]))
    return gap_x, gap_y


def _candidate_aspect_ratio(candidate):
    width = max(1, int(candidate.get("w", 0)))
    height = max(1, int(candidate.get("h", 0)))
    return width / height


def _is_squareish_candidate(candidate, config):
    aspect_ratio = _candidate_aspect_ratio(candidate)
    area = int(candidate.get("w", 0)) * int(candidate.get("h", 0))
    return (
        float(config.get("square_aspect_min", 0.6)) <= aspect_ratio <= float(config.get("square_aspect_max", 1.4))
        and int(config.get("square_area_min", 20)) <= area <= int(config.get("square_area_max", 700))
    )


def _marker_candidate_class(candidate, config):
    min_w = int(config["min_marker_w"])
    max_w = int(config["max_marker_w"])
    min_h = int(config["min_marker_h"])
    max_h = int(config["max_marker_h"])
    relaxed_margin = int(config.get("marker_relaxed_size_margin", 6))
    relaxed_min_w = max(3, min_w - 3)
    relaxed_min_h = max(3, min_h - 3)
    relaxed_max_w = max_w + relaxed_margin
    relaxed_max_h = max_h + relaxed_margin
    half_width = candidate["w"] >= max(3, int(min_w * 0.5))
    half_height = candidate["h"] >= max(3, int(min_h * 0.5))
    squareish = _is_squareish_candidate(candidate, config)
    if (min_w <= candidate["w"] <= max_w and min_h <= candidate["h"] <= max_h) or (squareish and candidate.get("color_bucket") == "gray"):
        return "strong"
    if candidate.get("confidence", 0.0) < float(config.get("marker_confidence_min", 0.18)):
        return "rejected"
    if squareish and candidate.get("color_bucket") == "gray":
        return "weak"
    if half_width and half_height and candidate.get("mean_color_distance", 999.0) <= float(config.get("marker_color_thresholds", {}).get(candidate["color_bucket"], 48)):
        return "weak"
    if relaxed_min_w <= candidate["w"] <= relaxed_max_w and relaxed_min_h <= candidate["h"] <= relaxed_max_h:
        return "weak"
    return "rejected"


def _candidate_to_node(candidate, area_slug: str, marker_strength: str):
    return {
        "id": f"{area_slug}_{candidate['x']}_{candidate['y']}",
        "kind": candidate["color_bucket"],
        "marker_strength": marker_strength,
        **candidate,
    }


def _dedupe_marker_nodes(candidates, area_slug: str, config, marker_strength: str):
    deduped = []
    tolerance = int(config["node_duplicate_tolerance"])
    for candidate in sorted(candidates, key=lambda item: (item["y"], item["x"], item["color_bucket"])):
        duplicate = None
        for existing in deduped:
            if abs(candidate["x"] - existing["x"]) <= tolerance and abs(candidate["y"] - existing["y"]) <= tolerance:
                duplicate = existing
                break
        if duplicate is None:
            deduped.append(_candidate_to_node(candidate, area_slug, marker_strength))
    return deduped


def _merge_marker_fragments(candidates, config):
    remaining = sorted(list(candidates or []), key=lambda item: (item["color_bucket"], item["y"], item["x"]))
    merged = []
    centroid_tolerance = int(config["marker_merge_centroid_tolerance"])
    merge_gap = int(config["marker_merge_gap"])
    relaxed_margin = int(config.get("marker_relaxed_size_margin", 6))
    max_w = min(int(config["max_marker_w"]) + relaxed_margin, int(config.get("marker_merge_union_limit", int(config["max_marker_w"]) + relaxed_margin)))
    max_h = min(int(config["max_marker_h"]) + relaxed_margin, int(config.get("marker_merge_union_limit", int(config["max_marker_h"]) + relaxed_margin)))
    source_limit = int(config.get("marker_merge_source_limit", 4))
    center_spacing_limit = float(config.get("marker_merge_center_spacing_limit", 10))
    while remaining:
        current = remaining.pop(0)
        current.setdefault("source_cluster_ids", list(current.get("source_cluster_ids") or ([current.get("cluster_id")] if current.get("cluster_id") else [])))
        changed = True
        while changed:
            changed = False
            for index, candidate in enumerate(list(remaining)):
                if candidate["color_bucket"] != current["color_bucket"]:
                    continue
                candidate.setdefault("source_cluster_ids", list(candidate.get("source_cluster_ids") or ([candidate.get("cluster_id")] if candidate.get("cluster_id") else [])))
                gap_x, gap_y = _bbox_gaps(current, candidate)
                center_distance = _distance(current, candidate)
                close_centroid = abs(candidate["x"] - current["x"]) <= centroid_tolerance and abs(candidate["y"] - current["y"]) <= centroid_tolerance
                close_bbox = gap_x <= merge_gap and gap_y <= merge_gap
                if not close_centroid and not close_bbox:
                    continue
                if center_distance > center_spacing_limit and (gap_x > 1 or gap_y > 1):
                    continue
                union = _bbox_union(current, candidate)
                source_cluster_ids = sorted(set(list(current.get("source_cluster_ids") or []) + list(candidate.get("source_cluster_ids") or [])))
                if len(source_cluster_ids) > source_limit:
                    continue
                if union["w"] > max_w or union["h"] > max_h:
                    continue
                current = {
                    "x": int(round((current["x"] + candidate["x"]) / 2)),
                    "y": int(round((current["y"] + candidate["y"]) / 2)),
                    "w": union["w"],
                    "h": union["h"],
                    "bbox": union,
                    "color_bucket": current["color_bucket"],
                    "confidence": round(max(current["confidence"], candidate["confidence"]), 4),
                    "pixel_count": int(current.get("pixel_count", 0)) + int(candidate.get("pixel_count", 0)),
                    "mean_color_distance": round((float(current.get("mean_color_distance", 0.0)) + float(candidate.get("mean_color_distance", 0.0))) / 2.0, 4),
                    "size_in_bounds": union["w"] <= int(config["max_marker_w"]) and union["h"] <= int(config["max_marker_h"]),
                    "source_cluster_ids": source_cluster_ids,
                }
                remaining.pop(index)
                changed = True
                break
        merged.append(current)
    return merged


def _detect_nodes(img, area_slug: str, config):
    raw_candidates = []
    marker_masks = _build_marker_masks(img, config)
    for bucket_name, mask in marker_masks.items():
        cleaned_mask = _cleanup_mask(mask)
        raw_candidates.extend(_component_candidates_from_mask(img, bucket_name, cleaned_mask, config))
    _write_debug_json(area_slug, "debug_marker_candidates.json", raw_candidates, bool(config["debug_markers"]))
    merged = _merge_marker_fragments(raw_candidates, config)
    strong_candidates = []
    weak_candidates = []
    rejected_candidates = []
    for candidate in merged:
        candidate_class = _marker_candidate_class(candidate, config)
        candidate["candidate_class"] = candidate_class
        if candidate_class == "strong":
            strong_candidates.append(candidate)
        elif candidate_class == "weak":
            weak_candidates.append(candidate)
        else:
            rejected_candidates.append(candidate)
    deduped = _dedupe_marker_nodes(strong_candidates, area_slug, config, "strong")
    _write_debug_json(
        area_slug,
        "debug_final_markers.json",
        [{"id": node["id"], "x": node["x"], "y": node["y"], "bbox": node["bbox"], "color_bucket": node["color_bucket"]} for node in deduped],
        bool(config["debug_markers"]),
    )
    marker_report = {
        "raw_cluster_count": len(raw_candidates),
        "candidate_count": len(merged),
        "accepted_count": len(deduped),
        "weak_candidate_count": len(weak_candidates),
        "rejected_count": len(rejected_candidates),
        "weak_promoted_count": 0,
        "missing_count": max(0, len(raw_candidates) - len(deduped)),
        "coverage": round(len(deduped) / max(len(raw_candidates), 1), 4),
        "raw_candidates": raw_candidates,
        "weak_candidates": weak_candidates,
        "rejected_candidates": rejected_candidates,
    }
    node_preserve_mask = _mask_from_candidates(img.size, raw_candidates, expand=1)
    return deduped, weak_candidates, marker_report, node_preserve_mask


def _cv_room_to_node(room):
    bbox_x = int(room["x"] - room["w"] / 2)
    bbox_y = int(room["y"] - room["h"] / 2)
    return {
        "id": room["id"],
        "x": int(room["x"]),
        "y": int(room["y"]),
        "kind": "room",
        "w": int(room["w"]),
        "h": int(room["h"]),
        "area": int(room["area"]),
        "bbox": {"x": bbox_x, "y": bbox_y, "w": int(room["w"]), "h": int(room["h"])} ,
        "color_bucket": room["color"],
        "room_color": room["color"],
        "marker_strength": "cv_v2",
        "source_cluster_ids": [room["id"]],
    }


def _detect_nodes_cv_v2(map_path, area_slug: str):
    from .cv_pipeline import build_preserve_mask, detect_rooms, load_bgr, write_room_overlay

    image_bgr = load_bgr(str(map_path))
    rooms = detect_rooms(image_bgr)
    write_room_overlay(image_bgr, rooms, _artifact_dir(area_slug) / "debug_room_overlay.png")
    nodes = [_cv_room_to_node(room) for room in rooms]
    marker_report = {
        "raw_cluster_count": len(rooms),
        "candidate_count": len(rooms),
        "accepted_count": len(nodes),
        "weak_candidate_count": 0,
        "rejected_count": 0,
        "weak_promoted_count": 0,
        "forced_promoted_count": 0,
        "missing_count": 0,
        "coverage": 1.0 if rooms else 0.0,
        "raw_candidates": [],
        "weak_candidates": [],
        "rejected_candidates": [],
    }
    node_preserve_mask = build_preserve_mask(image_bgr.shape, rooms).astype(bool).tolist()
    return nodes, [], marker_report, node_preserve_mask


def _candidate_matches_existing_node(candidate, nodes, tolerance):
    for node in nodes:
        if abs(candidate["x"] - node["x"]) <= tolerance and abs(candidate["y"] - node["y"]) <= tolerance:
            return True
    return False


def _candidate_junction_distance(candidate, junction):
    return abs(int(candidate.get("x", 0)) - int(junction.get("x", 0))) + abs(int(candidate.get("y", 0)) - int(junction.get("y", 0)))


def _promote_weak_nodes(weak_candidates, strong_nodes, segments, junctions, area_slug: str, config):
    promoted = []
    rejected = []
    tolerance = int(config["node_duplicate_tolerance"])
    attach_distance = int(config.get("line_attach_soft_distance", config["line_attach_distance"]))
    junction_distance = int(config.get("junction_attach_distance", 16))
    for candidate in sorted(list(weak_candidates or []), key=lambda item: (item["y"], item["x"], item["color_bucket"])):
        if _candidate_matches_existing_node(candidate, strong_nodes + promoted, tolerance):
            rejected.append({**candidate, "rejection_reason": "duplicate"})
            continue
        attached_segments = []
        for segment in segments:
            distance = _distance_to_segment(candidate["x"], candidate["y"], segment)
            if distance <= attach_distance:
                attached_segments.append(segment["id"])
        near_junction = any(_candidate_junction_distance(candidate, junction) <= junction_distance for junction in list(junctions or []))
        if not attached_segments and not near_junction:
            rejected.append({**candidate, "rejection_reason": "unattached"})
            continue
        node = _candidate_to_node(candidate, area_slug, "weak_promoted")
        node["promoted_from"] = "weak"
        node["promoted_segment_ids"] = sorted(set(attached_segments))
        if near_junction:
            node["promoted_from"] = "junction_override"
        promoted.append(node)
    return promoted, rejected


def _promote_rejected_fragments(rejected_candidates, raw_candidates, accepted_nodes, segments, junctions, area_slug: str, config):
    raw_lookup = {candidate.get("cluster_id"): candidate for candidate in list(raw_candidates or []) if candidate.get("cluster_id")}
    promoted = []
    rejected = []
    tolerance = int(config["node_duplicate_tolerance"])
    attach_distance = int(config.get("line_attach_soft_distance", config["line_attach_distance"]))
    junction_distance = int(config.get("junction_attach_distance", 16))
    for candidate in list(rejected_candidates or []):
        source_cluster_ids = list(candidate.get("source_cluster_ids") or [])
        if len(source_cluster_ids) <= 1:
            rejected.append({**candidate, "rejection_reason": "size_reject"})
            continue
        for cluster_id in source_cluster_ids:
            fragment = raw_lookup.get(cluster_id)
            if not fragment:
                continue
            if _candidate_matches_existing_node(fragment, accepted_nodes + promoted, tolerance):
                continue
            attached_segments = []
            for segment in segments:
                distance = _distance_to_segment(fragment["x"], fragment["y"], segment)
                if distance <= attach_distance:
                    attached_segments.append(segment["id"])
            near_junction = any(_candidate_junction_distance(fragment, junction) <= junction_distance for junction in list(junctions or []))
            if not attached_segments and not near_junction:
                rejected.append({**fragment, "rejection_reason": "merge_fail"})
                continue
            node = _candidate_to_node(fragment, area_slug, "forced_promoted")
            node["promoted_from"] = "rejected_fragment"
            node["promoted_segment_ids"] = sorted(set(attached_segments))
            if near_junction:
                node["promoted_from"] = "intersection_override"
            promoted.append(node)
    return promoted, rejected


def _build_segment_node_counts(corridor_graph):
    counts = defaultdict(set)
    for attachment in list(corridor_graph.get("attachments") or []):
        counts[str(attachment.get("segment_id") or "")].add(str(attachment.get("node_id") or ""))
    return [
        {"segment_id": segment.get("id"), "node_count": len(counts.get(segment.get("id"), set()))}
        for segment in list(corridor_graph.get("segments") or [])
    ]


def _infer_grid_spacing(nodes, config):
    x_diffs = []
    y_diffs = []
    for node in list(nodes or []):
        for other in list(nodes or []):
            if node.get("id") == other.get("id"):
                continue
            dx = abs(int(node.get("x", 0)) - int(other.get("x", 0)))
            dy = abs(int(node.get("y", 0)) - int(other.get("y", 0)))
            if dy <= 3 and int(config.get("grid_spacing_min", 12)) <= dx <= int(config.get("grid_spacing_max", 18)):
                x_diffs.append(dx)
            if dx <= 3 and int(config.get("grid_spacing_min", 12)) <= dy <= int(config.get("grid_spacing_max", 18)):
                y_diffs.append(dy)
    counts = defaultdict(int)
    for value in x_diffs + y_diffs:
        counts[value] += 1
    if not counts:
        return 14
    return max(sorted(counts), key=lambda value: counts[value])


def _node_like_pixel(pixel, config):
    if _is_gray_square_pixel(pixel, config):
        return True
    for bucket_name in MARKER_PALETTES:
        matched, _distance_value, _threshold = _pixel_matches_bucket(pixel, bucket_name, config)
        if matched:
            return True
    return False


def _local_node_support(img, center_x, center_y, config, radius=4):
    pixels = img.load()
    width, height = img.size
    support = 0
    for y in range(max(0, center_y - radius), min(height, center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(width, center_x + radius + 1)):
            if _node_like_pixel(pixels[x, y], config):
                support += 1
    return support


def _recover_grid_nodes_from_corridors(img, nodes, corridor_graph, area_slug: str, config):
    node_lookup = {str(node.get("id") or ""): node for node in list(nodes or [])}
    attachments_by_segment = defaultdict(list)
    for attachment in list(corridor_graph.get("attachments") or []):
        attachments_by_segment[str(attachment.get("segment_id") or "")].append(attachment)
    inferred_spacing = _infer_grid_spacing(nodes, config)
    recovered = []
    tolerance = int(config.get("node_duplicate_tolerance", 2))
    for segment in list(corridor_graph.get("segments") or []):
        attachments = [attachment for attachment in attachments_by_segment.get(str(segment.get("id") or ""), []) if str(attachment.get("node_id") or "") in node_lookup]
        if len(attachments) < 2:
            continue
        if segment.get("orientation") == "horizontal":
            ordered = sorted(attachments, key=lambda item: node_lookup[str(item.get("node_id"))]["x"])
        else:
            ordered = sorted(attachments, key=lambda item: node_lookup[str(item.get("node_id"))]["y"])
        for left, right in zip(ordered, ordered[1:]):
            left_node = node_lookup[str(left.get("node_id"))]
            right_node = node_lookup[str(right.get("node_id"))]
            gap = abs((right_node["x"] - left_node["x"]) if segment.get("orientation") == "horizontal" else (right_node["y"] - left_node["y"]))
            if gap < inferred_spacing * 1.5:
                continue
            steps = int(round(gap / inferred_spacing)) - 1
            for index in range(1, max(0, steps) + 1):
                if segment.get("orientation") == "horizontal":
                    center_x = int(round(left_node["x"] + inferred_spacing * index * (1 if right_node["x"] >= left_node["x"] else -1)))
                    center_y = int(segment.get("y1", 0))
                else:
                    center_x = int(segment.get("x1", 0))
                    center_y = int(round(left_node["y"] + inferred_spacing * index * (1 if right_node["y"] >= left_node["y"] else -1)))
                candidate = {
                    "x": center_x,
                    "y": center_y,
                    "w": 6,
                    "h": 6,
                    "bbox": {"x": center_x - 3, "y": center_y - 3, "w": 6, "h": 6},
                    "color_bucket": "gray",
                    "confidence": 0.35,
                    "source_cluster_ids": [f"grid-{segment.get('id')}-{index}"],
                }
                if _candidate_matches_existing_node(candidate, nodes + recovered, tolerance):
                    continue
                if _local_node_support(img, center_x, center_y, config) < int(config.get("grid_gap_support_threshold", 12)):
                    continue
                node = _candidate_to_node(candidate, area_slug, "grid_recovered")
                node["promoted_from"] = "grid_gap_recovery"
                node["promoted_segment_ids"] = [segment.get("id")]
                recovered.append(node)
    return recovered, inferred_spacing


def _derive_grid_adjacency_edges(nodes, audits, config, inferred_spacing=None):
    spacing = int(inferred_spacing or _infer_grid_spacing(nodes, config))
    spacing_tolerance = int(config.get("grid_adjacency_tolerance", 2))
    axis_tolerance = int(config.get("grid_axis_tolerance", 3))
    recovered = []

    for source in list(nodes or []):
        best_by_direction = {}
        for target in list(nodes or []):
            if source.get("id") == target.get("id"):
                continue
            dx = int(target.get("x", 0)) - int(source.get("x", 0))
            dy = int(target.get("y", 0)) - int(source.get("y", 0))
            direction = None
            distance = None
            if abs(dy) <= axis_tolerance and abs(abs(dx) - spacing) <= spacing_tolerance:
                direction = "east" if dx > 0 else "west"
                distance = abs(dx)
            elif abs(dx) <= axis_tolerance and abs(abs(dy) - spacing) <= spacing_tolerance:
                direction = "south" if dy > 0 else "north"
                distance = abs(dy)
            if not direction:
                continue
            current = best_by_direction.get(direction)
            score = (distance, abs(dx) + abs(dy))
            if current is None or score < current[0]:
                best_by_direction[direction] = (score, target)
        for direction, (_score, target) in best_by_direction.items():
            if (source.get("id"), direction) in audits:
                continue
            recovered.append({
                "source": source.get("id"),
                "target": target.get("id"),
                "direction": direction,
                "derivation_method": "grid_adjacency",
                "confidence": 0.72,
            })
    return recovered


def _build_marker_recovery_report(area_slug: str, marker_report, merged_candidates, accepted_nodes, weak_promoted_nodes, forced_promoted_nodes, weak_rejected_candidates, fragment_rejected_candidates):
    raw_candidates = list(marker_report.get("raw_candidates") or [])
    merged_by_source = {}
    for candidate in list(merged_candidates or []):
        for cluster_id in list(candidate.get("source_cluster_ids") or []):
            merged_by_source[cluster_id] = candidate

    accepted_cluster_ids = set()
    forced_cluster_ids = set()
    for node in list(accepted_nodes or []):
        accepted_cluster_ids.update(node.get("source_cluster_ids") or [])
    for node in list(forced_promoted_nodes or []):
        forced_cluster_ids.update(node.get("source_cluster_ids") or [])

    cluster_reasons = []
    for candidate in raw_candidates:
        cluster_id = candidate.get("cluster_id")
        merged_candidate = merged_by_source.get(cluster_id)
        reason = "accepted"
        if cluster_id in forced_cluster_ids:
            reason = "forced_promoted"
        elif cluster_id in accepted_cluster_ids:
            source_ids = list((merged_candidate or {}).get("source_cluster_ids") or [])
            reason = "merge_accept" if len(source_ids) > 1 else "accepted"
        elif merged_candidate and merged_candidate.get("candidate_class") == "rejected":
            reason = "merge_fail" if len(list(merged_candidate.get("source_cluster_ids") or [])) > 1 else "size_reject"
        elif merged_candidate and merged_candidate.get("candidate_class") == "weak":
            reason = "overlap_reject"
        cluster_reasons.append({
            "cluster_id": cluster_id,
            "x": candidate.get("x"),
            "y": candidate.get("y"),
            "reason": reason,
            "merged_candidate_bbox": (merged_candidate or {}).get("bbox"),
        })

    report = {
        "raw_cluster_count": marker_report.get("raw_cluster_count", 0),
        "candidate_count": marker_report.get("candidate_count", 0),
        "accepted_count": len(accepted_nodes or []),
        "weak_candidate_count": marker_report.get("weak_candidate_count", 0),
        "rejected_count": marker_report.get("rejected_count", 0),
        "weak_promoted_count": len(weak_promoted_nodes or []),
        "forced_promoted_count": len(forced_promoted_nodes or []),
        "missing_count": max(0, int(marker_report.get("raw_cluster_count", 0)) - len(accepted_nodes or [])),
        "coverage": round(len(accepted_nodes or []) / max(int(marker_report.get("raw_cluster_count", 0)), 1), 4),
        "rejected_reasons": {
            "weak_rejected": len(weak_rejected_candidates or []),
            "fragment_rejected": len(fragment_rejected_candidates or []),
        },
        "cluster_reasons": cluster_reasons,
        "weak_candidates": marker_report.get("weak_candidates") or [],
        "rejected_candidates": marker_report.get("rejected_candidates") or [],
        "weak_promoted_nodes": weak_promoted_nodes or [],
        "forced_promoted_nodes": forced_promoted_nodes or [],
        "weak_rejected_candidates": weak_rejected_candidates or [],
        "fragment_rejected_candidates": fragment_rejected_candidates or [],
    }
    save_json(_artifact_dir(area_slug) / "marker_recovery_report.json", report)
    return report


def _point_in_marker_bbox(x, y, node, expand=0):
    bbox = node.get("bbox") or {}
    return bbox.get("x", 0) - expand <= x <= bbox.get("x", 0) + bbox.get("w", 0) - 1 + expand and bbox.get("y", 0) - expand <= y <= bbox.get("y", 0) + bbox.get("h", 0) - 1 + expand


def _build_dark_line_mask(img, node_preserve_mask, config):
    pixels = img.load()
    width, height = img.size
    max_intensity = int(config["line_dark_intensity_max"])
    max_delta = int(config["line_dark_channel_delta_max"])
    mask = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if node_preserve_mask and node_preserve_mask[y][x]:
                continue
            red, green, blue = pixels[x, y]
            intensity = (red + green + blue) // 3
            channel_delta = max(red, green, blue) - min(red, green, blue)
            if intensity <= max_intensity and channel_delta <= max_delta:
                mask[y][x] = True
    thickened = mask
    for _ in range(max(0, int(config.get("line_thicken_passes", 0)))):
        thickened = _subtract_mask(_dilate(thickened), node_preserve_mask)
    return _subtract_mask(_cleanup_mask(thickened), node_preserve_mask)


def _scan_line_segments(mask, orientation):
    height = len(mask)
    width = len(mask[0]) if height else 0
    segments = []
    if orientation == "horizontal":
        for y in range(height):
            start = None
            for x in range(width + 1):
                occupied = x < width and mask[y][x]
                if occupied and start is None:
                    start = x
                elif not occupied and start is not None:
                    segments.append({"x1": start, "y1": y, "x2": x - 1, "y2": y, "orientation": "horizontal", "length": x - start})
                    start = None
    else:
        for x in range(width):
            start = None
            for y in range(height + 1):
                occupied = y < height and mask[y][x]
                if occupied and start is None:
                    start = y
                elif not occupied and start is not None:
                    segments.append({"x1": x, "y1": start, "x2": x, "y2": y - 1, "orientation": "vertical", "length": y - start})
                    start = None
    return segments


def _merge_collinear_segments(segments, config):
    merged = []
    remaining = sorted(list(segments or []), key=lambda item: (item["orientation"], item["y1"], item["x1"]))
    align_tolerance = int(config["line_merge_alignment_tolerance"])
    gap_tolerance = int(config["line_merge_gap"])
    while remaining:
        current = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            for index, candidate in enumerate(list(remaining)):
                if candidate["orientation"] != current["orientation"]:
                    continue
                if current["orientation"] == "horizontal":
                    if abs(candidate["y1"] - current["y1"]) > align_tolerance:
                        continue
                    if candidate["x1"] > current["x2"] + gap_tolerance + 1 or current["x1"] > candidate["x2"] + gap_tolerance + 1:
                        continue
                    current = {"x1": min(current["x1"], candidate["x1"]), "y1": int(round((current["y1"] + candidate["y1"]) / 2)), "x2": max(current["x2"], candidate["x2"]), "y2": int(round((current["y2"] + candidate["y2"]) / 2)), "orientation": "horizontal", "length": max(current["x2"], candidate["x2"]) - min(current["x1"], candidate["x1"]) + 1}
                else:
                    if abs(candidate["x1"] - current["x1"]) > align_tolerance:
                        continue
                    if candidate["y1"] > current["y2"] + gap_tolerance + 1 or current["y1"] > candidate["y2"] + gap_tolerance + 1:
                        continue
                    current = {"x1": int(round((current["x1"] + candidate["x1"]) / 2)), "y1": min(current["y1"], candidate["y1"]), "x2": int(round((current["x2"] + candidate["x2"]) / 2)), "y2": max(current["y2"], candidate["y2"]), "orientation": "vertical", "length": max(current["y2"], candidate["y2"]) - min(current["y1"], candidate["y1"]) + 1}
                remaining.pop(index)
                changed = True
                break
        merged.append(current)
    return merged


def _segment_length(segment):
    return int(segment.get("length") or max(abs(segment["x2"] - segment["x1"]), abs(segment["y2"] - segment["y1"])) + 1)


def _distance_to_segment(point_x, point_y, segment):
    if segment["orientation"] == "horizontal":
        clamped_x = min(max(point_x, segment["x1"]), segment["x2"])
        return abs(point_y - segment["y1"]) + abs(point_x - clamped_x)
    clamped_y = min(max(point_y, segment["y1"]), segment["y2"])
    return abs(point_x - segment["x1"]) + abs(point_y - clamped_y)


def _marker_attachment_side(node, segment):
    center_x = node["x"]
    center_y = node["y"]
    if segment["orientation"] == "horizontal":
        if center_x <= segment["x1"]:
            return "left"
        if center_x >= segment["x2"]:
            return "right"
        return "top" if center_y < segment["y1"] else "bottom"
    if center_y <= segment["y1"]:
        return "top"
    if center_y >= segment["y2"]:
        return "bottom"
    return "left" if center_x < segment["x1"] else "right"


def _build_junctions(segments, config):
    tolerance = int(config["junction_tolerance"])
    horizontal = [segment for segment in segments if segment["orientation"] == "horizontal"]
    vertical = [segment for segment in segments if segment["orientation"] == "vertical"]
    junctions = []
    for h_segment in horizontal:
        for v_segment in vertical:
            if h_segment["x1"] - tolerance <= v_segment["x1"] <= h_segment["x2"] + tolerance and v_segment["y1"] - tolerance <= h_segment["y1"] <= v_segment["y2"] + tolerance:
                junctions.append({"id": f"junction-{len(junctions) + 1:03d}", "x": int(v_segment["x1"]), "y": int(h_segment["y1"]), "segment_ids": []})
    return junctions


def _assign_segment_ids(segments):
    for index, segment in enumerate(segments, start=1):
        segment["id"] = f"segment-{index:03d}"
    return segments


def _attach_markers_to_corridors(nodes, segments, junctions, config):
    attachment_limit = int(config["line_attach_distance"])
    soft_attachment_limit = max(attachment_limit, int(config.get("line_attach_soft_distance", attachment_limit)))
    attachments = []
    for junction in junctions:
        junction["segment_ids"] = []
    for segment in segments:
        if segment["orientation"] == "horizontal":
            for junction in junctions:
                if segment["x1"] <= junction["x"] <= segment["x2"] and abs(segment["y1"] - junction["y"]) <= int(config["junction_tolerance"]):
                    junction["segment_ids"].append(segment["id"])
        else:
            for junction in junctions:
                if segment["y1"] <= junction["y"] <= segment["y2"] and abs(segment["x1"] - junction["x"]) <= int(config["junction_tolerance"]):
                    junction["segment_ids"].append(segment["id"])
    for node in nodes:
        attached_segment_ids = []
        raw_attached_segment_ids = []
        for segment in segments:
            distance = _distance_to_segment(node["x"], node["y"], segment)
            if distance > soft_attachment_limit:
                continue
            raw_attached_segment_ids.append(segment["id"])
            attachments.append({
                "node_id": node["id"],
                "segment_id": segment["id"],
                "distance": distance,
                "side": _marker_attachment_side(node, segment),
                "anchor": {"x": node["x"], "y": node["y"]},
                "attachment_strength": "primary" if distance <= attachment_limit else "soft",
            })
            attached_segment_ids.append(segment["id"])
        node["raw_attached_segment_ids"] = sorted(set(raw_attached_segment_ids))
        node["attached_segment_ids"] = sorted(set(attached_segment_ids))
    clustered_segment_ids = set()
    for junction in junctions:
        if len(junction["segment_ids"]) >= 2:
            clustered_segment_ids.update(junction["segment_ids"])
    filtered_segments = []
    for segment in segments:
        attached_node_ids = {attachment["node_id"] for attachment in attachments if attachment["segment_id"] == segment["id"]}
        if (
            _segment_length(segment) >= int(config["line_min_length"])
            or segment["id"] in clustered_segment_ids
            or len(attached_node_ids) >= 2
            or any(attachment["segment_id"] == segment["id"] and attachment.get("attachment_strength") == "primary" for attachment in attachments)
        ):
            filtered_segments.append(segment)
    filtered_lookup = {segment["id"]: segment for segment in filtered_segments}
    filtered_attachments = [attachment for attachment in attachments if attachment["segment_id"] in filtered_lookup]
    filtered_junctions = []
    for junction in junctions:
        segment_ids = [segment_id for segment_id in junction["segment_ids"] if segment_id in filtered_lookup]
        if segment_ids:
            filtered_junctions.append({**junction, "segment_ids": sorted(segment_ids)})
    component_neighbors = defaultdict(set)
    for junction in filtered_junctions:
        for segment_id in junction["segment_ids"]:
            for other_segment_id in junction["segment_ids"]:
                if segment_id != other_segment_id:
                    component_neighbors[segment_id].add(other_segment_id)
    segment_components = {}
    next_component = 0
    for segment in filtered_segments:
        segment_id = segment["id"]
        if segment_id in segment_components:
            continue
        next_component += 1
        queue = deque([segment_id])
        segment_components[segment_id] = next_component
        while queue:
            current = queue.popleft()
            for neighbor in component_neighbors.get(current, set()):
                if neighbor in segment_components:
                    continue
                segment_components[neighbor] = next_component
                queue.append(neighbor)
    for segment in filtered_segments:
        segment["component_id"] = segment_components.get(segment["id"], 0)
    for attachment in filtered_attachments:
        segment = filtered_lookup.get(attachment["segment_id"])
        attachment["component_id"] = segment.get("component_id", 0) if segment else 0
    for node in nodes:
        node["attached_segment_ids"] = sorted({attachment["segment_id"] for attachment in filtered_attachments if attachment["node_id"] == node["id"]})
        node["attached_component_ids"] = sorted({attachment["component_id"] for attachment in filtered_attachments if attachment["node_id"] == node["id"]})
    return {"segments": filtered_segments, "junctions": filtered_junctions, "attachments": filtered_attachments}


def _distance(left: dict, right: dict) -> float:
    dx = float(left["x"] - right["x"])
    dy = float(left["y"] - right["y"])
    return (dx * dx + dy * dy) ** 0.5


def _candidate_direction(source, target, config):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    abs_x = abs(dx)
    abs_y = abs(dy)
    if abs_y <= 6 and 10 <= abs_x <= int(config["orthogonal_distance_max"]):
        return ("east" if dx > 0 else "west", abs_x)
    if abs_x <= 6 and 10 <= abs_y <= int(config["orthogonal_distance_max"]):
        return ("south" if dy > 0 else "north", abs_y)
    if bool(config["allow_diagonal_edges"]) and abs(abs_x - abs_y) <= 4 and 10 <= abs_x <= int(config["diagonal_distance_max"]):
        if dx > 0 and dy > 0:
            return ("southeast", (abs_x + abs_y) / 2)
        if dx > 0 and dy < 0:
            return ("northeast", (abs_x + abs_y) / 2)
        if dx < 0 and dy > 0:
            return ("southwest", (abs_x + abs_y) / 2)
        return ("northwest", (abs_x + abs_y) / 2)
    return (None, None)


def _sample_has_path(img, source, target, config=None):
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
    hit_ratio = float((config or {}).get("fallback_sampling_hit_ratio", DEFAULT_EXTRACT_CONFIG["fallback_sampling_hit_ratio"]))
    return total_count > 0 and (hit_count / total_count) >= hit_ratio


def _coarse_direction(source, target, config):
    dx = target["x"] - source["x"]
    dy = target["y"] - source["y"]
    abs_x = abs(dx)
    abs_y = abs(dy)
    if max(abs_x, abs_y) < 8:
        return None
    if abs_x >= abs_y:
        return "east" if dx > 0 else "west"
    return "south" if dy > 0 else "north"


def _recover_isolated_component_edges(nodes, audits, config):
    connected_nodes = {edge["source"] for edge in audits.values()} | {edge["target"] for edge in audits.values()}
    max_distance = float(config.get("isolated_recovery_max_distance", 110))
    recovered = []
    for source in nodes:
        if source["id"] in connected_nodes:
            continue
        component_ids = set(source.get("attached_component_ids") or [])
        if not component_ids:
            continue
        candidates = []
        for target in nodes:
            if target["id"] == source["id"]:
                continue
            if not component_ids.intersection(target.get("attached_component_ids") or []):
                continue
            distance = _distance(source, target)
            if distance > max_distance:
                continue
            direction = _candidate_direction(source, target, config)[0] or _coarse_direction(source, target, config)
            if not direction:
                continue
            candidates.append((distance, direction, target))
        seen_directions = set()
        for distance, direction, target in sorted(candidates, key=lambda item: item[0]):
            if direction in seen_directions:
                continue
            seen_directions.add(direction)
            recovered.append({
                "source": source["id"],
                "target": target["id"],
                "direction": direction,
                "derivation_method": "isolated_component_recovery",
                "confidence": round(max(0.22, 1.0 - (distance / max(max_distance, 1.0))), 4),
            })
    return recovered


def _derive_edges_from_corridors(img, nodes, corridor_graph, config, inferred_grid_spacing=None):
    node_lookup = {node["id"]: node for node in nodes}
    segment_lookup = {segment["id"]: segment for segment in corridor_graph["segments"]}
    attachments_by_segment = defaultdict(list)
    for attachment in corridor_graph["attachments"]:
        attachments_by_segment[attachment["segment_id"]].append(attachment)
    audits = {}

    def register_edge(source_id, target_id, direction, method, confidence):
        if not source_id or not target_id or not direction or source_id == target_id:
            return
        key = (source_id, direction)
        payload = {"source": source_id, "target": target_id, "direction": direction, "derivation_method": method, "confidence": round(confidence, 4)}
        existing = audits.get(key)
        if existing is None or payload["confidence"] > existing["confidence"]:
            audits[key] = payload

    for segment_id, attachments in attachments_by_segment.items():
        segment = segment_lookup.get(segment_id)
        if not segment:
            continue
        if segment["orientation"] == "horizontal":
            ordered = sorted(attachments, key=lambda item: (node_lookup[item["node_id"]]["x"], node_lookup[item["node_id"]]["y"]))
        else:
            ordered = sorted(attachments, key=lambda item: (node_lookup[item["node_id"]]["y"], node_lookup[item["node_id"]]["x"]))
        for left, right in zip(ordered, ordered[1:]):
            source = node_lookup[left["node_id"]]
            target = node_lookup[right["node_id"]]
            direction, _distance_value = _candidate_direction(source, target, config)
            if not direction:
                continue
            confidence = max(0.5, 1.0 - ((left["distance"] + right["distance"]) / 40.0))
            register_edge(source["id"], target["id"], direction, "corridor", confidence)
            reverse = OPPOSITE_DIRECTIONS.get(direction)
            if reverse:
                register_edge(target["id"], source["id"], reverse, "corridor", confidence)

    for junction in corridor_graph["junctions"]:
        nearest_per_segment = []
        for segment_id in junction["segment_ids"]:
            candidates = [attachment for attachment in attachments_by_segment.get(segment_id, []) if attachment["node_id"] in node_lookup]
            if not candidates:
                continue
            nearest = min(candidates, key=lambda item: abs(node_lookup[item["node_id"]]["x"] - junction["x"]) + abs(node_lookup[item["node_id"]]["y"] - junction["y"]))
            nearest_per_segment.append(nearest)
        for index, left in enumerate(nearest_per_segment):
            for right in nearest_per_segment[index + 1:]:
                source = node_lookup[left["node_id"]]
                target = node_lookup[right["node_id"]]
                direction, _distance_value = _candidate_direction(source, target, config)
                if not direction:
                    continue
                confidence = max(0.35, 1.0 - ((left["distance"] + right["distance"]) / 50.0))
                register_edge(source["id"], target["id"], direction, "corridor", confidence)
                reverse = OPPOSITE_DIRECTIONS.get(direction)
                if reverse:
                    register_edge(target["id"], source["id"], reverse, "corridor", confidence)

    for recovered_edge in _recover_isolated_component_edges(nodes, audits, config):
        register_edge(recovered_edge["source"], recovered_edge["target"], recovered_edge["direction"], recovered_edge["derivation_method"], recovered_edge["confidence"])

    for recovered_edge in _derive_grid_adjacency_edges(nodes, audits, config, inferred_spacing=inferred_grid_spacing):
        register_edge(recovered_edge["source"], recovered_edge["target"], recovered_edge["direction"], recovered_edge["derivation_method"], recovered_edge["confidence"])

    if bool(config["fallback_sampling"]):
        isolated_only = bool(config.get("fallback_sampling_isolated_only", True))
        sourced_edges = {edge["source"] for edge in audits.values()}
        for source in nodes:
            if isolated_only and source["id"] in sourced_edges:
                continue
            directional_candidates = {}
            for target in nodes:
                if source["id"] == target["id"]:
                    continue
                direction, distance = _candidate_direction(source, target, config)
                if not direction:
                    continue
                current = directional_candidates.get(direction)
                if current is None or distance < current[0]:
                    directional_candidates[direction] = (distance, target)
            for direction, (_distance_value, target) in directional_candidates.items():
                if (source["id"], direction) in audits:
                    continue
                if _sample_has_path(img, source, target, config=config):
                    register_edge(source["id"], target["id"], direction, "fallback_sample", 0.35)

    ordered_edges = []
    for edge in sorted(audits.values(), key=lambda item: (item["source"], item["direction"], item["target"])):
        ordered_edges.append((edge["source"], edge["direction"], edge["target"], edge))
    return ordered_edges, list(sorted(audits.values(), key=lambda item: (item["source"], item["direction"], item["target"])))


def _build_isolated_node_audit(nodes, exit_audit):
    sourced_nodes = {edge.get("source") for edge in exit_audit}
    targeted_nodes = {edge.get("target") for edge in exit_audit}
    connected_node_ids = sourced_nodes | targeted_nodes
    audit = []
    for node in nodes:
        node_id = node.get("id")
        if node_id in connected_node_ids:
            continue
        raw_segments = list(node.get("raw_attached_segment_ids") or [])
        filtered_segments = list(node.get("attached_segment_ids") or [])
        if not raw_segments:
            reason = "no_line_attach"
        elif not filtered_segments:
            reason = "filtered_out"
        else:
            reason = "no_segment_match"
        audit.append({
            "node_id": node_id,
            "reason": reason,
            "raw_attached_segment_ids": raw_segments,
            "attached_segment_ids": filtered_segments,
            "attached_component_ids": list(node.get("attached_component_ids") or []),
        })
    return sorted(audit, key=lambda item: str(item.get("node_id") or ""))


def _is_local_room_label(line, config):
    text = normalize_ocr_text(line.get("text"))
    if not text or line.get("label_type") in {"travel_label", "noise", "district_landmark"}:
        return False
    if float(line.get("confidence", 0.0)) < float(config["min_room_label_confidence"]):
        return False
    if float(line.get("quality_score", 0.0)) < float(config["min_room_label_quality"]):
        return False
    if len(text.split()) > int(config["max_room_label_words"]):
        return False
    if int(line.get("w", 0)) > int(config["max_room_label_box"]):
        return False
    return int(line.get("w", 0)) * int(line.get("h", 0)) <= int(config["room_label_area_max"])


def _attach_node_labels(nodes, ocr_lines, config):
    attachment_audit = []
    for node in nodes:
        best = None
        best_distance = None
        for line in ocr_lines:
            if not _is_local_room_label(line, config):
                continue
            distance = _distance(node, line)
            if distance > float(config["node_label_radius"]):
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
        if best:
            attachment_audit.append({"text": best.get("text"), "bbox": {"x": best.get("x"), "y": best.get("y"), "w": best.get("w"), "h": best.get("h")}, "attachment_target_id": node["id"], "attachment_role": "room_name"})
    return attachment_audit


def _is_boxed_travel_label(line, line_mask):
    x = int(line.get("x", 0))
    y = int(line.get("y", 0))
    width = max(1, int(line.get("w", 0)))
    height = max(1, int(line.get("h", 0)))
    mask_height = len(line_mask)
    mask_width = len(line_mask[0]) if mask_height else 0
    if not mask_height or not mask_width:
        return False
    left = max(0, x - 2)
    top = max(0, y - 2)
    right = min(mask_width - 1, x + width + 1)
    bottom = min(mask_height - 1, y + height + 1)
    border_points = []
    for check_x in range(left, right + 1):
        border_points.append((check_x, top))
        border_points.append((check_x, bottom))
    for check_y in range(top, bottom + 1):
        border_points.append((left, check_y))
        border_points.append((right, check_y))
    hits = sum(1 for check_x, check_y in border_points if line_mask[check_y][check_x])
    return bool(border_points) and hits / len(border_points) >= 0.16


def _infer_special_target_text(text):
    normalized = normalize_ocr_text(text)
    match = BOXED_TRAVEL_RE.search(normalized)
    if match:
        return match.group(0)
    if " to " in normalized.lower():
        parts = re.split(r" to ", normalized, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            return parts[1].strip()
    return ""


def _build_special_exit_candidates(nodes, ocr_lines, corridor_graph, line_mask):
    attachment_audit = []
    candidates = []
    segment_lookup = {segment["id"]: segment for segment in corridor_graph["segments"]}
    segment_endpoints = []
    for segment in corridor_graph["segments"]:
        segment_endpoints.append((segment["id"], {"x": segment["x1"], "y": segment["y1"]}))
        segment_endpoints.append((segment["id"], {"x": segment["x2"], "y": segment["y2"]}))
    for line in ocr_lines:
        text = normalize_ocr_text(line.get("text"))
        if not text:
            continue
        role = "ignored"
        attachment_target_id = None
        boxed = _is_boxed_travel_label(line, line_mask)
        if is_exit_command(text) or boxed or line.get("label_type") == "travel_label":
            nearest_node = min(nodes, key=lambda node: _distance(node, line), default=None)
            nearest_endpoint = min(segment_endpoints, key=lambda item: _distance(item[1], line), default=(None, None))
            source_node_id = nearest_node["id"] if nearest_node else None
            if nearest_endpoint[0] and (nearest_node is None or _distance(nearest_endpoint[1], line) < _distance(nearest_node, line)):
                segment = segment_lookup.get(nearest_endpoint[0])
                if segment:
                    component_nodes = [node for node in nodes if segment.get("component_id", 0) in node.get("attached_component_ids", [])]
                    if component_nodes:
                        nearest_node = min(component_nodes, key=lambda node: _distance(node, line))
                        source_node_id = nearest_node["id"]
            if source_node_id:
                role = "special_exit_candidate"
                attachment_target_id = source_node_id
                candidates.append({"label": text, "x": line.get("x"), "y": line.get("y"), "source_node_id": source_node_id, "candidate_target_text": _infer_special_target_text(text), "confidence": line.get("confidence", 0.0), "boxed": boxed})
        elif line.get("label_type") == "district_landmark":
            role = "landmark"
        attachment_audit.append({"text": text, "bbox": {"x": line.get("x"), "y": line.get("y"), "w": line.get("w"), "h": line.get("h")}, "attachment_target_id": attachment_target_id, "attachment_role": role})
    return candidates, attachment_audit


def _attach_edge_labels(edges, nodes, ocr_lines, config):
    node_lookup = {node["id"]: node for node in nodes}
    enriched = []
    for source_id, direction, target_id, edge_audit in edges:
        source = node_lookup[source_id]
        target = node_lookup[target_id]
        midpoint = {"x": (source["x"] + target["x"]) / 2, "y": (source["y"] + target["y"]) / 2}
        best = None
        best_distance = None
        for line in ocr_lines:
            if line.get("label_type") == "travel_label":
                continue
            distance = _distance(midpoint, line)
            if distance > float(config["edge_label_radius"]):
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
            "auto_reverse": bool(edge_audit.get("auto_reverse", False)),
            "confidence_tier": classify_confidence(score_label_confidence(best_distance, best.get("confidence", 0.0))) if best else classify_confidence(edge_audit.get("confidence", 0.0)),
            "needs_review": False,
            "derivation_method": edge_audit.get("derivation_method", "corridor"),
            "derivation_confidence": edge_audit.get("confidence", 0.0),
        }
        enriched.append((source_id, direction, target_id, edge_data))
    return enriched


def extract_yaml_graph_area_spec(map_path, area_id, use_ocr=True, use_ai_adjudication=False, profile=None, style_settings=None):
    del use_ai_adjudication, profile
    area_slug = _slugify_area_id(area_id)
    config = _extract_config(style_settings)
    image = _load_map_image(map_path)
    nodes, weak_candidates, marker_report, node_preserve_mask = _detect_nodes(image, area_slug, config)
    line_mask = _build_dark_line_mask(image, node_preserve_mask, config)
    _write_debug_mask(area_slug, "debug_line_mask.png", line_mask, bool(config["debug_lines"]))
    _write_debug_mask(area_slug, "debug_node_mask.png", node_preserve_mask, bool(config["debug_markers"]))
    raw_segments = _scan_line_segments(line_mask, "horizontal") + _scan_line_segments(line_mask, "vertical")
    _write_debug_json(area_slug, "debug_line_segments.json", raw_segments, bool(config["debug_lines"]))
    merged_segments = _assign_segment_ids(_merge_collinear_segments(raw_segments, config))
    junctions = _build_junctions(merged_segments, config)
    promoted_weak_nodes, rejected_weak_nodes = _promote_weak_nodes(weak_candidates, nodes, merged_segments, junctions, area_slug, config)
    forced_promoted_nodes, fragment_rejected_candidates = _promote_rejected_fragments(marker_report.get("rejected_candidates") or [], marker_report.get("raw_candidates") or [], nodes + promoted_weak_nodes, merged_segments, junctions, area_slug, config)
    nodes = nodes + promoted_weak_nodes + forced_promoted_nodes
    merged_candidates = _merge_marker_fragments(list(marker_report.get("raw_candidates") or []), config)
    marker_report = _build_marker_recovery_report(
        area_slug,
        marker_report,
        merged_candidates,
        nodes,
        promoted_weak_nodes,
        forced_promoted_nodes,
        rejected_weak_nodes,
        fragment_rejected_candidates,
    )
    corridor_graph = _attach_markers_to_corridors(nodes, merged_segments, junctions, config)
    grid_recovered_nodes = []
    inferred_grid_spacing = _infer_grid_spacing(nodes, config)
    segment_node_counts = _build_segment_node_counts(corridor_graph)
    _write_debug_json(area_slug, "debug_corridor_graph.json", {"segments": corridor_graph["segments"], "junctions": corridor_graph["junctions"], "attached_nodes": corridor_graph["attachments"]}, bool(config["debug_corridors"]))
    spatial_edges, exit_audit = _derive_edges_from_corridors(image, nodes, corridor_graph, config, inferred_grid_spacing=inferred_grid_spacing)
    isolated_node_audit = _build_isolated_node_audit(nodes, exit_audit)
    _write_debug_json(area_slug, "debug_exit_derivation.json", exit_audit, bool(config["debug_corridors"]))
    _write_debug_json(area_slug, "debug_isolated_nodes.json", isolated_node_audit, bool(config["debug_corridors"]))

    ocr_bundle = None
    ocr_lines = []
    if use_ocr and ocr_available():
        try:
            ocr_bundle = extract_ocr_bundle(map_path)
        except RuntimeError:
            ocr_bundle = None
        else:
            ocr_lines = list(ocr_bundle.get("lines") or [])

    ocr_attachment_audit = _attach_node_labels(nodes, ocr_lines, config)
    special_exit_candidates, special_attachment_audit = _build_special_exit_candidates(nodes, ocr_lines, corridor_graph, line_mask)
    ocr_attachment_audit.extend(special_attachment_audit)
    _write_debug_json(area_slug, "debug_ocr_attachments.json", ocr_attachment_audit, bool(config["debug_ocr"]))

    artifact_edges = _attach_edge_labels(spatial_edges, nodes, ocr_lines, config)
    return {
        "nodes": nodes,
        "edges": artifact_edges,
        "meta": {
            "area_id": area_id,
            "area_slug": area_slug,
            "area_name": str(area_id or "").replace("_", " ").replace("-", " ").title(),
            "ocr_used": bool(ocr_bundle),
            "node_count": len(nodes),
            "raw_cluster_count": marker_report["raw_cluster_count"],
            "weak_marker_candidate_count": marker_report["weak_candidate_count"],
            "weak_marker_promoted_count": marker_report["weak_promoted_count"],
            "forced_marker_promoted_count": marker_report.get("forced_promoted_count", 0),
            "missing_marker_count": marker_report.get("missing_count", 0),
            "marker_coverage": marker_report.get("coverage", 0.0),
            "under_detected": len(nodes) < 170,
            "grid_recovered_count": len(grid_recovered_nodes),
            "inferred_grid_spacing": inferred_grid_spacing,
            "weak_nodes": promoted_weak_nodes,
            "edge_count": len(artifact_edges),
            "pipeline": "yaml_graph",
            "corridor_segments": corridor_graph["segments"],
            "corridor_segment_count": len(corridor_graph["segments"]),
            "segment_node_counts": segment_node_counts,
            "special_exit_candidates": special_exit_candidates,
            "special_exit_candidate_count": len(special_exit_candidates),
            "ocr_label_candidates": ocr_lines,
            "ocr_attachment_audit": ocr_attachment_audit,
            "exit_derivation": exit_audit,
            "isolated_node_audit": isolated_node_audit,
            "isolated_node_count": len(isolated_node_audit),
            "unnamed_room_count": sum(1 for node in nodes if not node.get("final_label")),
            "source_image": str(map_path),
        },
    }


def extract_yaml_graph_area_spec_v2(map_path, area_id, use_ocr=True, use_ai_adjudication=False, profile=None, style_settings=None):
    from .cv_pipeline import LineDetectConfig, attach_rooms_to_corridors, build_line_mask, corridors_to_edges, extract_corridor_graph, load_bgr

    del use_ai_adjudication, profile
    area_slug = _slugify_area_id(area_id)
    config = _extract_config(style_settings)
    image = _load_map_image(map_path)
    image_bgr = load_bgr(str(map_path))
    nodes, weak_candidates, marker_report, node_preserve_mask = _detect_nodes_cv_v2(map_path, area_slug)
    del weak_candidates
    line_cfg = LineDetectConfig(debug_output_dir=_artifact_dir(area_slug))
    line_mask = build_line_mask(image_bgr, node_preserve_mask, cfg=line_cfg)
    _write_debug_mask(area_slug, "debug_node_mask.png", node_preserve_mask, bool(config["debug_markers"]))
    promoted_weak_nodes = []
    raw_corridor_graph = extract_corridor_graph(line_mask, cfg=line_cfg)
    raw_attachments = attach_rooms_to_corridors(
        nodes,
        raw_corridor_graph["segments"],
        max_distance=int(config.get("line_attach_distance", 20)),
        cfg=line_cfg,
    )
    room_attachment_counts = defaultdict(int)
    for attached_room_ids in raw_attachments.values():
        for room_id in attached_room_ids:
            room_attachment_counts[str(room_id)] += 1
    attached_room_ids = {room_id for room_id, count in room_attachment_counts.items() if count > 0}
    unattached_room_ids = sorted(node["id"] for node in nodes if node["id"] not in attached_room_ids)
    for node in nodes:
        attachment_count = room_attachment_counts.get(str(node.get("id") or ""), 0)
        node["corridor_attachment_count"] = attachment_count
        if attachment_count == 0:
            node["review_flag"] = "no_corridor_attachment"

    attached_segments = []
    edge_segments = []
    for segment in raw_corridor_graph["segments"]:
        attachment_count = len(raw_attachments.get(segment.get("id"), []))
        if attachment_count < 1:
            continue
        next_segment = dict(segment)
        next_segment["dead_end"] = attachment_count == 1
        attached_segments.append(next_segment)
        edge_segments.append(next_segment)
    edge_segment_ids = {segment.get("id") for segment in edge_segments}
    edge_attachments = {segment_id: sorted(raw_attachments.get(segment_id, [])) for segment_id in edge_segment_ids}
    edge_segment_pixels = {
        (int(pixel.get("x", 0)), int(pixel.get("y", 0)))
        for segment in edge_segments
        for pixel in list(segment.get("pixels") or [])
    }
    junction_keep_radius = max(3, int(line_cfg.junction_dilate) + 1)
    filtered_junctions = [
        junction
        for junction in raw_corridor_graph["junctions"]
        if any(
            (int(junction.get("x", 0)) + dx, int(junction.get("y", 0)) + dy) in edge_segment_pixels
            for dx in range(-junction_keep_radius, junction_keep_radius + 1)
            for dy in range(-junction_keep_radius, junction_keep_radius + 1)
        )
    ]
    filtered_debug_mask = [[False] * len(line_mask[0]) for _ in range(len(line_mask))]
    for pixel_x, pixel_y in edge_segment_pixels:
        filtered_debug_mask[pixel_y][pixel_x] = True
    for junction in filtered_junctions:
        junction_x = int(junction.get("x", 0))
        junction_y = int(junction.get("y", 0))
        if 0 <= junction_y < len(filtered_debug_mask) and 0 <= junction_x < len(filtered_debug_mask[0]):
            filtered_debug_mask[junction_y][junction_x] = True
    corridor_graph = {
        "segments": edge_segments,
        "junctions": filtered_junctions,
        "attachments": edge_attachments,
    }
    _write_debug_mask(area_slug, "debug_skeleton_filtered.png", filtered_debug_mask, True)
    _write_debug_json(
        area_slug,
        "debug_corridor_graph_raw.json",
        {"segments": raw_corridor_graph["segments"], "junctions": raw_corridor_graph["junctions"]},
        True,
    )
    _write_debug_json(
        area_slug,
        "debug_corridor_graph_filtered.json",
        {
            "segments": edge_segments,
            "junctions": filtered_junctions,
            "attached_segments": attached_segments,
            "attached_rooms": edge_attachments,
        },
        True,
    )
    _write_debug_json(area_slug, "debug_corridor_graph.json", {"segments": edge_segments, "junctions": filtered_junctions, "attached_rooms": edge_attachments}, True)
    _write_debug_json(area_slug, "debug_room_attachments_raw.json", raw_attachments, True)
    _write_debug_json(area_slug, "debug_room_attachments_filtered.json", edge_attachments, True)
    _write_debug_json(area_slug, "debug_room_attachments.json", edge_attachments, True)
    grid_recovered_nodes = []
    inferred_grid_spacing = _infer_grid_spacing(nodes, config)
    segment_node_counts = [
        {"segment_id": segment.get("id"), "node_count": len(edge_attachments.get(segment.get("id"), []))}
        for segment in edge_segments
    ]
    exit_audit = corridors_to_edges(nodes, edge_segments, edge_attachments, filtered_junctions)
    pre_normalization_audit = audit_graph(nodes, exit_audit)
    normalized_exit_audit = normalize_edges(exit_audit)
    lane_tolerance = max(3, int(round(inferred_grid_spacing / 2))) if inferred_grid_spacing else 12
    lane_clusters = assign_lane_clusters(nodes, tolerance=lane_tolerance)
    graph_audit = audit_graph(nodes, normalized_exit_audit)
    long_edges = detect_long_edges(nodes, normalized_exit_audit, threshold=3)
    direction_mismatches = validate_direction_consistency(nodes, normalized_exit_audit)
    spatial_edges = [(edge["source"], edge["direction"], edge["target"], edge) for edge in normalized_exit_audit]
    isolated_node_audit = _build_isolated_node_audit(nodes, normalized_exit_audit)
    _write_debug_json(area_slug, "debug_graph_audit.json", {"before_normalization": pre_normalization_audit, "after_normalization": graph_audit}, True)
    _write_debug_json(area_slug, "debug_long_edges.json", long_edges, True)
    _write_debug_json(area_slug, "debug_direction_mismatches.json", direction_mismatches, True)
    _write_debug_json(area_slug, "debug_lane_clusters.json", lane_clusters, True)
    _write_debug_json(area_slug, "debug_exit_derivation.json", normalized_exit_audit, bool(config["debug_corridors"]))
    _write_debug_json(area_slug, "debug_isolated_nodes.json", isolated_node_audit, bool(config["debug_corridors"]))

    ocr_bundle = None
    ocr_lines = []
    if use_ocr and ocr_available():
        try:
            ocr_bundle = extract_ocr_bundle(map_path)
        except RuntimeError:
            ocr_bundle = None
        else:
            ocr_lines = list(ocr_bundle.get("lines") or [])

    ocr_attachment_audit = _attach_node_labels(nodes, ocr_lines, config)
    special_exit_candidates, special_attachment_audit = _build_special_exit_candidates(nodes, ocr_lines, corridor_graph, (line_mask > 0).tolist())
    ocr_attachment_audit.extend(special_attachment_audit)
    _write_debug_json(area_slug, "debug_ocr_attachments.json", ocr_attachment_audit, bool(config["debug_ocr"]))

    artifact_edges = _attach_edge_labels(spatial_edges, nodes, ocr_lines, config)
    return {
        "nodes": nodes,
        "edges": artifact_edges,
        "meta": {
            "area_id": area_id,
            "area_slug": area_slug,
            "area_name": str(area_id or "").replace("_", " ").replace("-", " ").title(),
            "ocr_used": bool(ocr_bundle),
            "node_count": len(nodes),
            "raw_cluster_count": marker_report["raw_cluster_count"],
            "weak_marker_candidate_count": marker_report["weak_candidate_count"],
            "weak_marker_promoted_count": marker_report["weak_promoted_count"],
            "forced_marker_promoted_count": marker_report.get("forced_promoted_count", 0),
            "missing_marker_count": marker_report.get("missing_count", 0),
            "marker_coverage": marker_report.get("coverage", 0.0),
            "under_detected": len(nodes) < 170,
            "grid_recovered_count": len(grid_recovered_nodes),
            "inferred_grid_spacing": inferred_grid_spacing,
            "weak_nodes": promoted_weak_nodes,
            "edge_count": len(artifact_edges),
            "edge_count_pre_normalization": len(exit_audit),
            "pipeline": "cv_v2",
            "corridor_segments": edge_segments,
            "corridor_segment_count": len(edge_segments),
            "corridor_segment_count_raw": len(raw_corridor_graph["segments"]),
            "corridor_segment_count_attached": len(attached_segments),
            "junction_count": len(filtered_junctions),
            "junction_count_raw": len(raw_corridor_graph["junctions"]),
            "corridor_attachment_count": sum(len(room_ids) for room_ids in edge_attachments.values()),
            "attached_room_count": len(attached_room_ids),
            "unattached_room_count": len(unattached_room_ids),
            "unattached_room_ids": unattached_room_ids,
            "segment_node_counts": segment_node_counts,
            "raw_room_attachments": raw_attachments,
            "filtered_room_attachments": edge_attachments,
            "graph_audit": graph_audit,
            "long_edge_count": len(long_edges),
            "direction_mismatch_count": len(direction_mismatches),
            "lane_cluster_tolerance": lane_tolerance,
            "special_exit_candidates": special_exit_candidates,
            "special_exit_candidate_count": len(special_exit_candidates),
            "ocr_label_candidates": ocr_lines,
            "ocr_attachment_audit": ocr_attachment_audit,
            "exit_derivation": exit_audit,
            "isolated_node_audit": isolated_node_audit,
            "isolated_node_count": len(isolated_node_audit),
            "unnamed_room_count": sum(1 for node in nodes if not node.get("final_label")),
            "source_image": str(map_path),
        },
    }