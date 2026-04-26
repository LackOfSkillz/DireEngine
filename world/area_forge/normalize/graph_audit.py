from __future__ import annotations

import math


def _node_id(node):
    return str(node.get("id") or "")


def _node_lookup(nodes):
    return {_node_id(node): node for node in list(nodes or []) if _node_id(node)}


def _position(node):
    if "lane_x" in node and "lane_y" in node:
        return int(node.get("lane_x", 0)), int(node.get("lane_y", 0))
    return int(node.get("x", 0)), int(node.get("y", 0))


def direction_from_delta(dx, dy):
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


def detect_long_edges(nodes, edges, threshold=3):
    lookup = _node_lookup(nodes)
    long_edges = []
    for edge in list(edges or []):
        source = lookup.get(str(edge.get("source") or ""))
        target = lookup.get(str(edge.get("target") or ""))
        if not source or not target:
            continue
        source_x, source_y = _position(source)
        target_x, target_y = _position(target)
        dx = abs(source_x - target_x)
        dy = abs(source_y - target_y)
        distance = dx + dy
        if distance > threshold:
            long_edges.append({
                "source": str(edge.get("source") or ""),
                "target": str(edge.get("target") or ""),
                "direction": edge.get("direction"),
                "distance": int(distance),
                "dx": int(dx),
                "dy": int(dy),
            })
    return long_edges


def validate_direction_consistency(nodes, edges):
    lookup = _node_lookup(nodes)
    mismatches = []
    for edge in list(edges or []):
        source = lookup.get(str(edge.get("source") or ""))
        target = lookup.get(str(edge.get("target") or ""))
        if not source or not target:
            continue
        source_x, source_y = _position(source)
        target_x, target_y = _position(target)
        dx = int(target_x - source_x)
        dy = int(target_y - source_y)
        expected_direction = direction_from_delta(dx, dy)
        stored_direction = edge.get("direction")
        if expected_direction and stored_direction != expected_direction:
            mismatches.append({
                "source": str(edge.get("source") or ""),
                "target": str(edge.get("target") or ""),
                "stored_direction": stored_direction,
                "expected_direction": expected_direction,
                "dx": dx,
                "dy": dy,
            })
    return mismatches


def audit_graph(nodes, edges):
    node_ids = [_node_id(node) for node in list(nodes or []) if _node_id(node)]
    adjacency = {node_id: set() for node_id in node_ids}
    triple_counts = {}
    directed_pairs = set()

    for edge in list(edges or []):
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        direction = str(edge.get("direction") or "")
        if source in adjacency:
            adjacency[source].add(target)
        if target in adjacency:
            adjacency[target].add(source)
        triple = (source, target, direction)
        triple_counts[triple] = triple_counts.get(triple, 0) + 1
        directed_pairs.add((source, target))

    degree_histogram = {}
    isolated_nodes = []
    for node_id in node_ids:
        degree = len([neighbor for neighbor in adjacency[node_id] if neighbor])
        degree_histogram[str(degree)] = degree_histogram.get(str(degree), 0) + 1
        if degree == 0:
            isolated_nodes.append(node_id)

    one_way_edges = []
    for source, target in sorted(directed_pairs):
        if not source or not target:
            continue
        if (target, source) not in directed_pairs:
            one_way_edges.append({"source": source, "target": target})

    duplicate_edges = []
    for (source, target, direction), count in sorted(triple_counts.items()):
        if count > 1:
            duplicate_edges.append({
                "source": source,
                "target": target,
                "direction": direction,
                "count": int(count),
            })

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "degree_histogram": degree_histogram,
        "isolated_nodes": isolated_nodes,
        "one_way_edges": one_way_edges,
        "long_edges": detect_long_edges(nodes, edges),
        "duplicate_edges": duplicate_edges,
    }