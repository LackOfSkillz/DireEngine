from __future__ import annotations

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


def normalize_edges(edges):
    deduped = {}
    for edge in list(edges or []):
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        direction = str(edge.get("direction") or "")
        if not source or not target or source == target:
            continue
        key = (source, target, direction)
        if key in deduped:
            continue
        deduped[key] = dict(edge)

    normalized = list(deduped.values())
    existing_keys = {(str(edge.get("source") or ""), str(edge.get("target") or ""), str(edge.get("direction") or "")) for edge in normalized}
    auto_reversed = []
    for edge in normalized:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        direction = str(edge.get("direction") or "")
        reverse_direction = OPPOSITE_DIRECTIONS.get(direction, direction)
        reverse_key = (target, source, reverse_direction)
        if reverse_key in existing_keys:
            continue
        reverse_edge = dict(edge)
        reverse_edge["source"] = target
        reverse_edge["target"] = source
        reverse_edge["direction"] = reverse_direction
        reverse_edge["auto_reverse"] = True
        auto_reversed.append(reverse_edge)
        existing_keys.add(reverse_key)

    normalized.extend(auto_reversed)
    normalized.sort(key=lambda edge: (str(edge.get("source") or ""), str(edge.get("target") or ""), str(edge.get("direction") or "")))
    return normalized