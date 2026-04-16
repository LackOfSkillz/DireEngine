from __future__ import annotations


BUILDER_MAP_IMPORT_AVAILABLE = False

try:
    from world.builder.schemas.map_schema_v1 import validate_map_schema

    from .exit_service import BUILDER_EXIT_SERVICE_AVAILABLE, ensure_exit
    from .room_service import BUILDER_ROOM_SERVICE_AVAILABLE, create_room, get_room
except Exception:  # pragma: no cover - optional builder dependency guard
    validate_map_schema = None
    ensure_exit = None
    create_room = None
    get_room = None
else:
    BUILDER_MAP_IMPORT_AVAILABLE = BUILDER_ROOM_SERVICE_AVAILABLE and BUILDER_EXIT_SERVICE_AVAILABLE


def _require_builder_runtime() -> None:
    if not BUILDER_MAP_IMPORT_AVAILABLE:
        raise RuntimeError("Builder map importer is unavailable because the Evennia runtime could not be imported.")


def import_map(data: dict, mode: str = "safe"):
    _require_builder_runtime()
    validate_map_schema(data)
    normalized_mode = str(mode or "safe").strip().lower() or "safe"
    if normalized_mode not in {"safe", "strict"}:
        raise ValueError("mode must be one of: safe, strict")

    room_index = {}
    exits_created = 0
    exits_replaced = 0

    for room_data in data["rooms"]:
        room_payload = dict(room_data)
        room_payload["area_id"] = data["area_id"]
        room_payload["region"] = data["area_id"]
        room = create_room(room_payload)
        room_index[room_data["id"]] = room

    for room_data in data["rooms"]:
        source = room_index[room_data["id"]]
        for direction, target_id in room_data["exits"].items():
            target = room_index[target_id]
            _, action = ensure_exit(source, direction, target)
            if action == "created":
                exits_created += 1
            elif action == "replaced":
                exits_replaced += 1

    if normalized_mode == "strict":
        # Placeholder for future exact-topology enforcement.
        pass

    return {
        "mode": normalized_mode,
        "rooms_created": len(room_index),
        "exits_created": exits_created,
        "exits_replaced": exits_replaced,
    }