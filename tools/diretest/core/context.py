"""Scenario execution context for DireTest."""

from __future__ import annotations

import time

from .diff import diff_snapshots as build_snapshot_diff
from .invariants import INVARIANTS, run_invariant
from .metrics import capture_metric_state
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
        self.diffs = []
        self.log_messages = []
        self.invariant_results = []
        self.metrics = {"command_timings_ms": []}
        self.metric_baseline = {}
        self.failure_type = None
        self.failure_message = ""
        self.test_mode = True
        self.suppress_client_payloads = False
        self.time_offset = 0.0
        self.time_frozen = False
        self.frozen_time = None
        self._previous_object_records = {}

    def _coerce_snapshot_entry(self, snapshot_ref):
        if isinstance(snapshot_ref, int):
            return self.snapshots[snapshot_ref]
        if isinstance(snapshot_ref, dict) and "data" in snapshot_ref:
            return snapshot_ref
        raise TypeError("Snapshot reference must be an index or a snapshot entry.")

    def _ensure_metric_baseline(self):
        if self.metric_baseline:
            return self.metric_baseline
        character = self.get_character()
        if character is None:
            return {}
        self.metric_baseline = capture_metric_state(character)
        return self.metric_baseline

    def set_failure(self, failure_type, message=""):
        self.failure_type = str(failure_type or "") or None
        self.failure_message = str(message or "")
        return self.failure_type

    def diff_snapshots(self, before, after):
        return build_snapshot_diff(self._coerce_snapshot_entry(before), self._coerce_snapshot_entry(after))

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

        self._ensure_metric_baseline()
        self.command_log.append(command)
        original_msg, output_entries = self._capture_character_output()
        started = time.perf_counter()
        try:
            result = self.character.execute_cmd(command)
        except Exception as error:
            self.set_failure("command_execution_failure", str(error))
            output_entries.append(f"ERROR {error}")
            raise
        finally:
            elapsed_ms = max(0, int(round((time.perf_counter() - started) * 1000.0)))
            self.metrics.setdefault("command_timings_ms", []).append(elapsed_ms)
            self._restore_character_output(original_msg, output_entries)

        self.room = getattr(self.character, "location", None) or self.room
        if self.auto_snapshot:
            self.snapshot(command)
        return result

    def direct(self, func, *args, **kwargs):
        function_name = getattr(func, "__name__", "callable")
        self._ensure_metric_baseline()
        self.command_log.append(f"DIRECT {function_name}")

        original_msg, output_entries = self._capture_character_output()
        try:
            result = func(*args, **kwargs)
            output_entries.append(f"RETURN {result!r}")
        except Exception as error:
            self.set_failure("direct_execution_failure", str(error))
            output_entries.append(f"ERROR {error}")
            raise
        finally:
            self._restore_character_output(original_msg, output_entries)

        return result

    def snapshot(self, label):
        self._ensure_metric_baseline()
        try:
            snapshot = capture_snapshot(self)
        except Exception as error:
            self.set_failure("snapshot_failure", str(error))
            raise
        snapshot["label"] = str(label)
        snapshot["snapshot_label"] = str(label)
        snapshot["timestamp"] = time.time()
        entry = {"label": str(label), "data": snapshot}
        previous_entry = self.snapshots[-1] if self.snapshots else None
        self.snapshots.append(entry)
        if previous_entry is not None:
            diff_entry = {
                "from": str(previous_entry.get("label", "") or ""),
                "to": str(entry.get("label", "") or ""),
                "data": build_snapshot_diff(previous_entry, entry),
            }
            self.diffs.append(diff_entry)
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
        self._ensure_metric_baseline()
        invariant_name = str(name or "").strip()
        result = run_invariant(invariant_name, self)
        self.invariant_results.append(result)
        if not result["passed"]:
            message = result["message"] or f"DireTest invariant failed: {invariant_name}"
            self.set_failure("invariant_failure", message)
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

    def advance_time(self, seconds):
        self.time_offset += float(seconds or 0.0)
        if self.time_frozen:
            self.frozen_time = (self.frozen_time or time.time()) + float(seconds or 0.0)
        return self.time_offset

    def freeze_time(self):
        self.time_frozen = True
        self.frozen_time = time.time() + self.time_offset
        return self.frozen_time

    def resume_time(self):
        self.time_frozen = False
        self.frozen_time = None
        return self.time_offset