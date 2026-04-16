from __future__ import annotations

import logging


logger = logging.getLogger(__name__)
MAX_DEPTH = 10
PLACEMENT_TYPES = {"room", "container", "surface"}
PLACEMENT_RELATIONS = {"in", "on"}
PLACEMENT_AVAILABLE = False

try:
    from evennia.utils.search import search_object
    from typeclasses.rooms import Room

    from .audit_service import log_audit_event
except ImportError:  # pragma: no cover - optional builder dependency guard
    search_object = None
    Room = None
    log_audit_event = None
else:
    PLACEMENT_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not PLACEMENT_AVAILABLE:
        raise RuntimeError("Builder placement service is unavailable because the Evennia runtime could not be imported.")


def _require_object(obj, label: str):
    if obj is None:
        raise ValueError(f"{label} is required.")
    if getattr(obj, "id", None) is None:
        raise ValueError(f"{label} must be a valid live object.")
    return obj


def _lookup_object(obj_id, label: str):
    normalized_obj_id = str(obj_id or "").strip()
    if not normalized_obj_id:
        raise ValueError(f"{label} is required.")

    lookup_value = normalized_obj_id if normalized_obj_id.startswith("#") else f"#{normalized_obj_id}"
    matches = search_object(lookup_value)
    obj = matches[0] if matches else None
    if obj is None:
        raise ValueError(f"Unknown {label}: {obj_id}")
    return obj


def is_circular(obj, destination) -> bool:
    _require_builder_runtime()
    current = _require_object(destination, "destination")
    target_id = getattr(obj, "id", None)
    depth = 0
    while current is not None:
        if getattr(current, "id", None) == target_id:
            return True
        depth += 1
        if depth > MAX_DEPTH:
            raise ValueError(f"Placement depth exceeds maximum of {MAX_DEPTH}.")
        current = getattr(current, "location", None)
    return False


def get_placement_info(obj):
    _require_builder_runtime()
    target_obj = _require_object(obj, "obj")
    placement_type = str(getattr(getattr(target_obj, "db", None), "placement_type", "") or "room")
    placement_relation = str(getattr(getattr(target_obj, "db", None), "placement_relation", "") or "in")
    location = getattr(target_obj, "location", None)
    return {
        "object_id": getattr(target_obj, "id", None),
        "location_id": getattr(location, "id", None) if location is not None else None,
        "placement_type": placement_type,
        "placement_relation": placement_relation,
    }


def _detect_placement_type(destination) -> str:
    target_destination = _require_object(destination, "destination")
    if bool(getattr(getattr(target_destination, "db", None), "is_surface", False)):
        return "surface"
    if isinstance(target_destination, Room):
        return "room"
    return "container"


def _default_relation_for_type(placement_type: str) -> str:
    return "on" if placement_type == "surface" else "in"


def _validate_relation_for_type(placement_type: str, relation: str) -> str:
    normalized_type = str(placement_type or "").strip().lower()
    normalized_relation = str(relation or "").strip().lower()

    if normalized_type not in PLACEMENT_TYPES:
        raise ValueError(f"Unsupported placement_type: {placement_type}")
    if normalized_relation not in PLACEMENT_RELATIONS:
        raise ValueError("relation must be one of: in, on")
    if normalized_relation == "on" and normalized_type != "surface":
        raise ValueError("Relation 'on' requires a surface destination.")
    if normalized_relation == "in" and normalized_type == "surface":
        raise ValueError("Relation 'in' is invalid for a surface destination.")
    return normalized_relation


def move_to_location(obj, destination):
    _require_builder_runtime()
    target_obj = _require_object(obj, "obj")
    target_destination = _require_object(destination, "destination")

    if getattr(target_obj, "id", None) == getattr(target_destination, "id", None):
        raise ValueError("Object cannot be moved into itself.")
    if is_circular(target_obj, target_destination):
        raise ValueError("Circular containment detected.")

    target_obj.location = target_destination
    if getattr(target_obj, "location", None) != target_destination:
        raise ValueError("Object move failed.")

    placement_type = _detect_placement_type(target_destination)
    placement_relation = _default_relation_for_type(placement_type)
    target_obj.db.placement_type = placement_type
    target_obj.db.placement_relation = placement_relation

    logger.info(
        "Move: obj=%s dest=%s type=%s relation=%s",
        getattr(target_obj, "id", None),
        getattr(target_destination, "id", None),
        placement_type,
        placement_relation,
    )
    log_audit_event(
        "move",
        getattr(target_obj, "id", 0),
        {
            "destination": getattr(target_destination, "id", None),
            "placement_type": placement_type,
            "relation": placement_relation,
        },
    )
    return {
        "object_id": getattr(target_obj, "id", None),
        "new_location_id": getattr(target_destination, "id", None),
        "placement_type": placement_type,
        "placement_relation": placement_relation,
    }


def move_with_relation(obj, destination, relation: str = "in"):
    _require_builder_runtime()
    target_obj = _require_object(obj, "obj")
    target_destination = _require_object(destination, "destination")
    placement_type = _detect_placement_type(target_destination)
    normalized_relation = _validate_relation_for_type(placement_type, relation)

    result = move_to_location(target_obj, target_destination)
    target_obj.db.placement_relation = normalized_relation
    result["placement_relation"] = normalized_relation
    return result


def move_instance(obj_id, destination_id, relation: str = "in"):
    _require_builder_runtime()
    obj = _lookup_object(obj_id, "object_id")
    destination = _lookup_object(destination_id, "destination_id")
    return move_with_relation(obj, destination, relation=relation)


def move_to_room(obj, room):
    return move_to_location(obj, room)


def move_to_container(obj, container):
    return move_to_location(obj, container)