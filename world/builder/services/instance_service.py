from __future__ import annotations

import logging
from collections.abc import Mapping


logger = logging.getLogger(__name__)
INSTANCE_AVAILABLE = False

try:
    from evennia.utils.search import search_object
    from typeclasses.rooms import Room

    from .audit_service import log_audit_event
except ImportError:  # pragma: no cover - optional builder dependency guard
    search_object = None
    Room = None
    log_audit_event = None
else:
    INSTANCE_AVAILABLE = True


def _require_builder_runtime() -> None:
    if not INSTANCE_AVAILABLE:
        raise RuntimeError("Builder instance service is unavailable because the Evennia runtime could not be imported.")


def get_instance(obj_id):
    _require_builder_runtime()
    normalized_obj_id = str(obj_id or "").strip()
    if not normalized_obj_id:
        raise ValueError("object_id is required.")

    lookup_value = normalized_obj_id if normalized_obj_id.startswith("#") else f"#{normalized_obj_id}"
    matches = search_object(lookup_value)
    return matches[0] if matches else None


def require_instance(obj_id):
    obj = get_instance(obj_id)
    if obj is None:
        raise ValueError(f"Unknown object_id: {obj_id}")
    return obj


def _normalize_update_fields(fields: dict) -> dict:
    if not isinstance(fields, Mapping):
        raise ValueError("fields must be a mapping.")

    allowed_fields = {"name", "description", "attributes", "flags", "item_kind", "weight", "value"}
    unknown_fields = sorted(set(fields.keys()) - allowed_fields)
    if unknown_fields:
        raise ValueError(f"Unsupported object update fields: {', '.join(unknown_fields)}")

    normalized: dict = {}
    if "name" in fields:
        name = str(fields.get("name") or "").strip()
        if not name:
            raise ValueError("name must be a non-empty string.")
        normalized["name"] = name
    if "description" in fields:
        normalized["description"] = str(fields.get("description") or "")
    if "attributes" in fields:
        raw_attributes = fields.get("attributes") or {}
        if not isinstance(raw_attributes, Mapping):
            raise ValueError("attributes must be a mapping.")
        normalized_attributes = {}
        for raw_key, raw_value in raw_attributes.items():
            attribute_name = str(raw_key or "").strip().lower()
            if not attribute_name:
                raise ValueError("attribute names must be non-empty strings.")
            if not isinstance(raw_value, (int, float)):
                raise ValueError(f"attributes.{attribute_name} must be numeric.")
            normalized_attributes[attribute_name] = int(raw_value) if isinstance(raw_value, int) else float(raw_value)
        normalized["attributes"] = normalized_attributes
    if "flags" in fields:
        raw_flags = fields.get("flags") or []
        if not isinstance(raw_flags, list):
            raise ValueError("flags must be a list.")
        normalized_flags = []
        for raw_flag in raw_flags:
            flag_name = str(raw_flag or "").strip().lower()
            if not flag_name:
                continue
            if flag_name not in normalized_flags:
                normalized_flags.append(flag_name)
        normalized["flags"] = normalized_flags
    if "item_kind" in fields:
        normalized["item_kind"] = str(fields.get("item_kind") or "").strip().lower()
    if "weight" in fields:
        weight = fields.get("weight", 0.0)
        if not isinstance(weight, (int, float)):
            raise ValueError("weight must be numeric.")
        normalized["weight"] = float(weight)
    if "value" in fields:
        value = fields.get("value", 0.0)
        if not isinstance(value, (int, float)):
            raise ValueError("value must be numeric.")
        normalized["value"] = float(value)
    return normalized


def update_instance(obj, fields: dict):
    _require_builder_runtime()
    if obj is None:
        raise ValueError("obj is required.")

    normalized_fields = _normalize_update_fields(fields)
    if "name" in normalized_fields:
        obj.key = normalized_fields["name"]
    if "description" in normalized_fields:
        obj.db.desc = normalized_fields["description"]
    if "attributes" in normalized_fields:
        obj.db.builder_attributes = dict(normalized_fields["attributes"])
    if "flags" in normalized_fields:
        flags = list(normalized_fields["flags"])
        obj.db.builder_flags = flags
        obj.db.aggressive = "aggressive" in flags
        obj.db.patrol = "patrol" in flags
    if "item_kind" in normalized_fields:
        item_kind = str(normalized_fields["item_kind"] or "").strip().lower()
        obj.db.builder_item_kind = item_kind
        obj.db.is_container = item_kind == "container"
    if "weight" in normalized_fields:
        obj.db.weight = float(normalized_fields["weight"])
    if "value" in normalized_fields:
        obj.db.value = float(normalized_fields["value"])

    obj.save()
    obj_id = getattr(obj, "id", None)
    logger.info("Updated object %s", obj_id)
    log_audit_event("update", obj_id or 0, {"updated_id": obj_id, "fields": normalized_fields})
    return {
        "object_id": obj_id,
        "fields": normalized_fields,
    }


def update_instance_by_id(obj_id, fields: dict):
    obj = require_instance(obj_id)
    return update_instance(obj, fields)


def delete_instance(obj, allow_room: bool = False):
    _require_builder_runtime()
    if obj is None:
        raise ValueError("obj is required.")
    obj_id = getattr(obj, "id", None)
    if obj_id is None:
        raise ValueError("Object is already deleted.")
    if not allow_room and (isinstance(obj, Room) or str(getattr(obj, "typeclass_path", "") or "") == "typeclasses.rooms.Room"):
        raise ValueError("Room deletion is not allowed.")

    try:
        obj.delete()
    except Exception as exc:
        raise ValueError(f"Delete failed: {exc}") from exc
    logger.info("Deleted object %s", obj_id)
    log_audit_event("delete", obj_id, {"deleted_id": obj_id})
    return {"deleted_id": obj_id}


def delete_instance_by_id(obj_id, allow_room: bool = False):
    obj = require_instance(obj_id)
    return delete_instance(obj, allow_room=allow_room)