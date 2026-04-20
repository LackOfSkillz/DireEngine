from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import yaml


CARDINAL_DIRECTIONS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}

DIAGONAL_DIRECTIONS = {
    "northeast": (1, -1),
    "northwest": (-1, -1),
    "southeast": (1, 1),
    "southwest": (-1, 1),
}

OPPOSITE_DIRECTION = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
}


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump_yaml(path: Path, payload: dict) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def _read_room_coords(zone: dict) -> Dict[str, Tuple[int, int]]:
    coords: Dict[str, Tuple[int, int]] = {}
    for room in zone.get("rooms", []):
        room_id = str(room.get("id") or "")
        map_data = room.get("map") or {}
        coords[room_id] = (int(map_data.get("x", 0)), int(map_data.get("y", 0)))
    return coords


def _resolve_snapped_layout(
    coords: Dict[str, Tuple[int, int]],
    grid_step: int,
) -> Tuple[Dict[str, Tuple[int, int]], Dict[str, Tuple[int, int]], Dict[Tuple[int, int], List[str]], dict]:
    snapped_anchor_coords = {
        room_id: (round(x / grid_step) * grid_step, round(y / grid_step) * grid_step)
        for room_id, (x, y) in coords.items()
    }
    anchor_groups: Dict[Tuple[int, int], List[str]] = {}
    for room_id, anchor in snapped_anchor_coords.items():
        anchor_groups.setdefault(anchor, []).append(room_id)

    display_coords: Dict[str, Tuple[int, int]] = {}
    max_stack = 0
    collision_count = 0
    for (anchor_x, anchor_y), room_ids in anchor_groups.items():
        ordered_room_ids = sorted(room_ids)
        if len(ordered_room_ids) > 1:
            collision_count += 1
        max_stack = max(max_stack, len(ordered_room_ids))
        if len(ordered_room_ids) == 1:
            display_coords[ordered_room_ids[0]] = (anchor_x, anchor_y)
            continue
        offsets = [
            (0, 0),
            (-12, 0),
            (12, 0),
            (0, -12),
            (0, 12),
            (-12, -12),
            (12, -12),
            (-12, 12),
            (12, 12),
        ]
        for index, room_id in enumerate(ordered_room_ids):
            dx, dy = offsets[index] if index < len(offsets) else (0, 16 * (index - len(offsets) + 1))
            display_coords[room_id] = (anchor_x + dx, anchor_y + dy)

    report = {
        "snapped_unique_coords": len(anchor_groups),
        "snapped_collision_count": collision_count,
        "snapped_max_stack": max_stack,
    }
    return snapped_anchor_coords, display_coords, anchor_groups, report


def _snap_grid(value: float, grid_step: int) -> int:
    return int(round(value / grid_step) * grid_step)


def _median_int(values: Iterable[int]) -> int:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        return 0
    return ordered[len(ordered) // 2]


def _build_anchor_exit_map(
    raw_zone: dict,
    snapped_anchor_coords: Dict[str, Tuple[int, int]],
    anchor_primaries: Dict[Tuple[int, int], str],
) -> Dict[str, Dict[str, str]]:
    room_to_primary = {
        room_id: anchor_primaries[anchor]
        for room_id, anchor in snapped_anchor_coords.items()
    }
    directional_votes: Dict[str, Dict[str, Counter]] = {}
    for raw_room in raw_zone.get("rooms", []):
        source_room_id = str(raw_room.get("id") or "")
        source_primary_id = room_to_primary.get(source_room_id)
        if not source_primary_id:
            continue
        for direction, exit_spec in (raw_room.get("exits") or {}).items():
            normalized_direction = str(direction or "").strip().lower()
            if normalized_direction not in CARDINAL_DIRECTIONS and normalized_direction not in DIAGONAL_DIRECTIONS:
                continue
            target_room_id = str((exit_spec or {}).get("target") or "")
            target_primary_id = room_to_primary.get(target_room_id)
            if not target_primary_id or target_primary_id == source_primary_id:
                continue
            directional_votes.setdefault(source_primary_id, {}).setdefault(normalized_direction, Counter())[target_primary_id] += 1

    anchor_exit_map: Dict[str, Dict[str, str]] = {}
    for source_primary_id, direction_votes in directional_votes.items():
        anchor_exit_map[source_primary_id] = {
            direction: votes.most_common(1)[0][0]
            for direction, votes in direction_votes.items()
            if votes
        }
    return anchor_exit_map


def _build_anchor_adjacency(anchor_exit_map: Dict[str, Dict[str, str]]) -> Dict[str, Set[str]]:
    adjacency: Dict[str, Set[str]] = {}
    for source_room_id, exits in anchor_exit_map.items():
        adjacency.setdefault(source_room_id, set())
        for target_room_id in exits.values():
            adjacency.setdefault(target_room_id, set()).add(source_room_id)
            adjacency[source_room_id].add(target_room_id)
    return adjacency


def _find_connected_components(node_ids: Iterable[str], adjacency: Dict[str, Set[str]]) -> List[List[str]]:
    remaining = set(node_ids)
    components: List[List[str]] = []
    while remaining:
        start = remaining.pop()
        component = [start]
        stack = [start]
        while stack:
            current = stack.pop()
            for neighbor in adjacency.get(current, set()):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                component.append(neighbor)
                stack.append(neighbor)
        components.append(sorted(component))
    return components


def _find_directional_runs(
    primary_coords: Dict[str, Tuple[int, int]],
    anchor_exit_map: Dict[str, Dict[str, str]],
    directions: Set[str],
) -> List[List[str]]:
    adjacency: Dict[str, Set[str]] = {room_id: set() for room_id in primary_coords}
    for room_id, exits in anchor_exit_map.items():
        for direction, target_id in exits.items():
            if direction not in directions or target_id not in primary_coords:
                continue
            adjacency[room_id].add(target_id)
            adjacency[target_id].add(room_id)
    return [component for component in _find_connected_components(primary_coords.keys(), adjacency) if len(component) >= 3]


def _normalize_run_axis(
    primary_coords: Dict[str, Tuple[int, int]],
    run_room_ids: List[str],
    axis: str,
    grid_step: int,
) -> None:
    if axis == "horizontal":
        ordered_room_ids = sorted(run_room_ids, key=lambda room_id: (primary_coords[room_id][0], room_id))
        shared_y = _snap_grid(_median_int(primary_coords[room_id][1] for room_id in ordered_room_ids), grid_step)
        center_x = sum(primary_coords[room_id][0] for room_id in ordered_room_ids) / len(ordered_room_ids)
        start_x = _snap_grid(center_x - ((len(ordered_room_ids) - 1) * grid_step) / 2, grid_step)
        for index, room_id in enumerate(ordered_room_ids):
            primary_coords[room_id] = (start_x + index * grid_step, shared_y)
        return

    ordered_room_ids = sorted(run_room_ids, key=lambda room_id: (primary_coords[room_id][1], room_id))
    shared_x = _snap_grid(_median_int(primary_coords[room_id][0] for room_id in ordered_room_ids), grid_step)
    center_y = sum(primary_coords[room_id][1] for room_id in ordered_room_ids) / len(ordered_room_ids)
    start_y = _snap_grid(center_y - ((len(ordered_room_ids) - 1) * grid_step) / 2, grid_step)
    for index, room_id in enumerate(ordered_room_ids):
        primary_coords[room_id] = (shared_x, start_y + index * grid_step)


def _component_bbox(primary_coords: Dict[str, Tuple[int, int]], room_ids: Iterable[str]) -> Tuple[int, int, int, int]:
    xs = [primary_coords[room_id][0] for room_id in room_ids]
    ys = [primary_coords[room_id][1] for room_id in room_ids]
    return min(xs), min(ys), max(xs), max(ys)


def _shift_component(primary_coords: Dict[str, Tuple[int, int]], room_ids: Iterable[str], delta_x: int, delta_y: int) -> None:
    for room_id in room_ids:
        x, y = primary_coords[room_id]
        primary_coords[room_id] = (x + delta_x, y + delta_y)


def _space_groups(
    primary_coords: Dict[str, Tuple[int, int]],
    groups: List[List[str]],
    min_group_gap: int,
    grid_step: int,
) -> Tuple[int, int]:
    if len(groups) <= 1:
        return len(groups), 0

    shifts_applied = 0
    for _ in range(12):
        moved = False
        for left_index, left_component in enumerate(groups):
            left_min_x, left_min_y, left_max_x, left_max_y = _component_bbox(primary_coords, left_component)
            left_center_x = (left_min_x + left_max_x) / 2
            left_center_y = (left_min_y + left_max_y) / 2
            for right_component in groups[left_index + 1 :]:
                right_min_x, right_min_y, right_max_x, right_max_y = _component_bbox(primary_coords, right_component)
                gap_x = max(right_min_x - left_max_x, left_min_x - right_max_x, 0)
                gap_y = max(right_min_y - left_max_y, left_min_y - right_max_y, 0)
                if gap_x >= min_group_gap or gap_y >= min_group_gap:
                    continue
                right_center_x = (right_min_x + right_max_x) / 2
                right_center_y = (right_min_y + right_max_y) / 2
                need_x = max(min_group_gap - gap_x, grid_step)
                need_y = max(min_group_gap - gap_y, grid_step)
                if abs(right_center_x - left_center_x) >= abs(right_center_y - left_center_y):
                    direction_x = 1 if right_center_x >= left_center_x else -1
                    _shift_component(primary_coords, right_component, direction_x * need_x, 0)
                else:
                    direction_y = 1 if right_center_y >= left_center_y else -1
                    _shift_component(primary_coords, right_component, 0, direction_y * need_y)
                shifts_applied += 1
                moved = True
        if not moved:
            break
    return len(groups), shifts_applied


def _build_district_groups(primary_coords: Dict[str, Tuple[int, int]], grid_step: int) -> List[List[str]]:
    district_span = grid_step * 8
    district_bins: Dict[Tuple[int, int], List[str]] = {}
    for room_id, (x, y) in primary_coords.items():
        district_key = (round(x / district_span), round(y / district_span))
        district_bins.setdefault(district_key, []).append(room_id)
    return [sorted(room_ids) for room_ids in district_bins.values() if room_ids]


def _beautify_anchor_layout(
    raw_zone: dict,
    snapped_anchor_coords: Dict[str, Tuple[int, int]],
    anchor_groups: Dict[Tuple[int, int], List[str]],
    anchor_primaries: Dict[Tuple[int, int], str],
    grid_step: int,
) -> Tuple[Dict[Tuple[int, int], Tuple[int, int]], dict]:
    primary_coords = {
        primary_room_id: anchor
        for anchor, primary_room_id in anchor_primaries.items()
    }
    anchor_exit_map = _build_anchor_exit_map(raw_zone, snapped_anchor_coords, anchor_primaries)

    horizontal_runs = _find_directional_runs(primary_coords, anchor_exit_map, {"east", "west"})
    vertical_runs = _find_directional_runs(primary_coords, anchor_exit_map, {"north", "south"})

    for run_room_ids in horizontal_runs:
        _normalize_run_axis(primary_coords, run_room_ids, axis="horizontal", grid_step=grid_step)
    for run_room_ids in vertical_runs:
        _normalize_run_axis(primary_coords, run_room_ids, axis="vertical", grid_step=grid_step)

    district_groups = _build_district_groups(primary_coords, grid_step=grid_step)
    district_count, shifts_applied = _space_groups(
        primary_coords,
        district_groups,
        min_group_gap=grid_step,
        grid_step=grid_step,
    )

    anchor_positions = {
        anchor: primary_coords[anchor_primaries[anchor]]
        for anchor in anchor_groups
    }
    report = {
        "horizontal_run_count": len(horizontal_runs),
        "vertical_run_count": len(vertical_runs),
        "district_count": district_count,
        "district_shifts_applied": shifts_applied,
        "district_min_gap": grid_step,
    }
    return anchor_positions, report


def _select_anchor_primaries(raw_zone: dict, anchor_groups: Dict[Tuple[int, int], List[str]]) -> Dict[Tuple[int, int], str]:
    raw_rooms = {str(room.get("id") or ""): room for room in raw_zone.get("rooms", [])}
    primaries: Dict[Tuple[int, int], str] = {}
    for anchor, room_ids in anchor_groups.items():
        def sort_key(room_id: str) -> Tuple[int, int, str]:
            raw_room = raw_rooms.get(room_id, {})
            return (
                -len(raw_room.get("exits") or {}),
                -len(raw_room.get("special_exits") or {}),
                room_id,
            )

        primaries[anchor] = sorted(room_ids, key=sort_key)[0]
    return primaries


def _align_display_coords_to_primaries(
    anchor_groups: Dict[Tuple[int, int], List[str]],
    anchor_primaries: Dict[Tuple[int, int], str],
    anchor_positions: Dict[Tuple[int, int], Tuple[int, int]] | None = None,
) -> Dict[str, Tuple[int, int]]:
    display_coords: Dict[str, Tuple[int, int]] = {}
    offsets = [
        (-12, 0),
        (12, 0),
        (0, -12),
        (0, 12),
        (-12, -12),
        (12, -12),
        (-12, 12),
        (12, 12),
    ]
    for (anchor_x, anchor_y), room_ids in anchor_groups.items():
        base_x, base_y = anchor_positions.get((anchor_x, anchor_y), (anchor_x, anchor_y)) if anchor_positions else (anchor_x, anchor_y)
        primary_room_id = anchor_primaries[(anchor_x, anchor_y)]
        display_coords[primary_room_id] = (base_x, base_y)
        secondary_room_ids = sorted(room_id for room_id in room_ids if room_id != primary_room_id)
        for index, room_id in enumerate(secondary_room_ids):
            dx, dy = offsets[index] if index < len(offsets) else (0, 16 * (index - len(offsets) + 1))
            display_coords[room_id] = (base_x + dx, base_y + dy)
    return display_coords


def _detect_grid_step(coords: Dict[str, Tuple[int, int]]) -> int:
    deltas = Counter()
    values = list(coords.values())
    for index, (x1, y1) in enumerate(values):
        for x2, y2 in values[index + 1 :]:
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            if 0 < dx <= 120:
                deltas[dx] += 1
            if 0 < dy <= 120:
                deltas[dy] += 1
    if not deltas:
        return 40
    return deltas.most_common(1)[0][0]


def _candidate_for_direction(
    room_id: str,
    coords: Dict[str, Tuple[int, int]],
    direction: str,
    grid_step: int,
) -> str | None:
    origin_x, origin_y = coords[room_id]
    align_tolerance = max(10, grid_step // 2)
    best_room_id = None
    best_metric = None

    def maybe_take(candidate_id: str, metric: Tuple[int, int, int]) -> None:
        nonlocal best_room_id, best_metric
        if best_metric is None or metric < best_metric:
            best_room_id = candidate_id
            best_metric = metric

    for candidate_id, (target_x, target_y) in coords.items():
        if candidate_id == room_id:
            continue
        dx = target_x - origin_x
        dy = target_y - origin_y
        if direction == "east":
            if dx <= 0 or abs(dy) > align_tolerance:
                continue
            maybe_take(candidate_id, (dx, abs(dy), abs(dx) + abs(dy)))
        elif direction == "west":
            if dx >= 0 or abs(dy) > align_tolerance:
                continue
            maybe_take(candidate_id, (abs(dx), abs(dy), abs(dx) + abs(dy)))
        elif direction == "south":
            if dy <= 0 or abs(dx) > align_tolerance:
                continue
            maybe_take(candidate_id, (dy, abs(dx), abs(dx) + abs(dy)))
        elif direction == "north":
            if dy >= 0 or abs(dx) > align_tolerance:
                continue
            maybe_take(candidate_id, (abs(dy), abs(dx), abs(dx) + abs(dy)))
        elif direction == "northeast":
            if dx <= 0 or dy >= 0 or abs(abs(dx) - abs(dy)) > align_tolerance:
                continue
            maybe_take(candidate_id, (max(abs(dx), abs(dy)), abs(abs(dx) - abs(dy)), abs(dx) + abs(dy)))
        elif direction == "northwest":
            if dx >= 0 or dy >= 0 or abs(abs(dx) - abs(dy)) > align_tolerance:
                continue
            maybe_take(candidate_id, (max(abs(dx), abs(dy)), abs(abs(dx) - abs(dy)), abs(dx) + abs(dy)))
        elif direction == "southeast":
            if dx <= 0 or dy <= 0 or abs(abs(dx) - abs(dy)) > align_tolerance:
                continue
            maybe_take(candidate_id, (max(abs(dx), abs(dy)), abs(abs(dx) - abs(dy)), abs(dx) + abs(dy)))
        elif direction == "southwest":
            if dx >= 0 or dy <= 0 or abs(abs(dx) - abs(dy)) > align_tolerance:
                continue
            maybe_take(candidate_id, (max(abs(dx), abs(dy)), abs(abs(dx) - abs(dy)), abs(dx) + abs(dy)))
    return best_room_id


def _build_immediate_exit_map(coords: Dict[str, Tuple[int, int]], include_diagonals: bool, grid_step: int) -> Dict[str, Dict[str, str]]:
    coord_to_room = {coord: room_id for room_id, coord in coords.items()}
    directions = dict(CARDINAL_DIRECTIONS)
    if include_diagonals:
        directions.update(DIAGONAL_DIRECTIONS)
    geometric_exits: Dict[str, Dict[str, str]] = {room_id: {} for room_id in coords}
    for room_id, (origin_x, origin_y) in coords.items():
        for direction, (dx_unit, dy_unit) in directions.items():
            target_id = coord_to_room.get((origin_x + dx_unit * grid_step, origin_y + dy_unit * grid_step))
            if target_id:
                geometric_exits[room_id][direction] = target_id
    return geometric_exits


def _build_geometric_exit_map(
    coords: Dict[str, Tuple[int, int]],
    include_diagonals: bool,
    mode: str,
) -> Dict[str, Dict[str, str]]:
    grid_step = _detect_grid_step(coords)
    if mode == "immediate":
        return _build_immediate_exit_map(coords, include_diagonals=include_diagonals, grid_step=grid_step)
    directions = dict(CARDINAL_DIRECTIONS)
    if include_diagonals:
        directions.update(DIAGONAL_DIRECTIONS)
    nearest = {
        room_id: {
            direction: _candidate_for_direction(room_id, coords, direction, grid_step)
            for direction in directions
        }
        for room_id in coords
    }

    geometric_exits: Dict[str, Dict[str, str]] = {room_id: {} for room_id in coords}
    for room_id, exit_candidates in nearest.items():
        for direction, target_id in exit_candidates.items():
            if not target_id:
                continue
            reverse = OPPOSITE_DIRECTION[direction]
            if nearest.get(target_id, {}).get(reverse) != room_id:
                continue
            geometric_exits[room_id][direction] = target_id
    return geometric_exits


def _make_exit_payload(target_id: str) -> dict:
    return {
        "target": target_id,
        "typeclass": "typeclasses.exits.Exit",
        "speed": "",
        "travel_time": 0,
    }


def _merge_special_exits(room: dict, original_exits: dict, kept_exits: Dict[str, str]) -> dict:
    special_exits = copy.deepcopy(room.get("special_exits") or {})
    for direction, exit_spec in (original_exits or {}).items():
        target_id = str((exit_spec or {}).get("target") or "")
        if kept_exits.get(direction) == target_id:
            continue
        key = f"raw_{direction}_{target_id}" if target_id else f"raw_{direction}"
        special_exits[key] = copy.deepcopy(exit_spec)
    return special_exits


def build_builder_target_zone(
    raw_zone: dict,
    seeded_zone: dict,
    output_zone_id: str,
    include_diagonals: bool,
    adjacency_mode: str,
) -> Tuple[dict, dict]:
    seeded_coords = _read_room_coords(seeded_zone)
    grid_step = _detect_grid_step(seeded_coords)
    snapped_anchor_coords, _display_coords, anchor_groups, snap_report = _resolve_snapped_layout(seeded_coords, grid_step=grid_step)
    anchor_primaries = _select_anchor_primaries(raw_zone, anchor_groups)
    display_coords = _align_display_coords_to_primaries(anchor_groups, anchor_primaries)
    primary_coords = {
        primary_room_id: anchor
        for anchor, primary_room_id in anchor_primaries.items()
    }
    geometric_exit_map = _build_geometric_exit_map(
        primary_coords,
        include_diagonals=include_diagonals,
        mode=adjacency_mode,
    )

    output_rooms: List[dict] = []
    stats = {
        "room_count": len(raw_zone.get("rooms", [])),
        "grid_step": grid_step,
        "spatial_exit_count": 0,
        "raw_spatial_exit_count": 0,
        "raw_special_exit_count": 0,
        "promoted_directions": Counter(),
    }

    for raw_room in raw_zone.get("rooms", []):
        room_id = str(raw_room.get("id") or "")
        output_room = copy.deepcopy(raw_room)
        output_room["zone_id"] = output_zone_id
        output_room["map"] = {
            "x": display_coords[room_id][0],
            "y": display_coords[room_id][1],
            "layer": int((raw_room.get("map") or {}).get("layer", 0) or 0),
        }

        original_exits = copy.deepcopy(raw_room.get("exits") or {})
        original_special_exits = raw_room.get("special_exits") or {}
        stats["raw_spatial_exit_count"] += len(original_exits)
        stats["raw_special_exit_count"] += len(original_special_exits)

        room_anchor = snapped_anchor_coords[room_id]
        is_anchor_primary = anchor_primaries[room_anchor] == room_id
        rebuilt_exits = {}
        if is_anchor_primary:
            rebuilt_exits = {
                direction: _make_exit_payload(target_id)
                for direction, target_id in geometric_exit_map.get(room_id, {}).items()
            }
        for direction in rebuilt_exits:
            stats["promoted_directions"][direction] += 1

        output_room["exits"] = rebuilt_exits
        output_room["special_exits"] = _merge_special_exits(output_room, original_exits, geometric_exit_map.get(room_id, {}))
        details = copy.deepcopy(output_room.get("details") or {})
        details["builder_target_source_zone"] = str(raw_zone.get("zone_id") or "")
        details["builder_target_layout_zone"] = str(seeded_zone.get("zone_id") or "")
        details["builder_target_anchor_x"] = snapped_anchor_coords[room_id][0]
        details["builder_target_anchor_y"] = snapped_anchor_coords[room_id][1]
        details["builder_target_anchor_primary"] = is_anchor_primary
        output_room["details"] = details
        stats["spatial_exit_count"] += len(rebuilt_exits)
        output_rooms.append(output_room)

    zone = {
        "schema_version": raw_zone.get("schema_version", "v1"),
        "zone_id": output_zone_id,
        "name": output_zone_id,
        "rooms": output_rooms,
    }
    report = {
        "zone_id": output_zone_id,
        "room_count": stats["room_count"],
        "grid_step": stats["grid_step"],
        "spatial_exit_count": stats["spatial_exit_count"],
        "raw_spatial_exit_count": stats["raw_spatial_exit_count"],
        "raw_special_exit_count": stats["raw_special_exit_count"],
        "direction_counts": dict(stats["promoted_directions"]),
        "include_diagonals": include_diagonals,
        "adjacency_mode": adjacency_mode,
        "anchor_primary_count": len(anchor_primaries),
        **snap_report,
    }
    return zone, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a builder-target preview zone for crossingV2.")
    parser.add_argument(
        "--raw-zone",
        default="worlddata/zones/crossingV2.raw.yaml",
        help="Source zone whose room ids and metadata should be preserved.",
    )
    parser.add_argument(
        "--layout-zone",
        default="worlddata/zones/crossingV2_seeded.yaml",
        help="Zone whose map coordinates should drive the preview layout.",
    )
    parser.add_argument(
        "--output-zone",
        default="worlddata/zones/crossingV2_builder_target.yaml",
        help="Output YAML path.",
    )
    parser.add_argument(
        "--report-path",
        default="build/crossingV2_builder_target/layout_report.json",
        help="Where to write a summary report.",
    )
    parser.add_argument(
        "--zone-id",
        default="crossingv2_builder_target",
        help="Zone id to emit in the preview file.",
    )
    parser.add_argument(
        "--cardinals-only",
        action="store_true",
        help="Restrict generated spatial exits to north/south/east/west.",
    )
    parser.add_argument(
        "--adjacency-mode",
        choices=["immediate", "nearest"],
        default="immediate",
        help="How to derive visible spatial exits from the layout grid.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    raw_zone = _load_yaml(root / args.raw_zone)
    layout_zone = _load_yaml(root / args.layout_zone)
    output_zone, report = build_builder_target_zone(
        raw_zone=raw_zone,
        seeded_zone=layout_zone,
        output_zone_id=args.zone_id,
        include_diagonals=not args.cardinals_only,
        adjacency_mode=args.adjacency_mode,
    )
    output_path = root / args.output_zone
    report_path = root / args.report_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _dump_yaml(output_path, output_zone)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()