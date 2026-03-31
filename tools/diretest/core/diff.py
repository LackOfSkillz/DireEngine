"""Canonical snapshot diff support for DireTest."""

from __future__ import annotations


DIFF_SCHEMA = {
    "character_changes": dict,
    "room_changes": dict,
    "inventory_changes": {
        "added": list,
        "removed": list,
    },
    "equipment_changes": {
        "added": list,
        "removed": list,
    },
    "combat_changes": dict,
    "attribute_changes": dict,
    "object_delta_changes": dict,
}


def _snapshot_entry(snapshot_ref):
    if isinstance(snapshot_ref, dict) and "data" in snapshot_ref:
        return snapshot_ref
    if isinstance(snapshot_ref, dict):
        return {"label": str(snapshot_ref.get("label", "") or ""), "data": snapshot_ref}
    raise TypeError("Snapshot reference must be a snapshot entry or snapshot data dict.")


def _object_keys(entries):
    keys = set()
    for entry in list(entries or []):
        if isinstance(entry, dict):
            key = str(entry.get("key", "") or "")
        else:
            key = str(entry or "")
        if key:
            keys.add(key)
    return keys


def _dict_delta(before, after):
    before_map = dict(before or {})
    after_map = dict(after or {})
    changed = {}
    for key in sorted(set(before_map) | set(after_map)):
        if before_map.get(key) != after_map.get(key):
            changed[key] = {
                "before": before_map.get(key),
                "after": after_map.get(key),
            }
    return changed


def diff_snapshots(before: dict, after: dict) -> dict:
    before_entry = _snapshot_entry(before)
    after_entry = _snapshot_entry(after)
    before_data = dict(before_entry.get("data", {}) or {})
    after_data = dict(after_entry.get("data", {}) or {})
    before_character = dict(before_data.get("character", {}) or {})
    after_character = dict(after_data.get("character", {}) or {})
    before_room = dict(before_data.get("room", {}) or {})
    after_room = dict(after_data.get("room", {}) or {})
    before_combat = dict(before_data.get("combat", {}) or {})
    after_combat = dict(after_data.get("combat", {}) or {})
    before_target_summary = dict(before_combat.get("target_summary", {}) or {})
    after_target_summary = dict(after_combat.get("target_summary", {}) or {})

    before_inventory = _object_keys(before_data.get("inventory", []))
    after_inventory = _object_keys(after_data.get("inventory", []))
    before_equipment = _object_keys(before_data.get("equipment", []))
    after_equipment = _object_keys(after_data.get("equipment", []))
    before_room_contents = _object_keys(before_room.get("contents", []))
    after_room_contents = _object_keys(after_room.get("contents", []))

    after_created = _object_keys((after_data.get("object_deltas", {}) or {}).get("created", []))
    after_deleted = _object_keys((after_data.get("object_deltas", {}) or {}).get("deleted", []))

    before_hp = int(before_character.get("hp", 0) or 0)
    after_hp = int(after_character.get("hp", 0) or 0)
    before_coins = int(before_character.get("coins", 0) or 0)
    after_coins = int(after_character.get("coins", 0) or 0)
    before_bank = int(before_character.get("bank_coins", 0) or 0)
    after_bank = int(after_character.get("bank_coins", 0) or 0)
    before_life = str(before_character.get("life_state", "") or "")
    after_life = str(after_character.get("life_state", "") or "")
    before_is_dead = bool(before_character.get("is_dead", False))
    after_is_dead = bool(after_character.get("is_dead", False))
    before_target_hp = int(before_target_summary.get("hp", 0) or 0) if before_target_summary else None
    after_target_hp = int(after_target_summary.get("hp", 0) or 0) if after_target_summary else None

    return {
        "character_changes": {
            "before_label": str(before_entry.get("label", "") or ""),
            "after_label": str(after_entry.get("label", "") or ""),
            "location_before": str(before_character.get("location", "") or "") or None,
            "location_after": str(after_character.get("location", "") or "") or None,
            "hp_before": before_hp,
            "hp_after": after_hp,
            "hp_delta": after_hp - before_hp,
            "coins_before": before_coins,
            "coins_after": after_coins,
            "coins_delta": after_coins - before_coins,
            "bank_coins_before": before_bank,
            "bank_coins_after": after_bank,
            "bank_coins_delta": after_bank - before_bank,
            "life_state_before": before_life or None,
            "life_state_after": after_life or None,
            "is_dead_before": before_is_dead,
            "is_dead_after": after_is_dead,
            "died": (before_life != "DEAD") and (after_life == "DEAD"),
            "revived": (before_life == "DEAD") and (after_life == "ALIVE"),
        },
        "room_changes": {
            "room_before": str(before_room.get("key", "") or "") or None,
            "room_after": str(after_room.get("key", "") or "") or None,
            "changed": str(before_room.get("key", "") or "") != str(after_room.get("key", "") or "")
            or str(before_character.get("location", "") or "") != str(after_character.get("location", "") or ""),
            "contents_added": sorted(after_room_contents - before_room_contents),
            "contents_removed": sorted(before_room_contents - after_room_contents),
        },
        "inventory_changes": {
            "added": sorted(after_inventory - before_inventory),
            "removed": sorted(before_inventory - after_inventory),
        },
        "equipment_changes": {
            "added": sorted(after_equipment - before_equipment),
            "removed": sorted(before_equipment - after_equipment),
        },
        "combat_changes": {
            "target_before": str(before_combat.get("target", "") or "") or None,
            "target_after": str(after_combat.get("target", "") or "") or None,
            "target_assigned": not bool(before_combat.get("target")) and bool(after_combat.get("target")),
            "target_cleared": bool(before_combat.get("target")) and not bool(after_combat.get("target")),
            "in_combat_before": bool(before_combat.get("in_combat", False)),
            "in_combat_after": bool(after_combat.get("in_combat", False)),
            "entered_combat": (not bool(before_combat.get("in_combat", False))) and bool(after_combat.get("in_combat", False)),
            "exited_combat": bool(before_combat.get("in_combat", False)) and (not bool(after_combat.get("in_combat", False))),
            "roundtime_before": float(before_combat.get("roundtime", 0.0) or 0.0),
            "roundtime_after": float(after_combat.get("roundtime", 0.0) or 0.0),
            "target_hp_before": before_target_hp,
            "target_hp_after": after_target_hp,
            "target_hp_delta": None if before_target_hp is None or after_target_hp is None else after_target_hp - before_target_hp,
            "target_range_before": str(before_target_summary.get("range", "") or "") if before_target_summary else None,
            "target_range_after": str(after_target_summary.get("range", "") or "") if after_target_summary else None,
            "range_changed": (str(before_target_summary.get("range", "") or "") if before_target_summary else None)
            != (str(after_target_summary.get("range", "") or "") if after_target_summary else None),
        },
        "attribute_changes": {
            "changed": _dict_delta(before_data.get("attributes", {}), after_data.get("attributes", {})),
        },
        "object_delta_changes": {
            "created": sorted(after_created),
            "deleted": sorted(after_deleted),
        },
    }