from __future__ import annotations

from copy import deepcopy


DIFF_AVAILABLE = False


class DiffApplyError(ValueError):
    def __init__(
        self,
        message: str,
        failed_operation_index: int,
        failed_operation_id: str,
        failed_operation: dict | None = None,
        conflicts: list[dict] | None = None,
    ):
        super().__init__(message)
        self.failed_operation_index = int(failed_operation_index)
        self.failed_operation_id = str(failed_operation_id)
        self.failed_operation = dict(failed_operation or {}) if isinstance(failed_operation, dict) else None
        self.conflicts = list(conflicts or [])


try:
    from evennia.objects.models import ObjectDB

    from world.builder.services import diff_history_service, exit_service, instance_service, placement_service, room_service, spawn_service, template_service
    from world.builder.services.audit_service import log_audit_event
    from world.builder.services.instance_service import delete_instance
except Exception:  # pragma: no cover - optional builder dependency guard
    ObjectDB = None
    diff_history_service = None
    exit_service = None
    instance_service = None
    placement_service = None
    room_service = None
    spawn_service = None
    template_service = None
    log_audit_event = None
    delete_instance = None
else:
    DIFF_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not DIFF_AVAILABLE:
        raise RuntimeError("Builder map diff service is unavailable because the Evennia runtime could not be imported.")


def _require_mapping(data: object, label: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping.")
    return data


def _require_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value.strip()


def _normalize_direction(direction: object) -> str:
    return _require_non_empty_string(direction, "direction").lower()


def _normalize_operation_id(op: dict, index: int) -> str:
    return str(op.get("id") or f"auto-{index}")


def _fallback_operation_id(op, index: int) -> str:
    if isinstance(op, dict):
        return _normalize_operation_id(op, index)
    return f"auto-{index}"


def _extract_operation_ids(operations: list[dict]) -> list[str]:
    return [_normalize_operation_id(op, index) for index, op in enumerate(operations)]


def _normalize_optional_string(value) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _validate_exit_update_fields(fields: object, index: int) -> dict:
    payload = _require_mapping(fields, f"operations[{index}].fields")
    allowed_fields = {"direction", "target_id", "target_zone_id", "label", "aliases"}
    if not payload:
        raise ValueError(f"operations[{index}].fields must include at least one editable field.")
    unknown_fields = [key for key in payload.keys() if key not in allowed_fields]
    if unknown_fields:
        raise ValueError(f"operations[{index}].fields contains unknown keys: {', '.join(str(key) for key in unknown_fields)}")
    if "direction" in payload:
        _require_non_empty_string(payload.get("direction"), f"operations[{index}].fields.direction")
    if "target_id" in payload:
        _require_non_empty_string(payload.get("target_id"), f"operations[{index}].fields.target_id")
    if "target_zone_id" in payload:
        _require_non_empty_string(payload.get("target_zone_id"), f"operations[{index}].fields.target_zone_id")
    if "label" in payload and payload.get("label") is not None and not isinstance(payload.get("label"), str):
        raise ValueError(f"operations[{index}].fields.label must be a string.")
    if "aliases" in payload:
        aliases = payload.get("aliases")
        if not isinstance(aliases, list):
            raise ValueError(f"operations[{index}].fields.aliases must be a list.")
        for alias_index, alias in enumerate(aliases):
            if not isinstance(alias, str):
                raise ValueError(f"operations[{index}].fields.aliases[{alias_index}] must be a string.")
    return dict(payload)


def _validate_object_update_fields(fields: object, index: int) -> dict:
    payload = _require_mapping(fields, f"operations[{index}].fields")
    allowed_fields = {"name", "description", "attributes", "flags", "item_kind", "weight", "value"}
    if not payload:
        raise ValueError(f"operations[{index}].fields must include at least one editable field.")
    unknown_fields = [key for key in payload.keys() if key not in allowed_fields]
    if unknown_fields:
        raise ValueError(f"operations[{index}].fields contains unknown keys: {', '.join(str(key) for key in unknown_fields)}")
    if "name" in payload:
        _require_non_empty_string(payload.get("name"), f"operations[{index}].fields.name")
    if "description" in payload and payload.get("description") is not None and not isinstance(payload.get("description"), str):
        raise ValueError(f"operations[{index}].fields.description must be a string.")
    if "attributes" in payload:
        attributes = payload.get("attributes")
        if not isinstance(attributes, dict):
            raise ValueError(f"operations[{index}].fields.attributes must be a mapping.")
        for attribute_name, attribute_value in attributes.items():
            if not str(attribute_name or "").strip():
                raise ValueError(f"operations[{index}].fields.attributes contains an empty key.")
            if not isinstance(attribute_value, (int, float)):
                raise ValueError(f"operations[{index}].fields.attributes.{attribute_name} must be numeric.")
    if "flags" in payload:
        flags = payload.get("flags")
        if not isinstance(flags, list):
            raise ValueError(f"operations[{index}].fields.flags must be a list.")
        for flag_index, flag in enumerate(flags):
            if not isinstance(flag, str):
                raise ValueError(f"operations[{index}].fields.flags[{flag_index}] must be a string.")
    if "item_kind" in payload and payload.get("item_kind") is not None and not isinstance(payload.get("item_kind"), str):
        raise ValueError(f"operations[{index}].fields.item_kind must be a string.")
    if "weight" in payload and not isinstance(payload.get("weight"), (int, float)):
        raise ValueError(f"operations[{index}].fields.weight must be numeric.")
    if "value" in payload and not isinstance(payload.get("value"), (int, float)):
        raise ValueError(f"operations[{index}].fields.value must be numeric.")
    return dict(payload)


def _require_exit(exit_id: str, label: str):
    exit_obj = exit_service.get_exit_by_id(exit_id)
    if exit_obj is None:
        raise ValueError(f"Unknown {label}: {exit_id}")
    return exit_obj


def _validate_top_level(diff: dict) -> dict:
    payload = _require_mapping(diff, "diff")
    _require_non_empty_string(payload.get("area_id"), "area_id")

    operations = payload.get("operations")
    if not isinstance(operations, list):
        raise ValueError("operations must be a list.")
    return payload


def _validate_operation_structure(op: dict, index: int) -> dict:
    payload = _require_mapping(op, f"operations[{index}]")
    op_type = _require_non_empty_string(payload.get("op"), f"operations[{index}].op")

    op_id = payload.get("id")
    if op_id is not None:
        _require_non_empty_string(op_id, f"operations[{index}].id")

    required_fields = {
        "create_room": ["room"],
        "update_room": ["room_id", "updates"],
        "update_object": ["object_id", "fields"],
        "delete_room": ["room_id"],
        "set_exit": ["source_id", "direction", "target_id"],
        "update_exit": ["exit_id", "fields"],
        "delete_exit": ["source_id", "direction"],
        "move_object": ["object_id", "destination_id", "relation"],
        "spawn_template": ["template_id", "location_id"],
        "delete_object": ["object_id"],
    }
    if op_type not in required_fields:
        raise ValueError(f"Unknown operation: {op_type}")

    for field_name in required_fields[op_type]:
        if field_name not in payload:
            raise ValueError(f"operations[{index}] missing required field '{field_name}'.")

    if op_type == "create_room":
        room_payload = _require_mapping(payload.get("room"), f"operations[{index}].room")
        _require_non_empty_string(room_payload.get("id"), f"operations[{index}].room.id")
    elif op_type == "update_room":
        _require_non_empty_string(payload.get("room_id"), f"operations[{index}].room_id")
        _require_mapping(payload.get("updates"), f"operations[{index}].updates")
    elif op_type == "update_object":
        _require_non_empty_string(payload.get("object_id"), f"operations[{index}].object_id")
        payload["fields"] = _validate_object_update_fields(payload.get("fields"), index)
    elif op_type == "delete_room":
        _require_non_empty_string(payload.get("room_id"), f"operations[{index}].room_id")
    elif op_type == "set_exit":
        _require_non_empty_string(payload.get("source_id"), f"operations[{index}].source_id")
        _require_non_empty_string(payload.get("direction"), f"operations[{index}].direction")
        _require_non_empty_string(payload.get("target_id"), f"operations[{index}].target_id")
    elif op_type == "update_exit":
        _require_non_empty_string(payload.get("exit_id"), f"operations[{index}].exit_id")
        payload["fields"] = _validate_exit_update_fields(payload.get("fields"), index)
    elif op_type == "delete_exit":
        _require_non_empty_string(payload.get("source_id"), f"operations[{index}].source_id")
        _require_non_empty_string(payload.get("direction"), f"operations[{index}].direction")
    elif op_type == "move_object":
        _require_non_empty_string(payload.get("object_id"), f"operations[{index}].object_id")
        _require_non_empty_string(payload.get("destination_id"), f"operations[{index}].destination_id")
        _require_non_empty_string(payload.get("relation"), f"operations[{index}].relation")
    elif op_type == "spawn_template":
        _require_non_empty_string(payload.get("template_id"), f"operations[{index}].template_id")
        _require_non_empty_string(str(payload.get("location_id", "")), f"operations[{index}].location_id")
    elif op_type == "delete_object":
        _require_non_empty_string(payload.get("object_id"), f"operations[{index}].object_id")

    return payload


def _require_room(room_id: str, label: str, zone_id: str | None = None):
    room = room_service.get_room(room_id, zone_id=zone_id)
    if room is None:
        zone_label = f" in zone '{zone_id}'" if str(zone_id or "").strip() else ""
        raise ValueError(f"Unknown {label}: {room_id}{zone_label}")
    return room


def _get_exit_target_builder_id(source_id: str, direction: str) -> str | None:
    source = room_service.get_room(source_id)
    if source is None:
        return None
    existing = exit_service.find_exit(source, direction)
    destination = getattr(existing, "destination", None) if existing is not None else None
    builder_id = str(getattr(getattr(destination, "db", None), "builder_id", "") or "").strip()
    return builder_id or None


def _get_exit_target_zone_id(source_id: str, direction: str) -> str | None:
    source = room_service.get_room(source_id)
    if source is None:
        return None
    existing = exit_service.find_exit(source, direction)
    destination = getattr(existing, "destination", None) if existing is not None else None
    zone_id = str(getattr(getattr(destination, "db", None), "zone_id", "") or getattr(getattr(destination, "db", None), "zone", "") or getattr(getattr(destination, "db", None), "area_id", "") or "").strip()
    return zone_id or None


def _build_validation_state() -> dict:
    return {
        "created_rooms": set(),
        "deleted_rooms": set(),
        "exit_overrides": {},
        "updated_exit_directions": {},
    }


def _room_exists_in_state(room_id: str, state: dict) -> bool:
    normalized_room_id = str(room_id or "").strip()
    if normalized_room_id in state["deleted_rooms"]:
        return False
    if normalized_room_id in state["created_rooms"]:
        return True
    return room_service.get_room(normalized_room_id) is not None


def _get_effective_exit_target_id(source_id: str, direction: str, state: dict) -> str | None:
    key = (str(source_id or "").strip(), _normalize_direction(direction))
    if key in state["exit_overrides"]:
        return state["exit_overrides"][key]
    return _get_exit_target_builder_id(key[0], key[1])


def _room_has_incoming_exits_in_state(room_id: str, state: dict) -> bool:
    normalized_room_id = str(room_id or "").strip()
    room = room_service.get_room(normalized_room_id)
    current_keys = set()

    if room is not None:
        for candidate in list(ObjectDB.objects.filter(db_destination=room, db_typeclass_path="typeclasses.exits.Exit")):
            source = getattr(candidate, "location", None)
            source_builder_id = str(getattr(getattr(source, "db", None), "builder_id", "") or "").strip()
            direction = str(getattr(candidate, "key", "") or "").strip().lower()
            if source_builder_id and direction:
                current_keys.add((source_builder_id, direction))

    for key in current_keys:
        if key in state["exit_overrides"]:
            if state["exit_overrides"][key] == normalized_room_id:
                return True
            continue
        if _get_exit_target_builder_id(key[0], key[1]) == normalized_room_id:
            return True

    for key, target_id in state["exit_overrides"].items():
        if key in current_keys:
            continue
        if target_id == normalized_room_id:
            return True

    return False


def _apply_validation_state(op: dict, state: dict) -> None:
    op_type = str(op.get("op") or "")
    if op_type == "create_room":
        state["created_rooms"].add(str(op["room"]["id"]))
        state["deleted_rooms"].discard(str(op["room"]["id"]))
    elif op_type == "delete_room":
        state["deleted_rooms"].add(str(op["room_id"]))
        state["created_rooms"].discard(str(op["room_id"]))
    elif op_type == "set_exit":
        key = (str(op["source_id"]), _normalize_direction(op["direction"]))
        state["exit_overrides"][key] = str(op["target_id"])
    elif op_type == "update_exit":
        existing = exit_service.get_exit_by_id(op["exit_id"])
        if existing is None:
            return
        source = getattr(existing, "location", None)
        source_id = str(getattr(getattr(source, "db", None), "builder_id", "") or "").strip()
        current_direction = str(getattr(existing, "key", "") or "").strip().lower()
        new_direction = _normalize_direction(op["fields"].get("direction", current_direction))
        if source_id and current_direction:
            state["exit_overrides"][(source_id, current_direction)] = None
        if source_id and "target_id" in op["fields"]:
            state["exit_overrides"][(source_id, new_direction)] = str(op["fields"]["target_id"])
        state["updated_exit_directions"][str(op["exit_id"])] = new_direction
    elif op_type == "delete_exit":
        key = (str(op["source_id"]), _normalize_direction(op["direction"]))
        state["exit_overrides"][key] = None


def validate_operation(op: dict, index: int, state: dict | None = None) -> dict:
    _require_builder_runtime()
    payload = _validate_operation_structure(op, index)
    active_state = state if state is not None else _build_validation_state()
    op_type = str(payload.get("op") or "")

    if op_type == "update_room":
        if not _room_exists_in_state(payload["room_id"], active_state):
            raise ValueError(f"Unknown room_id: {payload['room_id']}")
    elif op_type == "update_object":
        instance_service.require_instance(payload["object_id"])
    elif op_type == "delete_room":
        if not _room_exists_in_state(payload["room_id"], active_state):
            raise ValueError(f"Unknown room_id: {payload['room_id']}")
        if _room_has_incoming_exits_in_state(payload["room_id"], active_state):
            raise ValueError("Room deletion is blocked while incoming exits still reference the room.")
    elif op_type == "set_exit":
        if not _room_exists_in_state(payload["source_id"], active_state):
            raise ValueError(f"Unknown source_id: {payload['source_id']}")
        if room_service.get_room(payload["target_id"], zone_id=payload.get("target_zone_id")) is None:
            raise ValueError(f"Unknown target_id: {payload['target_id']}")
    elif op_type == "update_exit":
        existing = _require_exit(payload["exit_id"], "exit_id")
        source = getattr(existing, "location", None)
        source_id = str(getattr(getattr(source, "db", None), "builder_id", "") or "").strip()
        if not source_id:
            raise ValueError("Exit source room is missing a builder_id.")
        fields = dict(payload.get("fields") or {})
        if "target_id" in fields and room_service.get_room(fields["target_id"], zone_id=fields.get("target_zone_id")) is None:
            raise ValueError(f"Unknown target_id: {fields['target_id']}")
        if "direction" in fields:
            new_direction = _normalize_direction(fields["direction"])
            direction_owner = exit_service.find_exit(source, new_direction)
            if direction_owner is not None and str(getattr(direction_owner, "id", "")) != str(getattr(existing, "id", "")):
                raise ValueError("Exit direction already exists on the source room.")
    elif op_type == "delete_exit":
        if not _room_exists_in_state(payload["source_id"], active_state):
            raise ValueError(f"Unknown source_id: {payload['source_id']}")
        if _get_effective_exit_target_id(payload["source_id"], payload["direction"], active_state) is None:
            raise ValueError("Exit not found.")
    elif op_type == "move_object":
        instance_service.require_instance(payload["object_id"])
        instance_service.require_instance(payload["destination_id"])
        placement_service._validate_relation_for_type(
            placement_service._detect_placement_type(instance_service.require_instance(payload["destination_id"])),
            payload["relation"],
        )
    elif op_type == "spawn_template":
        template_service.require_template(payload["template_id"])
        instance_service.require_instance(payload["location_id"])
    elif op_type == "delete_object":
        instance = instance_service.require_instance(payload["object_id"])
        if str(getattr(instance, "typeclass_path", "") or "") == "typeclasses.rooms.Room":
            raise ValueError("delete_object cannot target a room.")

    _apply_validation_state(payload, active_state)
    return payload


def _build_conflict(type_name: str, operation_index: int, operation_id: str, message: str) -> dict:
    return {
        "type": str(type_name),
        "operation_index": int(operation_index),
        "operation_id": str(operation_id),
        "message": str(message),
    }


def detect_conflicts(diff: dict) -> list[dict]:
    _require_builder_runtime()
    payload = _validate_top_level(diff)
    conflicts: list[dict] = []
    created_rooms: dict[str, tuple[int, str]] = {}
    deleted_rooms: dict[str, tuple[int, str]] = {}
    exit_targets: dict[tuple[str, str], tuple[str, int, str]] = {}
    updated_exit_ids: dict[str, tuple[int, str]] = {}

    for index, op in enumerate(payload["operations"]):
        validated = _validate_operation_structure(op, index)
        op_id = _normalize_operation_id(validated, index)
        op_type = str(validated.get("op") or "")

        if op_type == "create_room":
            room_id = str(validated["room"]["id"])
            if room_id in created_rooms:
                conflicts.append(_build_conflict("duplicate_room_create", index, op_id, f"Duplicate create_room for room_id '{room_id}'."))
            created_rooms.setdefault(room_id, (index, op_id))
        elif op_type == "update_room":
            room_id = str(validated["room_id"])
            if room_id in deleted_rooms:
                conflicts.append(_build_conflict("update_after_delete", index, op_id, f"update_room conflicts with earlier delete_room for room_id '{room_id}'."))
        elif op_type == "delete_room":
            room_id = str(validated["room_id"])
            if room_id in created_rooms:
                conflicts.append(_build_conflict("create_delete_contradiction", index, op_id, f"delete_room conflicts with create_room for room_id '{room_id}' in the same diff."))
            deleted_rooms[room_id] = (index, op_id)
        elif op_type == "set_exit":
            key = (str(validated["source_id"]), _normalize_direction(validated["direction"]))
            target_id = str(validated["target_id"])
            previous = exit_targets.get(key)
            if previous is not None and previous[0] != target_id:
                conflicts.append(_build_conflict("conflicting_exit_assignment", index, op_id, f"set_exit conflicts for source_id '{key[0]}' direction '{key[1]}'."))
            exit_targets[key] = (target_id, index, op_id)
        elif op_type == "update_exit":
            exit_id = str(validated["exit_id"])
            if exit_id in updated_exit_ids:
                conflicts.append(_build_conflict("duplicate_exit_update", index, op_id, f"Multiple update_exit operations target exit_id '{exit_id}' in the same diff."))
            updated_exit_ids[exit_id] = (index, op_id)

    return conflicts


def validate_diff(diff: dict) -> dict:
    _require_builder_runtime()
    payload = _validate_top_level(diff)
    conflicts = detect_conflicts(payload)
    if conflicts:
        first = conflicts[0]
        failed_index = int(first["operation_index"])
        failed_operation = payload["operations"][failed_index] if failed_index < len(payload["operations"]) else None
        raise DiffApplyError(
            "Diff conflicts detected.",
            failed_operation_index=failed_index,
            failed_operation_id=str(first["operation_id"]),
            failed_operation=failed_operation if isinstance(failed_operation, dict) else None,
            conflicts=conflicts,
        )

    validated_count = 0
    state = _build_validation_state()
    for index, op in enumerate(payload["operations"]):
        try:
            validate_operation(op, index, state=state)
            validated_count += 1
        except Exception as exc:
            failed_operation = op if isinstance(op, dict) else None
            raise DiffApplyError(
                f"Diff failed at operation {index}: {exc}",
                failed_operation_index=index,
                failed_operation_id=_fallback_operation_id(op, index),
                failed_operation=failed_operation,
            ) from exc

    return {"payload": payload, "validated_operations": validated_count}


def _ensure_no_incoming_exits(room) -> None:
    room_id = getattr(room, "id", None)
    if room_id is None:
        raise ValueError("room is required.")

    incoming = list(ObjectDB.objects.filter(db_destination=room, db_typeclass_path="typeclasses.exits.Exit").exclude(db_location=room))
    if incoming:
        raise ValueError("Room deletion is blocked while incoming exits still reference the room.")


def _apply_create_room(op: dict, area_id: str) -> None:
    room_payload = dict(op["room"])
    room_payload["area_id"] = area_id
    room_payload["region"] = area_id
    room_service.create_room(room_payload)


def _apply_update_room(op: dict) -> None:
    room = _require_room(op["room_id"], "room_id")
    room_service.update_room(room, op["updates"])


def _apply_update_object(op: dict) -> None:
    instance_service.update_instance_by_id(op["object_id"], op["fields"])


def _apply_delete_room(op: dict) -> None:
    room = _require_room(op["room_id"], "room_id")
    _ensure_no_incoming_exits(room)
    delete_instance(room, allow_room=True)


def _apply_set_exit(op: dict) -> None:
    source = _require_room(op["source_id"], "source_id")
    target = _require_room(op["target_id"], "target_id", zone_id=op.get("target_zone_id"))
    exit_service.ensure_exit(source, op["direction"], target)


def _apply_update_exit(op: dict) -> None:
    fields = dict(op.get("fields") or {})
    update_fields = {}
    if "direction" in fields:
        update_fields["direction"] = fields["direction"]
    if "target_id" in fields:
        update_fields["target"] = _require_room(fields["target_id"], "fields.target_id", zone_id=fields.get("target_zone_id"))
    if "label" in fields:
        update_fields["label"] = fields.get("label")
    if "aliases" in fields:
        update_fields["aliases"] = list(fields.get("aliases") or [])
    exit_service.update_exit(op["exit_id"], **update_fields)


def _apply_delete_exit(op: dict) -> None:
    source = _require_room(op["source_id"], "source_id")
    exit_service.delete_exit(source, op["direction"])


def _apply_move_object(op: dict) -> None:
    placement_service.move_instance(op["object_id"], op["destination_id"], relation=op["relation"])


def _apply_spawn_template(op: dict) -> None:
    location = instance_service.require_instance(op["location_id"])
    spawn_service.spawn_from_template_result(op["template_id"], location)


def _apply_delete_object(op: dict) -> None:
    instance_service.delete_instance_by_id(op["object_id"])


def apply_operation(op: dict, index: int, area_id: str, preview: bool = False, group_id: str | None = None):
    _require_builder_runtime()
    payload = _validate_operation_structure(op, index)
    op_id = _normalize_operation_id(payload, index)
    op_type = payload.get("op")

    if op_type == "create_room":
        _apply_create_room(payload, area_id)
    elif op_type == "update_room":
        _apply_update_room(payload)
    elif op_type == "update_object":
        _apply_update_object(payload)
    elif op_type == "delete_room":
        _apply_delete_room(payload)
    elif op_type == "set_exit":
        _apply_set_exit(payload)
    elif op_type == "update_exit":
        _apply_update_exit(payload)
    elif op_type == "delete_exit":
        _apply_delete_exit(payload)
    elif op_type == "move_object":
        _apply_move_object(payload)
    elif op_type == "spawn_template":
        _apply_spawn_template(payload)
    elif op_type == "delete_object":
        _apply_delete_object(payload)
    else:
        raise ValueError(f"Unknown operation: {op_type}")

    if not preview:
        details = {"operation_id": op_id, "operation": op_type, "payload": payload}
        normalized_group_id = _normalize_optional_string(group_id)
        if normalized_group_id is not None:
            details["group_id"] = normalized_group_id
        log_audit_event("diff_apply", 0, details)


def apply_diff(
    diff: dict,
    preview: bool = False,
    history_entry_type: str = "apply",
    session_id: str | None = None,
    group_id: str | None = None,
    username: str | None = None,
) -> dict:
    _require_builder_runtime()
    validation = validate_diff(diff)
    payload = validation["payload"]
    operation_ids = _extract_operation_ids(payload["operations"])
    normalized_session_id = _normalize_optional_string(session_id)
    normalized_group_id = _normalize_optional_string(group_id)
    normalized_username = _normalize_optional_string(username)

    if bool(preview):
        return {
            "applied": 0,
            "preview": True,
            "validated_operations": int(validation["validated_operations"]),
            "operation_ids": operation_ids,
        }

    applied_count = 0
    operations = payload["operations"]
    area_id = str(payload["area_id"])

    import world.builder.services.undo_service as undo_service

    pre_states: list[dict | None] = []
    undo_available = True
    for current_index, op in enumerate(operations):
        if undo_service.is_operation_invertible(op):
            pre_states.append(undo_service.capture_pre_state(op))
        else:
            pre_states.append(None)
            undo_available = False
        apply_operation(op, current_index, area_id, preview=False, group_id=normalized_group_id)
        applied_count += 1

    result = {"applied": applied_count, "undo_available": bool(undo_available)}
    if undo_available:
        result["undo_diff"] = undo_service.build_inverse_diff(payload, pre_states=pre_states)

    diff_history_service.append_history_entry(
        {
            "area_id": area_id,
            "type": str(history_entry_type or "apply").strip().lower() or "apply",
            "diff": deepcopy(payload),
            "result": deepcopy(result),
            "undo_diff": deepcopy(result.get("undo_diff")) if result.get("undo_diff") is not None else None,
            "operation_ids": list(operation_ids),
            "session_id": normalized_session_id,
            "group_id": normalized_group_id,
            "user": normalized_username,
        }
    )
    return result