"""Static patrol zone registry for bounded city guard coverage."""

PATROL_ZONES = {
    "amberwick_watch": {
        "zone_id": "amberwick_watch",
        "guard_id": 24581,
        "home_room_id": 4214,
        "room_ids": [4212, 4213, 4214, 4215, 4216, 4218],
        "route_room_ids": [4213, 4214, 4215, 4216, 4215, 4214, 4212, 4214, 4218, 4214],
        "neighbor_zone_ids": ["stonewake_watch"],
    },
    "lanternrest_watch": {
        "zone_id": "lanternrest_watch",
        "guard_id": 24571,
        "home_room_id": 4260,
        "room_ids": [4239, 4246, 4258, 4259, 4260],
        "route_room_ids": [4239, 4246, 4260, 4259, 4258, 4246],
        "neighbor_zone_ids": ["eastreach_watch", "stonewake_watch"],
    },
    "stonewake_watch": {
        "zone_id": "stonewake_watch",
        "guard_id": 24569,
        "home_room_id": 4273,
        "room_ids": [4267, 4273, 4287],
        "route_room_ids": [4267, 4273, 4287, 4273],
        "neighbor_zone_ids": ["amberwick_watch", "lanternrest_watch"],
    },
    "eastreach_watch": {
        "zone_id": "eastreach_watch",
        "guard_id": 24570,
        "home_room_id": 4367,
        "room_ids": [4351, 4352, 4365, 4366, 4367, 4368],
        "route_room_ids": [4351, 4352, 4367, 4366, 4365, 4367, 4368, 4367],
        "neighbor_zone_ids": ["lanternrest_watch", "marrowmarket_watch"],
    },
    "marrowmarket_watch": {
        "zone_id": "marrowmarket_watch",
        "guard_id": 24568,
        "home_room_id": 4390,
        "room_ids": [4376, 4387, 4390],
        "route_room_ids": [4376, 4387, 4390, 4387],
        "neighbor_zone_ids": ["eastreach_watch"],
    },
}


def _normalize_zone(zone):
    if not isinstance(zone, dict):
        return None
    room_ids = []
    for room_id in list(zone.get("room_ids") or []):
        normalized_room_id = int(room_id or 0)
        if normalized_room_id <= 0 or normalized_room_id in room_ids:
            continue
        room_ids.append(normalized_room_id)
    route_room_ids = []
    for room_id in list(zone.get("route_room_ids") or room_ids):
        normalized_room_id = int(room_id or 0)
        if normalized_room_id <= 0 or normalized_room_id not in room_ids:
            continue
        route_room_ids.append(normalized_room_id)
    zone_id = str(zone.get("zone_id") or "").strip()
    if not zone_id or not room_ids:
        return None
    return {
        "zone_id": zone_id,
        "guard_id": int(zone.get("guard_id", 0) or 0) or None,
        "home_room_id": int(zone.get("home_room_id", 0) or 0) or None,
        "room_ids": room_ids,
        "route_room_ids": route_room_ids or list(room_ids),
        "neighbor_zone_ids": [str(value).strip() for value in list(zone.get("neighbor_zone_ids") or []) if str(value).strip()],
    }


def iter_patrol_zones():
    for zone in PATROL_ZONES.values():
        normalized = _normalize_zone(zone)
        if normalized is not None:
            yield normalized


def get_patrol_zone(zone_id):
    normalized_zone_id = str(zone_id or "").strip()
    if not normalized_zone_id:
        return None
    zone = PATROL_ZONES.get(normalized_zone_id)
    return _normalize_zone(zone)


def get_patrol_zone_for_guard(guard_id):
    normalized_guard_id = int(guard_id or 0) or 0
    if normalized_guard_id <= 0:
        return None
    for zone in iter_patrol_zones():
        if int(zone.get("guard_id", 0) or 0) == normalized_guard_id:
            return zone
    return None


def get_patrol_zone_for_room(room_id):
    normalized_room_id = int(room_id or 0) or 0
    if normalized_room_id <= 0:
        return None
    for zone in iter_patrol_zones():
        if normalized_room_id in list(zone.get("room_ids") or []):
            return zone
    return None


def get_patrol_zone_coverage_summary():
    zones = list(iter_patrol_zones())
    room_ids = set()
    assigned_guard_ids = set()
    for zone in zones:
        room_ids.update(zone.get("room_ids") or [])
        guard_id = int(zone.get("guard_id", 0) or 0)
        if guard_id > 0:
            assigned_guard_ids.add(guard_id)
    return {
        "zone_count": len(zones),
        "assigned_guard_count": len(assigned_guard_ids),
        "covered_room_count": len(room_ids),
        "zone_sizes": {zone["zone_id"]: len(zone.get("room_ids") or []) for zone in zones},
    }