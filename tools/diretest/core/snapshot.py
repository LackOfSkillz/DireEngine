"""Snapshot capture for DireTest scenario state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def _serialize_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_serialize_value(item) for item in value]
    return str(value)


def _object_exists(obj):
    from evennia.objects.models import ObjectDB

    object_id = int(getattr(obj, "id", 0) or 0)
    return object_id > 0 and ObjectDB.objects.filter(id=object_id).exists()


def _serialize_object(obj):
    if not obj:
        return None
    location = getattr(obj, "location", None)
    return {
        "id": int(getattr(obj, "id", 0) or 0),
        "key": str(getattr(obj, "key", "") or ""),
        "typeclass": str(getattr(obj, "typeclass_path", "") or getattr(obj, "path", "") or ""),
        "location": str(getattr(location, "key", "") or "") if location else None,
    }


def _serialize_character(character):
    if not character:
        return {}
    location = getattr(character, "location", None)
    return {
        "id": int(getattr(character, "id", 0) or 0),
        "key": str(getattr(character, "key", "") or ""),
        "location": str(getattr(location, "key", "") or "") if location else None,
        "hp": int(character.db.hp or 0),
        "max_hp": int(character.db.max_hp or 0),
        "coins": int(character.db.coins or 0),
        "bank_coins": int(character.db.bank_coins or 0),
        "life_state": str(character.db.life_state or ""),
        "is_dead": bool(character.db.is_dead),
        "states": _serialize_value(character.db.states or {}),
    }


def _serialize_room(room):
    if not room:
        return {}
    return {
        "id": int(getattr(room, "id", 0) or 0),
        "key": str(getattr(room, "key", "") or ""),
        "contents": [str(getattr(obj, "key", "") or "") for obj in list(getattr(room, "contents", []) or [])],
        "exits": [str(getattr(obj, "key", "") or "") for obj in list(getattr(room, "exits", []) or [])],
    }


def _serialize_inventory(character):
    if not character:
        return []
    inventory = []
    for item in list(getattr(character, "contents", []) or []):
        inventory.append(_serialize_object(item))
    return inventory


def _serialize_equipment(character):
    if not character or not hasattr(character, "get_worn_items"):
        return []
    return [_serialize_object(item) for item in list(character.get_worn_items() or [])]


def _serialize_combat(character):
    if not character:
        return None
    target = character.get_target() if hasattr(character, "get_target") else None
    target_summary = None
    if target:
        target_summary = {
            "id": int(getattr(target, "id", 0) or 0),
            "key": str(getattr(target, "key", "") or ""),
            "hp": int(target.db.hp or 0),
            "max_hp": int(target.db.max_hp or 0),
            "in_combat": bool(target.db.in_combat),
            "range": str(character.get_range(target) if hasattr(character, "get_range") else "melee"),
        }
    return {
        "in_combat": bool(character.db.in_combat),
        "target": str(getattr(target, "key", "") or "") if target else None,
        "target_summary": target_summary,
        "roundtime": float(character.get_remaining_roundtime() if hasattr(character, "get_remaining_roundtime") else 0.0),
    }


def _collect_tracked_records(ctx):
    records = {}
    harness = getattr(ctx, "harness", None)
    for obj in list(getattr(harness, "created_objects", []) or []):
        object_id = int(getattr(obj, "id", 0) or 0)
        if object_id <= 0 or not _object_exists(obj):
            continue
        try:
            records[object_id] = _serialize_object(obj)
        except Exception:
            continue
    return records


def _capture_object_deltas(ctx):
    current_records = _collect_tracked_records(ctx)
    previous_records = dict(getattr(ctx, "_previous_object_records", {}) or {})
    current_ids = set(current_records)
    previous_ids = set(previous_records)

    created = [current_records[object_id] for object_id in sorted(current_ids - previous_ids)]
    deleted = [previous_records[object_id] for object_id in sorted(previous_ids - current_ids)]

    ctx._previous_object_records = current_records
    return {
        "created": created,
        "deleted": deleted,
    }


def capture_snapshot(ctx) -> dict:
    character = ctx.get_character()
    room = ctx.get_room()
    attributes = _serialize_value(character.db.attributes or {}) if character else {}

    return {
        "character": _serialize_character(character),
        "room": _serialize_room(room),
        "inventory": _serialize_inventory(character),
        "equipment": _serialize_equipment(character),
        "combat": _serialize_combat(character),
        "attributes": attributes,
        "object_deltas": _capture_object_deltas(ctx),
    }