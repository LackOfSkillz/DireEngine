"""Scenario execution context for DireTest."""

from __future__ import annotations

import time

from .invariants import INVARIANTS, run_invariant
from .snapshot import capture_snapshot


class DireTestContext:
    def __init__(self, harness=None, mode="direct", character=None, room=None, invariants=None, auto_snapshot=False):
        self.harness = harness
        self.mode = str(mode)
        self.character = character
        self.room = room or getattr(character, "location", None)
        self.invariants = dict(INVARIANTS)
        self.invariants.update(dict(invariants or {}))
        self.auto_snapshot = bool(auto_snapshot)
        self.command_log = []
        self.output_log = []
        self.snapshots = []
        self.log_messages = []
        self.invariant_results = []
        self._previous_object_records = {}

    def _coerce_snapshot_entry(self, snapshot_ref):
        if isinstance(snapshot_ref, int):
            return self.snapshots[snapshot_ref]
        if isinstance(snapshot_ref, dict) and "data" in snapshot_ref:
            return snapshot_ref
        raise TypeError("Snapshot reference must be an index or a snapshot entry.")

    def _snapshot_inventory_keys(self, snapshot_data):
        inventory = list(snapshot_data.get("inventory", []) or [])
        return {
            str(entry.get("key", "") or "")
            for entry in inventory
            if isinstance(entry, dict) and str(entry.get("key", "") or "")
        }

    def _snapshot_room_contents(self, snapshot_data):
        room = dict(snapshot_data.get("room", {}) or {})
        return {str(entry or "") for entry in list(room.get("contents", []) or []) if str(entry or "")}

    def diff_snapshots(self, before, after):
        before_entry = self._coerce_snapshot_entry(before)
        after_entry = self._coerce_snapshot_entry(after)
        before_data = dict(before_entry.get("data", {}) or {})
        after_data = dict(after_entry.get("data", {}) or {})
        before_character = dict(before_data.get("character", {}) or {})
        after_character = dict(after_data.get("character", {}) or {})

        before_inventory = self._snapshot_inventory_keys(before_data)
        after_inventory = self._snapshot_inventory_keys(after_data)
        before_room_contents = self._snapshot_room_contents(before_data)
        after_room_contents = self._snapshot_room_contents(after_data)
        before_room = str((before_data.get("room", {}) or {}).get("key", "") or "")
        after_room = str((after_data.get("room", {}) or {}).get("key", "") or "")
        before_location = str(before_character.get("location", "") or "")
        after_location = str(after_character.get("location", "") or "")
        before_character_hp = int(before_character.get("hp", 0) or 0)
        after_character_hp = int(after_character.get("hp", 0) or 0)
        before_character_coins = int(before_character.get("coins", 0) or 0)
        after_character_coins = int(after_character.get("coins", 0) or 0)
        before_bank_coins = int(before_character.get("bank_coins", 0) or 0)
        after_bank_coins = int(after_character.get("bank_coins", 0) or 0)
        before_life_state = str(before_character.get("life_state", "") or "")
        after_life_state = str(after_character.get("life_state", "") or "")
        before_is_dead = bool(before_character.get("is_dead", False))
        after_is_dead = bool(after_character.get("is_dead", False))
        before_combat = dict(before_data.get("combat", {}) or {})
        after_combat = dict(after_data.get("combat", {}) or {})
        before_target_summary = dict(before_combat.get("target_summary", {}) or {})
        after_target_summary = dict(after_combat.get("target_summary", {}) or {})
        before_target = str(before_combat.get("target", "") or "")
        after_target = str(after_combat.get("target", "") or "")
        before_in_combat = bool(before_combat.get("in_combat", False))
        after_in_combat = bool(after_combat.get("in_combat", False))
        before_roundtime = float(before_combat.get("roundtime", 0.0) or 0.0)
        after_roundtime = float(after_combat.get("roundtime", 0.0) or 0.0)
        before_target_hp = int(before_target_summary.get("hp", 0) or 0) if before_target_summary else None
        after_target_hp = int(after_target_summary.get("hp", 0) or 0) if after_target_summary else None
        before_target_range = str(before_target_summary.get("range", "") or "") if before_target_summary else None
        after_target_range = str(after_target_summary.get("range", "") or "") if after_target_summary else None
        after_created = list((((after_data.get("object_deltas", {}) or {}).get("created", []) or [])))
        after_deleted = list((((after_data.get("object_deltas", {}) or {}).get("deleted", []) or [])))

        return {
            "before_label": str(before_entry.get("label", "") or ""),
            "after_label": str(after_entry.get("label", "") or ""),
            "room_before": before_room,
            "room_after": after_room,
            "character_location_before": before_location,
            "character_location_after": after_location,
            "character_hp_before": before_character_hp,
            "character_hp_after": after_character_hp,
            "character_hp_delta": after_character_hp - before_character_hp,
            "character_coins_before": before_character_coins,
            "character_coins_after": after_character_coins,
            "character_coins_delta": after_character_coins - before_character_coins,
            "bank_coins_before": before_bank_coins,
            "bank_coins_after": after_bank_coins,
            "bank_coins_delta": after_bank_coins - before_bank_coins,
            "life_state_before": before_life_state or None,
            "life_state_after": after_life_state or None,
            "is_dead_before": before_is_dead,
            "is_dead_after": after_is_dead,
            "died": (before_life_state != "DEAD") and (after_life_state == "DEAD"),
            "revived": (before_life_state == "DEAD") and (after_life_state == "ALIVE"),
            "room_changed": (before_room != after_room) or (before_location != after_location),
            "inventory_added": sorted(after_inventory - before_inventory),
            "inventory_removed": sorted(before_inventory - after_inventory),
            "room_contents_added": sorted(after_room_contents - before_room_contents),
            "room_contents_removed": sorted(before_room_contents - after_room_contents),
            "target_before": before_target or None,
            "target_after": after_target or None,
            "target_assigned": not before_target and bool(after_target),
            "target_cleared": bool(before_target) and not after_target,
            "in_combat_before": before_in_combat,
            "in_combat_after": after_in_combat,
            "entered_combat": (not before_in_combat) and after_in_combat,
            "exited_combat": before_in_combat and (not after_in_combat),
            "roundtime_before": before_roundtime,
            "roundtime_after": after_roundtime,
            "target_hp_before": before_target_hp,
            "target_hp_after": after_target_hp,
            "target_hp_delta": (None if before_target_hp is None or after_target_hp is None else after_target_hp - before_target_hp),
            "target_range_before": before_target_range,
            "target_range_after": after_target_range,
            "range_changed": before_target_range != after_target_range,
            "after_snapshot_created": [str(entry.get("key", "") or "") for entry in after_created if isinstance(entry, dict)],
            "after_snapshot_deleted": [str(entry.get("key", "") or "") for entry in after_deleted if isinstance(entry, dict)],
        }

    def _coerce_output_entries(self, payload=None, options=None, kwargs=None):
        entries = []

        if payload is not None:
            if isinstance(payload, tuple) and len(payload) == 2 and isinstance(payload[1], dict):
                payload, tuple_options = payload
                if options is None:
                    options = tuple_options
            if isinstance(payload, (list, tuple)):
                entries.append(" ".join(str(part) for part in payload if part is not None))
            else:
                entries.append(str(payload))

        if options:
            entries.append(f"OPTIONS {options}")

        for key, value in dict(kwargs or {}).items():
            if value is None:
                continue
            if key in {"from_obj", "session"}:
                continue
            entries.append(f"{key.upper()} {value}")

        return [entry for entry in entries if str(entry).strip()]

    def _capture_character_output(self):
        if not self.character:
            return None, None

        original_msg = self.character.msg
        output_entries = []

        def capture_msg(*args, **kwargs):
            payload = kwargs.get("text")
            if payload is None and args:
                payload = args[0]
            options = kwargs.get("options")
            entries = self._coerce_output_entries(payload=payload, options=options, kwargs={key: value for key, value in kwargs.items() if key not in {"text", "options"}})
            output_entries.extend(entries)
            return original_msg(*args, **kwargs)

        self.character.msg = capture_msg
        return original_msg, output_entries

    def _restore_character_output(self, original_msg, output_entries):
        if self.character and original_msg is not None:
            self.character.msg = original_msg
        if output_entries:
            self.output_log.extend(output_entries)
        return output_entries or []

    def cmd(self, command_str):
        command = str(command_str or "").strip()
        if not command:
            raise ValueError("ctx.cmd requires a non-empty command string.")
        if not self.character:
            raise ValueError("ctx.cmd requires an active test character.")

        self.command_log.append(command)
        original_msg, output_entries = self._capture_character_output()
        try:
            result = self.character.execute_cmd(command)
        except Exception as error:
            output_entries.append(f"ERROR {error}")
            raise
        finally:
            self._restore_character_output(original_msg, output_entries)

        self.room = getattr(self.character, "location", None) or self.room
        if self.auto_snapshot:
            self.snapshot(command)
        return result

    def direct(self, func, *args, **kwargs):
        function_name = getattr(func, "__name__", "callable")
        self.command_log.append(f"DIRECT {function_name}")

        original_msg, output_entries = self._capture_character_output()
        try:
            result = func(*args, **kwargs)
            output_entries.append(f"RETURN {result!r}")
        except Exception as error:
            output_entries.append(f"ERROR {error}")
            raise
        finally:
            self._restore_character_output(original_msg, output_entries)

        return result

    def snapshot(self, label):
        snapshot = capture_snapshot(self)
        snapshot["label"] = str(label)
        snapshot["snapshot_label"] = str(label)
        snapshot["timestamp"] = time.time()
        entry = {"label": str(label), "data": snapshot}
        self.snapshots.append(entry)
        return snapshot

    def get_snapshot_labels(self):
        return [str(entry.get("label", "") or "") for entry in list(self.snapshots or [])]

    def get_snapshot_by_label(self, label):
        target_label = str(label or "").strip()
        for entry in list(self.snapshots or []):
            if str(entry.get("label", "") or "") == target_label:
                return entry
        raise KeyError(f"Unknown snapshot label: {target_label}")

    def assert_invariant(self, name):
        invariant_name = str(name or "").strip()
        result = run_invariant(invariant_name, self)
        self.invariant_results.append(result)
        if not result["passed"]:
            message = result["message"] or f"DireTest invariant failed: {invariant_name}"
            raise AssertionError(message)
        return result

    def log(self, message):
        entry = str(message or "")
        self.log_messages.append(entry)
        return entry

    def get_character(self, name=None):
        if name is None:
            return self.character
        target = str(name or "").strip().lower()
        if self.character and str(getattr(self.character, "key", "") or "").lower() == target:
            return self.character
        for obj in list(getattr(getattr(self, "harness", None), "created_objects", []) or []):
            if str(getattr(obj, "key", "") or "").lower() == target:
                return obj
        return None

    def get_room(self, name=None):
        if name is None:
            return self.room or getattr(self.character, "location", None)
        target = str(name or "").strip().lower()
        room = self.get_room()
        if room and str(getattr(room, "key", "") or "").lower() == target:
            return room
        for obj in list(getattr(getattr(self, "harness", None), "created_objects", []) or []):
            if getattr(obj, "destination", None) is None and str(getattr(obj, "key", "") or "").lower() == target:
                return obj
        return None