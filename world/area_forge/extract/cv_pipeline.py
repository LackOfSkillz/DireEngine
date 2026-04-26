from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math
import warnings

import cv2
import numpy as np
from scipy.ndimage import label as nd_label
from skimage.morphology import skeletonize

from world.area_forge.serializer import save_json


HSV_RANGES = {
    "red": [((0, 120, 80), (10, 255, 255)), ((170, 120, 80), (180, 255, 255))],
    "green": [((40, 120, 80), (80, 255, 255))],
    "yellow": [((20, 120, 120), (35, 255, 255))],
    "cyan": [((85, 120, 100), (100, 255, 255))],
    "blue": [((105, 120, 80), (130, 255, 255))],
}


OPPOSITE_DIRECTIONS = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "northwest": "southeast",
    "southeast": "northwest",
    "southwest": "northeast",
}


@dataclass(slots=True)
class RoomDetectConfig:
    gray_saturation_max: int = 35
    gray_value_min: int = 100
    gray_value_max: int = 225
    min_area: int = 22
    max_area: int = 700
    aspect_min: float = 0.5
    aspect_max: float = 1.7
    color_close_kernel: int = 3
    gray_close_kernels: tuple[int, ...] = (2, 3)


@dataclass(slots=True)
class LineDetectConfig:
    dark_value_max: int = 180
    max_saturation: int = 50
    close_kernel: int = 2
    min_corridor_length: int = 8
    junction_dilate: int = 1
    max_junction_count: int = 900
    junction_count_reference_p95: int = 300
    junction_count_reference_multiplier: float = 3.0
    debug_output_dir: str | Path | None = None


def load_bgr(path: str):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
    return img


def to_hsv(img_bgr):
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)


def build_color_mask(hsv, ranges):
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for lo, hi in ranges:
        mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
    return mask


def _room_cfg(cfg=None) -> RoomDetectConfig:
    if cfg is None:
        return RoomDetectConfig()
    if isinstance(cfg, RoomDetectConfig):
        return cfg
    if isinstance(cfg, dict):
        return RoomDetectConfig(**cfg)
    raise TypeError(f"Unsupported room detection config: {type(cfg)!r}")


def build_gray_mask(hsv, cfg=None):
    cfg = _room_cfg(cfg)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    return ((s <= int(cfg.gray_saturation_max)) & (v >= int(cfg.gray_value_min)) & (v <= int(cfg.gray_value_max))).astype(np.uint8) * 255


def clean_mask(mask, kernel_size=3):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


def get_components(mask):
    return cv2.connectedComponentsWithStats(mask, connectivity=8)


def components_to_rooms(stats, centroids, cfg=None):
    cfg = _room_cfg(cfg)
    rooms = []
    for i in range(1, len(stats)):
        x, y, w, h, area = stats[i]
        if area < int(cfg.min_area) or area > int(cfg.max_area):
            continue
        aspect = w / max(h, 1)
        if aspect < float(cfg.aspect_min) or aspect > float(cfg.aspect_max):
            continue
        cx, cy = centroids[i]
        rooms.append({
            "x": int(cx),
            "y": int(cy),
            "w": int(w),
            "h": int(h),
            "area": int(area),
        })
    return rooms


def detect_rooms(img, cfg=None):
    cfg = _room_cfg(cfg)
    hsv = to_hsv(img)
    rooms = []

    for name, ranges in HSV_RANGES.items():
        mask = clean_mask(build_color_mask(hsv, ranges), kernel_size=int(cfg.color_close_kernel))
        _, _, stats, centroids = get_components(mask)
        for room in components_to_rooms(stats, centroids, cfg=cfg):
            room["color"] = name
            rooms.append(room)

    gray_candidates = []
    for kernel_size in cfg.gray_close_kernels:
        mask = clean_mask(build_gray_mask(hsv, cfg=cfg), kernel_size=kernel_size)
        _, _, stats, centroids = get_components(mask)
        gray_candidates.append((len(components_to_rooms(stats, centroids, cfg=cfg)), stats, centroids))

    _, stats, centroids = max(gray_candidates, key=lambda item: item[0])
    for room in components_to_rooms(stats, centroids, cfg=cfg):
        room["color"] = "gray"
        rooms.append(room)

    rooms.sort(key=lambda room: (room["y"], room["x"]))
    for i, room in enumerate(rooms):
        room["id"] = f"room_{i:04d}"
    return rooms


def draw_rooms(img, rooms):
    out = img.copy()
    for room in rooms:
        x = int(room["x"] - room["w"] / 2)
        y = int(room["y"] - room["h"] / 2)
        color = (255, 255, 0) if room.get("color") == "gray" else (0, 0, 255)
        cv2.rectangle(out, (x, y), (x + room["w"], y + room["h"]), color, 1)
    return out


def write_room_overlay(img, rooms, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), draw_rooms(img, rooms))
    return path


def build_preserve_mask(shape, rooms):
    mask = np.zeros(shape[:2], dtype=np.uint8)
    height, width = shape[:2]
    for room in rooms:
        x = max(0, int(room["x"] - room["w"] / 2))
        y = max(0, int(room["y"] - room["h"] / 2))
        end_x = min(width, x + int(room["w"]))
        end_y = min(height, y + int(room["h"]))
        mask[y:end_y, x:end_x] = 1
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    return mask


def _line_cfg(cfg=None) -> LineDetectConfig:
    if cfg is None:
        return LineDetectConfig()
    if isinstance(cfg, LineDetectConfig):
        return cfg
    if isinstance(cfg, dict):
        return LineDetectConfig(**cfg)
    raise TypeError(f"Unsupported line detection config: {type(cfg)!r}")


def _debug_dir(cfg: LineDetectConfig | None) -> Path | None:
    if cfg is None or cfg.debug_output_dir is None:
        return None
    return Path(cfg.debug_output_dir)


def _write_debug_mask(path: Path | None, mask) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    output_mask = (np.asarray(mask, dtype=np.uint8) > 0).astype(np.uint8) * 255
    cv2.imwrite(str(path), output_mask)


def _write_debug_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    save_json(path, payload)


def _point_record(x: int, y: int) -> dict[str, int]:
    return {"x": int(x), "y": int(y)}


def _junction_overflow_threshold(cfg: LineDetectConfig) -> int:
    configured_cap = max(0, int(cfg.max_junction_count))
    reference_cap = max(0, int(round(float(cfg.junction_count_reference_p95) * float(cfg.junction_count_reference_multiplier))))
    return max(configured_cap, reference_cap)


def _room_bbox(room):
    bbox = room.get("bbox") if isinstance(room, dict) else None
    if isinstance(bbox, dict):
        return (
            int(bbox.get("x", 0)),
            int(bbox.get("y", 0)),
            int(bbox.get("w", room.get("w", 0))),
            int(bbox.get("h", room.get("h", 0))),
        )
    width = int(room.get("w", 0))
    height = int(room.get("h", 0))
    center_x = int(room.get("x", 0))
    center_y = int(room.get("y", 0))
    return (center_x - width // 2, center_y - height // 2, width, height)


def _point_to_rect_distance(point_x: int, point_y: int, bbox) -> float:
    rect_x, rect_y, rect_w, rect_h = bbox
    rect_right = rect_x + max(0, rect_w)
    rect_bottom = rect_y + max(0, rect_h)
    dx = max(rect_x - point_x, 0, point_x - rect_right)
    dy = max(rect_y - point_y, 0, point_y - rect_bottom)
    return math.hypot(dx, dy)


def _segment_sort_key(room, corridor) -> tuple[float, str]:
    endpoints = list(corridor.get("endpoints") or [])
    if len(endpoints) < 2:
        return (0.0, str(room.get("id") or ""))
    start = endpoints[0]
    end = endpoints[-1]
    dx = float(end.get("x", 0) - start.get("x", 0))
    dy = float(end.get("y", 0) - start.get("y", 0))
    norm = dx * dx + dy * dy
    if norm <= 0.0:
        return (0.0, str(room.get("id") or ""))
    projection = ((float(room.get("x", 0)) - float(start.get("x", 0))) * dx + (float(room.get("y", 0)) - float(start.get("y", 0))) * dy) / norm
    return (projection, str(room.get("id") or ""))


def _resolve_direction(source, target) -> str | None:
    dx = int(target.get("x", 0)) - int(source.get("x", 0))
    dy = int(target.get("y", 0)) - int(source.get("y", 0))
    if dx == 0 and dy == 0:
        return None
    angle = (math.degrees(math.atan2(-dy, dx)) + 360.0) % 360.0
    if angle >= 337.5 or angle < 22.5:
        return "east"
    if angle < 67.5:
        return "northeast"
    if angle < 112.5:
        return "north"
    if angle < 157.5:
        return "northwest"
    if angle < 202.5:
        return "west"
    if angle < 247.5:
        return "southwest"
    if angle < 292.5:
        return "south"
    return "southeast"


def _endpoint_near_junction(endpoint, junction, radius: int = 12) -> bool:
    endpoint_x = int(endpoint.get("x", 0))
    endpoint_y = int(endpoint.get("y", 0))
    junction_x = int(junction.get("x", 0))
    junction_y = int(junction.get("y", 0))
    return abs(endpoint_x - junction_x) <= radius and abs(endpoint_y - junction_y) <= radius


def _build_segment_junction_maps(corridors, junctions, radius: int = 12):
    corridor_lookup = {str(corridor.get("id") or ""): corridor for corridor in list(corridors or []) if corridor.get("id")}
    junction_segments = defaultdict(set)
    segment_junctions = defaultdict(set)
    for junction in list(junctions or []):
        junction_id = str(junction.get("id") or "")
        if not junction_id:
            continue
        for corridor_id, corridor in corridor_lookup.items():
            for endpoint in list(corridor.get("endpoints") or []):
                if _endpoint_near_junction(endpoint, junction, radius=radius):
                    junction_segments[junction_id].add(corridor_id)
                    segment_junctions[corridor_id].add(junction_id)
                    break
    return junction_segments, segment_junctions


def _reachable_bridge_targets(start_corridor_id: str, lone_room_id: str, attachments, segment_junctions, junction_segments, room_lookup):
    queue = deque([start_corridor_id])
    seen_corridors = {start_corridor_id}
    target_room_ids = set()
    while queue:
        current_corridor_id = queue.popleft()
        current_room_ids = [room_id for room_id in attachments.get(current_corridor_id, []) if room_id in room_lookup]
        other_room_ids = [room_id for room_id in current_room_ids if room_id != lone_room_id]
        if other_room_ids:
            target_room_ids.update(other_room_ids)
            continue
        for junction_id in segment_junctions.get(current_corridor_id, set()):
            for next_corridor_id in junction_segments.get(junction_id, set()):
                if next_corridor_id in seen_corridors:
                    continue
                seen_corridors.add(next_corridor_id)
                queue.append(next_corridor_id)
    return sorted(target_room_ids)


def _farthest_pair(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(points) == 1:
        return points[0], points[0]
    seed = points[0]
    distances = np.sum((points - seed) ** 2, axis=1)
    first = points[int(np.argmax(distances))]
    distances = np.sum((points - first) ** 2, axis=1)
    second = points[int(np.argmax(distances))]
    return first, second


def build_line_mask(img_bgr, node_preserve_mask, cfg=None):
    cfg = _line_cfg(cfg)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    preserve_mask = np.asarray(node_preserve_mask, dtype=bool)
    candidate_mask = ((gray <= int(cfg.dark_value_max)) & (hsv[:, :, 1] <= int(cfg.max_saturation)) & ~preserve_mask).astype(np.uint8) * 255
    kernel_size = max(1, int(cfg.close_kernel))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    cleaned_mask = cv2.morphologyEx(candidate_mask, cv2.MORPH_CLOSE, kernel)
    _write_debug_mask((_debug_dir(cfg) / "debug_line_mask.png") if _debug_dir(cfg) else None, cleaned_mask)
    return cleaned_mask


def extract_corridor_graph(line_mask, cfg=None):
    cfg = _line_cfg(cfg)
    skeleton = skeletonize(np.asarray(line_mask, dtype=np.uint8) > 0).astype(np.uint8)
    debug_dir = _debug_dir(cfg)
    _write_debug_mask((debug_dir / "debug_skeleton.png") if debug_dir else None, skeleton)

    kernel = np.ones((3, 3), dtype=np.uint8)
    kernel[1, 1] = 0
    neighbor_counts = cv2.filter2D(skeleton, cv2.CV_16S, kernel, borderType=cv2.BORDER_CONSTANT)

    junction_mask = ((skeleton > 0) & (neighbor_counts >= 3)).astype(np.uint8)
    dilate_radius = max(0, int(cfg.junction_dilate))
    if dilate_radius:
        junction_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_radius * 2 + 1, dilate_radius * 2 + 1))
        dilated_junction_mask = cv2.dilate(junction_mask, junction_kernel)
    else:
        dilated_junction_mask = junction_mask.copy()

    labeled_junctions, junction_count = nd_label(dilated_junction_mask > 0)
    junction_threshold = _junction_overflow_threshold(cfg)
    if int(junction_count) > junction_threshold:
        overflow = {
            "raw_junction_count": int(junction_count),
            "junction_threshold": int(junction_threshold),
        }
        warnings.warn(
            f"Aborting corridor extraction: junction count {junction_count} exceeded threshold {junction_threshold}.",
            RuntimeWarning,
            stacklevel=2,
        )
        graph = {
            "segments": [],
            "junctions": [],
            "skeleton": skeleton,
            "overflow": overflow,
        }
        _write_debug_json(
            (debug_dir / "debug_corridor_graph.json") if debug_dir else None,
            {"segments": [], "junctions": [], "overflow": overflow},
        )
        return graph

    junctions = []
    for index in range(1, int(junction_count) + 1):
        points = np.argwhere(labeled_junctions == index)
        if len(points) == 0:
            continue
        center_y, center_x = np.mean(points, axis=0)
        junctions.append({
            "id": f"J{len(junctions) + 1:04d}",
            "x": int(round(center_x)),
            "y": int(round(center_y)),
        })

    corridor_only = ((skeleton > 0) & ~(dilated_junction_mask > 0)).astype(np.uint8)
    corridor_neighbor_counts = cv2.filter2D(corridor_only, cv2.CV_16S, kernel, borderType=cv2.BORDER_CONSTANT)
    labeled_corridors, corridor_count = nd_label(corridor_only > 0)

    corridors = []
    for index in range(1, int(corridor_count) + 1):
        points = np.argwhere(labeled_corridors == index)
        pixel_count = len(points)
        if pixel_count < int(cfg.min_corridor_length):
            continue
        endpoint_candidates = points[corridor_neighbor_counts[points[:, 0], points[:, 1]] <= 1]
        if len(endpoint_candidates) >= 2:
            first, second = _farthest_pair(endpoint_candidates)
        else:
            first, second = _farthest_pair(points)
        start_y, start_x = (int(first[0]), int(first[1]))
        end_y, end_x = (int(second[0]), int(second[1]))
        corridor = {
            "id": f"C{len(corridors) + 1:04d}",
            "pixels": [_point_record(int(x), int(y)) for y, x in points],
            "endpoints": [_point_record(start_x, start_y), _point_record(end_x, end_y)],
            "length": int(pixel_count),
            "x1": int(start_x),
            "y1": int(start_y),
            "x2": int(end_x),
            "y2": int(end_y),
            "component_id": int(index),
        }
        corridors.append(corridor)

    graph = {
        "segments": corridors,
        "junctions": junctions,
        "skeleton": skeleton,
    }
    _write_debug_json(
        (debug_dir / "debug_corridor_graph.json") if debug_dir else None,
        {"segments": corridors, "junctions": junctions},
    )
    return graph


def attach_rooms_to_corridors(rooms, corridors, max_distance=20, cfg=None):
    cfg = _line_cfg(cfg)
    attachments = {}
    for corridor in list(corridors or []):
        corridor_id = str(corridor.get("id") or "")
        corridor_points = list(corridor.get("pixels") or [])
        if not corridor_points:
            corridor_points = list(corridor.get("endpoints") or [])
        attached_room_ids = set()
        for room in list(rooms or []):
            room_id = str(room.get("id") or "")
            if not room_id:
                continue
            bbox = _room_bbox(room)
            for point in corridor_points:
                distance = _point_to_rect_distance(int(point.get("x", 0)), int(point.get("y", 0)), bbox)
                if distance <= float(max_distance):
                    attached_room_ids.add(room_id)
                    break
        attachments[corridor_id] = sorted(attached_room_ids)
    _write_debug_json(
        (_debug_dir(cfg) / "debug_room_attachments.json") if _debug_dir(cfg) else None,
        attachments,
    )
    return attachments


def corridors_to_edges(rooms, corridors, attachments, junctions=None):
    room_lookup = {str(room.get("id") or ""): room for room in list(rooms or []) if room.get("id")}
    corridor_lookup = {str(corridor.get("id") or ""): corridor for corridor in list(corridors or []) if corridor.get("id")}
    edges = {}
    junction_segments, segment_junctions = _build_segment_junction_maps(corridors, junctions or [])

    def register_edge(source_id: str, target_id: str, derivation_method: str = "skeleton"):
        source = room_lookup.get(source_id)
        target = room_lookup.get(target_id)
        if not source or not target or source_id == target_id:
            return
        direction = _resolve_direction(source, target)
        if not direction:
            return
        key = (source_id, direction, target_id)
        edges[key] = {
            "source": source_id,
            "target": target_id,
            "direction": direction,
            "derivation_method": derivation_method,
            "confidence": 0.85,
        }
        reverse_direction = OPPOSITE_DIRECTIONS.get(direction)
        if reverse_direction:
            edges[(target_id, reverse_direction, source_id)] = {
                "source": target_id,
                "target": source_id,
                "direction": reverse_direction,
                "derivation_method": derivation_method,
                "confidence": 0.85,
            }

    for corridor_id in sorted(attachments):
        corridor = corridor_lookup.get(corridor_id)
        if not corridor:
            continue
        room_ids = [room_id for room_id in attachments.get(corridor_id, []) if room_id in room_lookup]
        ordered_room_ids = [room_id for room_id in sorted(room_ids, key=lambda room_id: _segment_sort_key(room_lookup[room_id], corridor))]
        for left_id, right_id in zip(ordered_room_ids, ordered_room_ids[1:]):
            register_edge(left_id, right_id)
        if len(ordered_room_ids) == 1 and corridor.get("dead_end"):
            lone_room_id = ordered_room_ids[0]
            for target_room_id in _reachable_bridge_targets(
                corridor_id,
                lone_room_id,
                attachments,
                segment_junctions,
                junction_segments,
                room_lookup,
            ):
                register_edge(lone_room_id, target_room_id, derivation_method="junction_bridge")

    return [edges[key] for key in sorted(edges, key=lambda item: (item[0], item[1], item[2]))]