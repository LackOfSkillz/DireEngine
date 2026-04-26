from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from world.area_forge.extract.cv_pipeline import _point_to_rect_distance, _room_bbox
from world.area_forge.extract.yaml_graph import extract_yaml_graph_area_spec_v2


DEFAULT_BASE_REPORT = ROOT / "build" / "area_forge_validation_base_maps.json"
DEFAULT_LETTER_REPORT = ROOT / "build" / "area_forge_validation_letter_maps.json"
DEFAULT_OUTPUT = ROOT / "build" / "area_forge_tail_audit.json"
NO_SKELETON_REACH_THRESHOLD = 28.0


def _load_results(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("results") or [])


def _component_sizes(nodes: list[dict[str, object]], edges: list[object]) -> dict[str, int]:
    adjacency = {str(node.get("id")): set() for node in nodes if node.get("id")}
    for raw_edge in edges:
        if not isinstance(raw_edge, (list, tuple)) or len(raw_edge) < 3:
            continue
        source = str(raw_edge[0] or "")
        target = str(raw_edge[2] or "")
        if source not in adjacency or target not in adjacency:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
    sizes = {}
    seen = set()
    for node_id in sorted(adjacency):
        if node_id in seen:
            continue
        queue = deque([node_id])
        seen.add(node_id)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        component_size = len(component)
        for component_node_id in component:
            sizes[component_node_id] = component_size
    return sizes


def _invert_attachments(attachment_map: dict[str, list[str]]) -> dict[str, list[str]]:
    room_segments: dict[str, list[str]] = defaultdict(list)
    for segment_id, room_ids in attachment_map.items():
        for room_id in list(room_ids or []):
            room_segments[str(room_id)].append(str(segment_id))
    return {room_id: sorted(segment_ids) for room_id, segment_ids in room_segments.items()}


def _nearest_skeleton_distance(room: dict[str, object], skeleton_path: Path) -> float | None:
    skeleton = cv2.imread(str(skeleton_path), cv2.IMREAD_GRAYSCALE)
    if skeleton is None:
        return None
    points = cv2.findNonZero((skeleton > 0).astype("uint8"))
    if points is None:
        return None
    bbox = _room_bbox(room)
    distances = [_point_to_rect_distance(int(point[0][0]), int(point[0][1]), bbox) for point in points]
    if not distances:
        return None
    return round(min(distances), 2)


def _nearest_corridor_distance(room: dict[str, object], segments: list[dict[str, object]]) -> tuple[float | None, str | None]:
    bbox = _room_bbox(room)
    best_distance = None
    best_segment_id = None
    for segment in segments:
        segment_id = str(segment.get("id") or "")
        for point in list(segment.get("pixels") or []):
            distance = _point_to_rect_distance(int(point.get("x", 0)), int(point.get("y", 0)), bbox)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_segment_id = segment_id
    if best_distance is None:
        return None, None
    return round(best_distance, 2), best_segment_id


def _bucket_for_room(filtered_segments: list[str], nearest_skeleton_px: float | None) -> str:
    if filtered_segments:
        return "attached_but_orphaned"
    if nearest_skeleton_px is None or nearest_skeleton_px > NO_SKELETON_REACH_THRESHOLD:
        return "no_skeleton_reaches"
    return "preserve_mask_occluded"


def _audit_map(result: dict[str, object]) -> dict[str, object]:
    map_path = Path(str(result["map_path"]))
    area_id = str(result.get("area_id") or f"audit_{map_path.stem}")
    area_spec = extract_yaml_graph_area_spec_v2(
        map_path=map_path,
        area_id=area_id,
        use_ocr=True,
        use_ai_adjudication=False,
        profile="yaml_graph",
        style_settings={},
    )
    artifact_dir = ROOT / "build" / area_id
    nodes = [node for node in list(area_spec.get("nodes") or []) if isinstance(node, dict)]
    node_lookup = {str(node.get("id")): node for node in nodes if node.get("id")}
    meta = dict(area_spec.get("meta") or {})
    raw_attachment_map = {str(key): list(value or []) for key, value in dict(meta.get("raw_room_attachments") or {}).items()}
    filtered_attachment_map = {str(key): list(value or []) for key, value in dict(meta.get("filtered_room_attachments") or {}).items()}
    raw_segments_by_room = _invert_attachments(raw_attachment_map)
    filtered_segments_by_room = _invert_attachments(filtered_attachment_map)
    filtered_graph_payload = json.loads((artifact_dir / "debug_corridor_graph_filtered.json").read_text(encoding="utf-8"))
    filtered_segments = list(filtered_graph_payload.get("segments") or [])
    component_sizes = _component_sizes(nodes, list(area_spec.get("edges") or []))
    skeleton_path = artifact_dir / "debug_skeleton.png"

    rooms = []
    bucket_counts: Counter[str] = Counter()
    isolated_node_audit = list(meta.get("isolated_node_audit") or [])
    for isolated in isolated_node_audit:
        room_id = str(isolated.get("node_id") or "")
        room = node_lookup.get(room_id)
        if not room:
            continue
        filtered_segments_for_room = list(filtered_segments_by_room.get(room_id, []))
        raw_segments_for_room = list(raw_segments_by_room.get(room_id, []))
        nearest_skeleton_px = _nearest_skeleton_distance(room, skeleton_path)
        nearest_corridor_px, nearest_segment_id = _nearest_corridor_distance(room, filtered_segments)
        bucket = _bucket_for_room(filtered_segments_for_room, nearest_skeleton_px)
        bucket_counts[bucket] += 1
        rooms.append(
            {
                "room_id": room_id,
                "x": int(room.get("x", 0)),
                "y": int(room.get("y", 0)),
                "raw_attached_segments": raw_segments_for_room,
                "filtered_attached_segments": filtered_segments_for_room,
                "nearest_skeleton_px": nearest_skeleton_px,
                "nearest_corridor_pixel_px": nearest_corridor_px,
                "nearest_corridor_segment_id": nearest_segment_id,
                "component_size": component_sizes.get(room_id, 1),
                "bucket": bucket,
            }
        )

    dominant_buckets = [bucket for bucket, count in bucket_counts.items() if count == max(bucket_counts.values(), default=0)]
    notes = []
    if not nodes:
        notes.append("zero_room_detection")
    if not isolated_node_audit and nodes:
        notes.append("no_isolated_nodes")
    return {
        "map_name": map_path.name,
        "map_path": str(map_path),
        "connected_pct": result.get("connected_pct"),
        "rooms_detected": len(nodes),
        "isolated_room_count": len(isolated_node_audit),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "dominant_buckets": sorted(dominant_buckets),
        "notes": notes,
        "rooms": rooms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the low-connectivity tail across AreaForge validation reports.")
    parser.add_argument("--base-report", default=str(DEFAULT_BASE_REPORT), help="Path to the base-map validation report JSON.")
    parser.add_argument("--letter-report", default=str(DEFAULT_LETTER_REPORT), help="Path to the letter-map validation report JSON.")
    parser.add_argument("--threshold", type=float, default=70.0, help="Connectivity threshold for selecting tail maps.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for a smaller audit subset.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write the tail audit JSON.")
    args = parser.parse_args()

    combined_results = []
    for report_path in (Path(args.base_report), Path(args.letter_report)):
        combined_results.extend(_load_results(report_path))
    tail_results = [result for result in combined_results if float(result.get("connected_pct", 0.0)) < float(args.threshold)]
    tail_results.sort(key=lambda item: (float(item.get("connected_pct", 0.0)), str(item.get("map_name") or item.get("map_path") or "")))
    if args.limit > 0:
        tail_results = tail_results[: args.limit]

    per_map = []
    dominant_counter: Counter[str] = Counter()
    dominant_combo_counter: Counter[str] = Counter()
    for result in tail_results:
        audited = _audit_map(result)
        per_map.append(audited)
        if audited["dominant_buckets"]:
            for bucket in audited["dominant_buckets"]:
                dominant_counter[bucket] += 1
            dominant_combo_counter["+".join(audited["dominant_buckets"])] += 1
        print(
            f"{audited['map_name']}: connected={audited['connected_pct']}% isolated={audited['isolated_room_count']} "
            f"dominant={','.join(audited['dominant_buckets']) or 'none'}"
        )

    output = {
        "threshold": float(args.threshold),
        "map_count": len(per_map),
        "dominant_bucket_counts": dict(sorted(dominant_counter.items())),
        "dominant_bucket_combinations": dict(sorted(dominant_combo_counter.items())),
        "maps": per_map,
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({
        "threshold": output["threshold"],
        "map_count": output["map_count"],
        "dominant_bucket_counts": output["dominant_bucket_counts"],
        "dominant_bucket_combinations": output["dominant_bucket_combinations"],
    }, indent=2))
    print(f"Wrote report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())