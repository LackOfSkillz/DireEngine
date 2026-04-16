"""Static patrol route registry for handler-owned movement intent."""

PATROL_ROUTES = {}


def get_patrol_route(route_id):
    return PATROL_ROUTES.get(str(route_id or "").strip())


def ensure_patrol_route(route_id, room_ids, loop=True):
    normalized_route_id = str(route_id or "").strip()
    if not normalized_route_id:
        return None
    normalized_room_ids = [int(room_id or 0) for room_id in list(room_ids or []) if int(room_id or 0) > 0]
    route = {
        "route_id": normalized_route_id,
        "room_ids": normalized_room_ids,
        "loop": bool(loop),
    }
    PATROL_ROUTES[normalized_route_id] = route
    return route


def get_route_length(route):
    if not isinstance(route, dict):
        return 0
    return len(list(route.get("room_ids") or []))