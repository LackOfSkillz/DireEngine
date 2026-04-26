from __future__ import annotations


def _cluster_axis(nodes, axis, tolerance):
    ordered = sorted(((int(node.get(axis, 0)), str(node.get("id") or ""), node) for node in list(nodes or [])), key=lambda item: (item[0], item[1]))
    clusters = []
    for value, node_id, node in ordered:
        if not clusters or abs(value - clusters[-1]["center"]) > tolerance:
            clusters.append({"index": len(clusters), "center": float(value), "node_ids": [node_id], "nodes": [node]})
            continue
        clusters[-1]["node_ids"].append(node_id)
        clusters[-1]["nodes"].append(node)
        clusters[-1]["center"] = sum(int(clustered_node.get(axis, 0)) for clustered_node in clusters[-1]["nodes"]) / len(clusters[-1]["nodes"])
    return clusters


def assign_lane_clusters(nodes, tolerance=12):
    for node in list(nodes or []):
        node["raw_x"] = int(node.get("x", 0))
        node["raw_y"] = int(node.get("y", 0))

    x_clusters = _cluster_axis(nodes, "x", tolerance)
    y_clusters = _cluster_axis(nodes, "y", tolerance)

    for cluster in x_clusters:
        for node in cluster["nodes"]:
            node["lane_x"] = int(cluster["index"])
    for cluster in y_clusters:
        for node in cluster["nodes"]:
            node["lane_y"] = int(cluster["index"])

    return {
        "tolerance": int(tolerance),
        "x_lanes": [
            {"index": int(cluster["index"]), "center": round(float(cluster["center"]), 2), "node_ids": list(cluster["node_ids"])}
            for cluster in x_clusters
        ],
        "y_lanes": [
            {"index": int(cluster["index"]), "center": round(float(cluster["center"]), 2), "node_ids": list(cluster["node_ids"])}
            for cluster in y_clusters
        ],
        "nodes": [
            {
                "id": str(node.get("id") or ""),
                "raw_x": int(node.get("raw_x", 0)),
                "raw_y": int(node.get("raw_y", 0)),
                "lane_x": int(node.get("lane_x", 0)),
                "lane_y": int(node.get("lane_y", 0)),
            }
            for node in list(nodes or [])
        ],
    }