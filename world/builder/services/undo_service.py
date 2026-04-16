from __future__ import annotations


UNDO_AVAILABLE = False

try:
    import world.builder.services.exit_service as exit_service
    import world.builder.services.instance_service as instance_service
    import world.builder.services.map_diff_service as map_diff_service
    import world.builder.services.placement_service as placement_service
    import world.builder.services.room_service as room_service
except Exception:  # pragma: no cover - optional builder dependency guard
    exit_service = None
    instance_service = None
    map_diff_service = None
    placement_service = None
    room_service = None
else:
    UNDO_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not UNDO_AVAILABLE:
        raise RuntimeError("Builder undo service is unavailable because the Evennia runtime could not be imported.")


def is_operation_invertible(op: dict) -> bool:
    op_type = str((op or {}).get("op") or "")
    return op_type in {"update_room", "set_exit", "update_exit", "delete_exit", "move_object"}


def _capture_exit_snapshot(exit_obj) -> dict:
    destination = getattr(exit_obj, "destination", None)
    aliases_handler = getattr(exit_obj, "aliases", None)
    aliases = []
    if aliases_handler is not None and hasattr(aliases_handler, "all"):
        for raw_alias in list(aliases_handler.all() or []):
            alias = str(raw_alias or "").strip()
            if alias and alias not in aliases:
                aliases.append(alias)
    return {
        "direction": str(getattr(exit_obj, "key", "") or ""),
        "target_id": str(getattr(getattr(destination, "db", None), "builder_id", "") or "").strip() or None,
        "target_zone_id": str(getattr(getattr(destination, "db", None), "zone_id", "") or getattr(getattr(destination, "db", None), "zone", "") or getattr(getattr(destination, "db", None), "area_id", "") or "").strip() or None,
        "label": str(getattr(getattr(exit_obj, "db", None), "exit_display_name", "") or ""),
        "aliases": aliases,
    }


def _capture_room_updates(room, updates: dict) -> dict:
    captured = {}
    for field_name in updates.keys():
        if field_name == "name":
            captured[field_name] = str(getattr(room, "key", "") or "")
        elif field_name in {"description", "desc"}:
            captured[field_name] = str(getattr(getattr(room, "db", None), "desc", "") or "")
        elif field_name == "map_x":
            captured[field_name] = int(getattr(getattr(room, "db", None), "map_x", 0) or 0)
        elif field_name == "map_y":
            captured[field_name] = int(getattr(getattr(room, "db", None), "map_y", 0) or 0)
        elif field_name == "map_layer":
            captured[field_name] = int(getattr(getattr(room, "db", None), "map_layer", 0) or 0)
        elif field_name == "area_id":
            captured[field_name] = str(getattr(getattr(room, "db", None), "area_id", "") or "")
    return captured


def capture_pre_state(op: dict) -> dict | None:
    _require_builder_runtime()
    payload = dict(op or {})
    op_type = str(payload.get("op") or "")

    if op_type == "update_room":
        room = room_service.get_room(payload["room_id"])
        if room is None:
            raise ValueError(f"Unknown room_id: {payload['room_id']}")
        return {
            "op": op_type,
            "room_id": str(payload["room_id"]),
            "updates": _capture_room_updates(room, dict(payload.get("updates") or {})),
        }

    if op_type in {"set_exit", "delete_exit"}:
        source = room_service.get_room(payload["source_id"])
        if source is None:
            raise ValueError(f"Unknown source_id: {payload['source_id']}")
        existing = exit_service.find_exit(source, payload["direction"])
        destination = getattr(existing, "destination", None) if existing is not None else None
        target_id = str(getattr(getattr(destination, "db", None), "builder_id", "") or "").strip() or None
        return {
            "op": op_type,
            "source_id": str(payload["source_id"]),
            "direction": str(payload["direction"]),
            "target_id": target_id,
        }

    if op_type == "update_exit":
        existing = exit_service.get_exit_by_id(payload["exit_id"])
        if existing is None:
            raise ValueError(f"Unknown exit_id: {payload['exit_id']}")
        return {
            "op": op_type,
            "exit_id": str(payload["exit_id"]),
            "fields": _capture_exit_snapshot(existing),
        }

    if op_type == "move_object":
        obj = instance_service.require_instance(payload["object_id"])
        return {
            "op": op_type,
            "object_id": str(payload["object_id"]),
            "placement": placement_service.get_placement_info(obj),
        }

    return None


def invert_operation(op: dict, pre_state: dict | None = None) -> dict:
    _require_builder_runtime()
    payload = dict(op or {})
    op_type = str(payload.get("op") or "")

    if op_type == "update_room":
        if not isinstance(pre_state, dict):
            raise ValueError("pre_state is required for update_room inversion.")
        return {
            "op": "update_room",
            "room_id": str(payload["room_id"]),
            "updates": dict(pre_state.get("updates") or {}),
        }

    if op_type == "set_exit":
        if not isinstance(pre_state, dict):
            raise ValueError("pre_state is required for set_exit inversion.")
        if pre_state.get("target_id"):
            return {
                "op": "set_exit",
                "source_id": str(payload["source_id"]),
                "direction": str(payload["direction"]),
                "target_id": str(pre_state["target_id"]),
            }
        return {
            "op": "delete_exit",
            "source_id": str(payload["source_id"]),
            "direction": str(payload["direction"]),
        }

    if op_type == "update_exit":
        if not isinstance(pre_state, dict):
            raise ValueError("pre_state is required for update_exit inversion.")
        return {
            "op": "update_exit",
            "exit_id": str(payload["exit_id"]),
            "fields": dict(pre_state.get("fields") or {}),
        }

    if op_type == "delete_exit":
        if not isinstance(pre_state, dict) or not pre_state.get("target_id"):
            raise ValueError("pre_state with previous target is required for delete_exit inversion.")
        return {
            "op": "set_exit",
            "source_id": str(payload["source_id"]),
            "direction": str(payload["direction"]),
            "target_id": str(pre_state["target_id"]),
        }

    if op_type == "move_object":
        placement = dict((pre_state or {}).get("placement") or {})
        destination_id = str(placement.get("location_id") or "").strip()
        relation = str(placement.get("placement_relation") or "in").strip().lower() or "in"
        if not destination_id:
            raise ValueError("pre_state with previous location is required for move_object inversion.")
        return {
            "op": "move_object",
            "object_id": str(payload["object_id"]),
            "destination_id": destination_id,
            "relation": relation,
        }

    raise ValueError(f"Operation not invertible: {op_type}")


def build_inverse_diff(diff: dict, pre_states: list[dict | None] | None = None) -> dict:
    _require_builder_runtime()
    payload = dict(diff or {})
    operations = list(payload.get("operations") or [])
    captured_states = list(pre_states or [])
    if len(captured_states) != len(operations):
        raise ValueError("pre_states must match operations length.")

    inverse_operations = []
    for index in range(len(operations) - 1, -1, -1):
        inverse_operations.append(invert_operation(operations[index], pre_state=captured_states[index]))

    return {
        "area_id": str(payload.get("area_id") or ""),
        "operations": inverse_operations,
    }


def apply_undo(undo_diff: dict) -> dict:
    _require_builder_runtime()
    return map_diff_service.apply_diff(undo_diff, history_entry_type="undo")


def apply_redo(diff: dict) -> dict:
    _require_builder_runtime()
    return map_diff_service.apply_diff(diff, history_entry_type="redo")