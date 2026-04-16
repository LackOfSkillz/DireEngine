from evennia.utils import logger

from world.simulation.kernel import SIM_KERNEL
from world.simulation.patrol_routes import ensure_patrol_route, get_patrol_route
from world.simulation.patrol_zones import get_patrol_zone_coverage_summary, get_patrol_zone_for_guard


def _normalize_zone_id(zone_id):
    normalized = str(zone_id or "landing").strip().lower()
    return normalized or "landing"


def _get_room_zone_id(room):
    room_db = getattr(room, "db", None)
    return _normalize_zone_id(getattr(room_db, "guard_zone", None) or getattr(room_db, "zone", None))


def _normalize_room_ids(room_ids):
    normalized = []
    for room_id in list(room_ids or []):
        current_room_id = int(room_id or 0)
        if current_room_id <= 0 or current_room_id in normalized:
            continue
        normalized.append(current_room_id)
    return normalized


def _get_guard_patrol_room_ids(guard, home_room_id):
    authored_route = getattr(getattr(guard, "db", None), "patrol_route", None)
    normalized_authored_route = _normalize_room_ids(authored_route)
    if normalized_authored_route:
        return normalized_authored_route

    home_room = getattr(guard, "location", None)
    if home_room is None or home_room_id is None:
        return [home_room_id] if home_room_id is not None else []

    home_zone_id = _get_room_zone_id(home_room)
    adjacent_room_ids = []
    for obj in list(getattr(home_room, "contents", []) or []):
        destination = getattr(obj, "destination", None)
        destination_id = int(getattr(destination, "id", 0) or 0)
        if destination is None or destination_id <= 0 or destination_id == int(home_room_id or 0):
            continue
        if _get_room_zone_id(destination) != home_zone_id:
            continue
        if destination_id not in adjacent_room_ids:
            adjacent_room_ids.append(destination_id)

    if not adjacent_room_ids:
        return [home_room_id]

    fallback_route = []
    for adjacent_room_id in adjacent_room_ids:
        fallback_route.append(adjacent_room_id)
        fallback_route.append(home_room_id)
    return _normalize_room_ids(fallback_route)


def get_or_create_guard_zone_service(zone_id):
    from world.simulation.zones.guard_zone_service import GuardZoneService

    normalized_zone_id = _normalize_zone_id(zone_id)
    service_id = f"guard_zone:{normalized_zone_id}"
    service = SIM_KERNEL.services.get(service_id)
    if isinstance(service, GuardZoneService):
        return service
    return GuardZoneService(service_id=service_id, zone_id=normalized_zone_id)


def register_guard(guard):
    if not guard or not getattr(guard, "id", None):
        return None
    if not bool(getattr(getattr(guard, "db", None), "is_guard", False)):
        return None
    zone_id = getattr(getattr(guard, "db", None), "zone_id", None) or getattr(getattr(guard, "db", None), "zone", None)
    service = get_or_create_guard_zone_service(zone_id)
    sim_state = getattr(guard, "sim_state", None)
    if sim_state is not None:
        current_room_id = int(getattr(getattr(guard, "location", None), "id", 0) or 0) or None
        patrol_zone = get_patrol_zone_for_guard(int(getattr(guard, "id", 0) or 0))
        home_room_id = sim_state.ensure_home_room_id(current_room_id)
        if sim_state.get_patrol_zone_id() is None and patrol_zone is not None:
            patrol_zone_id = patrol_zone.get("zone_id")
            patrol_home_room_id = int(patrol_zone.get("home_room_id", 0) or 0) or home_room_id
            patrol_room_ids = list(patrol_zone.get("room_ids") or [])
            patrol_route_room_ids = list(patrol_zone.get("route_room_ids") or patrol_room_ids)
            route_id = f"patrol_zone:{patrol_zone_id}"
            ensure_patrol_route(route_id, patrol_route_room_ids, loop=True)
            sim_state.set_patrol_zone_id(patrol_zone_id)
            sim_state.set_patrol_home_room_id(patrol_home_room_id)
            sim_state.set_patrol_room_ids(patrol_room_ids)
            sim_state.set_patrol_route_room_ids(patrol_route_room_ids)
            sim_state.set_patrol_enabled(True)
            sim_state.set_patrol_route_id(route_id)
            if sim_state.home_room_id is None and patrol_home_room_id is not None:
                sim_state.ensure_home_room_id(patrol_home_room_id)
        elif patrol_zone is not None and sim_state.get_patrol_zone_id() == patrol_zone.get("zone_id"):
            patrol_home_room_id = int(patrol_zone.get("home_room_id", 0) or 0) or home_room_id
            patrol_room_ids = list(patrol_zone.get("room_ids") or [])
            patrol_route_room_ids = list(patrol_zone.get("route_room_ids") or patrol_room_ids)
            route_id = f"patrol_zone:{patrol_zone.get('zone_id')}"
            ensure_patrol_route(route_id, patrol_route_room_ids, loop=True)
            if sim_state.get_patrol_home_room_id() is None and patrol_home_room_id is not None:
                sim_state.set_patrol_home_room_id(patrol_home_room_id)
            if not sim_state.get_patrol_room_ids() and patrol_room_ids:
                sim_state.set_patrol_room_ids(patrol_room_ids)
            if not sim_state.get_patrol_route_room_ids() and patrol_route_room_ids:
                sim_state.set_patrol_route_room_ids(patrol_route_room_ids)
            sim_state.set_patrol_enabled(True)
            if not sim_state.patrol_route_id:
                sim_state.set_patrol_route_id(route_id)
        elif sim_state.get_patrol_zone_id() is None:
            sim_state.set_patrol_enabled(False)
            sim_state.set_patrol_room_ids([])

        route_id = sim_state.patrol_route_id
        patrol_room_ids = sim_state.get_patrol_room_ids() or _get_guard_patrol_room_ids(guard, home_room_id)
        if route_id and get_patrol_route(route_id) is None and home_room_id is not None:
            ensure_patrol_route(route_id, patrol_room_ids or [home_room_id], loop=True)
        if not route_id and home_room_id is not None:
            route_id = f"guard_home_patrol:{int(getattr(guard, 'id', 0) or 0)}"
            ensure_patrol_route(route_id, patrol_room_ids or [home_room_id], loop=True)
            sim_state.set_patrol_route_id(route_id)
        if home_room_id is not None and sim_state.movement_target_room_id is None:
            sim_state.set_movement_target_room_id(home_room_id)
        sim_state.set_movement_progress_index(int(sim_state.patrol_index or 0))
        sim_state.save_if_needed()
    service.add_guard(guard)
    return service


def unregister_guard(guard):
    if not guard or not getattr(guard, "id", None):
        return None
    zone_id = getattr(getattr(guard, "db", None), "zone_id", None) or getattr(getattr(guard, "db", None), "zone", None)
    service = get_or_create_guard_zone_service(zone_id)
    service.npc_ids.discard(int(getattr(guard, "id", 0) or 0))
    return service


def register_existing_guards():
    from world.systems.guards import iter_active_guards

    registered = 0
    service_ids = set()
    service_counts = {}
    assigned_patrol_zone_ids = set()
    for guard in iter_active_guards():
        service = register_guard(guard)
        if service is None:
            continue
        sim_state = getattr(guard, "sim_state", None)
        if sim_state is not None and sim_state.get_patrol_zone_id() is not None:
            assigned_patrol_zone_ids.add(sim_state.get_patrol_zone_id())
        guard_zone_id = getattr(getattr(guard, "db", None), "zone_id", None) or getattr(getattr(guard, "db", None), "zone", None) or "landing"
        logger.log_err(
            f"[BOOT] Registering guard {int(getattr(guard, 'id', 0) or 0)} in zone {str(guard_zone_id).strip().lower() or 'landing'} via {service.service_id}"
        )
        registered += 1
        service_ids.add(service.service_id)
        service_counts[service.service_id] = len(getattr(service, "npc_ids", []) or [])
    logger.log_err(
        f"[BOOT] Registration summary: registered={registered} services={len(service_ids)} counts={service_counts or {}}"
    )
    logger.log_err(
        f"[BOOT] Patrol coverage summary: assigned_zones={sorted(assigned_patrol_zone_ids)} coverage={get_patrol_zone_coverage_summary()}"
    )
    return {"registered": registered, "service_count": len(service_ids)}


def get_guard_zone_service_for_room(room):
    if room is None:
        return None
    room_db = getattr(room, "db", None)
    zone_id = getattr(room_db, "guard_zone", None) or getattr(room_db, "zone", None) or "landing"
    return get_or_create_guard_zone_service(zone_id)


def get_zone_facts_for_room(room):
    from world.simulation.cache.zone_facts import get_or_create_zone_facts

    if room is None:
        return get_or_create_zone_facts("landing")
    room_db = getattr(room, "db", None)
    zone_id = getattr(room_db, "guard_zone", None) or getattr(room_db, "zone", None) or "landing"
    return get_or_create_zone_facts(zone_id)
