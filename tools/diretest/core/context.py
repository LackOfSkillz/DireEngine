"""Scenario execution context for DireTest."""

from __future__ import annotations

import time

from .diff import diff_snapshots as build_snapshot_diff
from .harness import _initialize_character_cmdsets
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
        self.lag_events = []
        self.log_messages = []
        self.invariant_results = []
        self.metrics = {"command_timings_ms": [], "command_timing_entries": []}
        self.metric_baseline = {}
        self.failure_type = None
        self.failure_message = ""
        self.test_mode = True
        self.suppress_client_payloads = False
        self.time_offset = 0.0
        self.time_frozen = False
        self.frozen_time = None
        self._previous_object_records = {}
        self._pending_lag_event_indexes = []
        self._pending_payload_ms = 0.0
        self._pending_script_delays = []

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

    def _looks_like_npc_response(self, text):
        payload = str(text or "").strip().lower()
        if not payload:
            return False
        return any(token in payload for token in ["mentor", "gremlin", "goblin", "objective", " says", "asks", "growls"])

    def _looks_like_combat_response(self, command, text):
        command_text = str(command or "").strip().lower()
        payload = str(text or "").strip().lower()
        if not command_text or not payload:
            return False
        if not any(token in command_text for token in ["attack", "ambush", "target", "disengage", "retreat"]):
            return False
        return any(token in payload for token in ["attack", "hit", "miss", "damage", "roundtime", "disengage", "retreat", "engage", "combat"])

    def _capture_character_output(self, started_perf=None, command_label=""):
        if not self.character:
            return None, None

        original_msg = self.character.msg
        probe = {
            "entries": [],
            "timed_entries": [],
            "first_response_ms": None,
            "npc_response_delay_ms": None,
            "combat_response_ms": None,
        }

        def capture_msg(*args, **kwargs):
            payload = kwargs.get("text")
            if payload is None and args:
                payload = args[0]
            options = kwargs.get("options")
            entries = self._coerce_output_entries(payload=payload, options=options, kwargs={key: value for key, value in kwargs.items() if key not in {"text", "options"}})
            elapsed_ms = None
            if started_perf is not None:
                elapsed_ms = max(0.0, (time.perf_counter() - started_perf) * 1000.0)
            for entry in entries:
                probe["entries"].append(entry)
                probe["timed_entries"].append({"text": entry, "ms": elapsed_ms})
                if elapsed_ms is not None and probe["first_response_ms"] is None:
                    probe["first_response_ms"] = elapsed_ms
                if elapsed_ms is not None and probe["npc_response_delay_ms"] is None and self._looks_like_npc_response(entry):
                    probe["npc_response_delay_ms"] = elapsed_ms
                if elapsed_ms is not None and probe["combat_response_ms"] is None and self._looks_like_combat_response(command_label, entry):
                    probe["combat_response_ms"] = elapsed_ms
            return original_msg(*args, **kwargs)

        self.character.msg = capture_msg
        return original_msg, probe

    def _restore_character_output(self, original_msg, output_probe):
        if self.character and original_msg is not None:
            self.character.msg = original_msg
        entries = list((output_probe or {}).get("entries", []) or [])
        if entries:
            self.output_log.extend(entries)
        return entries

    def record_payload_timing(self, duration_ms):
        try:
            self._pending_payload_ms += max(0.0, float(duration_ms or 0.0))
        except (TypeError, ValueError):
            return self._pending_payload_ms
        return self._pending_payload_ms

    def record_script_delay(self, duration_ms, source=""):
        try:
            delay_ms = max(0.0, float(duration_ms or 0.0))
        except (TypeError, ValueError):
            delay_ms = 0.0
        self._pending_script_delays.append({"source": str(source or ""), "ms": delay_ms})
        return delay_ms

    def _link_pending_lag_events(self, snapshot_label):
        if not self._pending_lag_event_indexes:
            return
        label = str(snapshot_label or "")
        event_indexes = list(self._pending_lag_event_indexes)
        self._pending_lag_event_indexes = []
        for index in event_indexes:
            if 0 <= index < len(self.lag_events):
                self.lag_events[index]["snapshot"] = label
            timing_entries = list((self.metrics or {}).get("command_timing_entries", []) or [])
            if 0 <= index < len(timing_entries):
                timing_entries[index]["snapshot"] = label

    def _record_timing_entry(self, command_label, elapsed_ms, output_probe, kind="command"):
        probe = dict(output_probe or {})
        payload_ms = max(0.0, float(self._pending_payload_ms or 0.0))
        script_entries = list(self._pending_script_delays or [])
        script_delay_ms = sum(float((entry or {}).get("ms", 0.0) or 0.0) for entry in script_entries)
        entry = {
            "command": str(command_label or "").strip(),
            "kind": str(kind or "command"),
            "ms": max(0.0, float(elapsed_ms or 0.0)),
            "first_response_ms": probe.get("first_response_ms"),
            "npc_response_delay_ms": probe.get("npc_response_delay_ms"),
            "combat_response_ms": probe.get("combat_response_ms"),
            "payload_ms": payload_ms,
            "script_delay_ms": script_delay_ms,
            "script_delay_sources": script_entries,
            "snapshot": None,
        }
        timing_entries = self.metrics.setdefault("command_timing_entries", [])
        timing_entries.append(entry)
        self.metrics.setdefault("command_timings_ms", []).append(entry["ms"])
        self.lag_events.append({"command": entry["command"], "ms": entry["ms"], "snapshot": None})
        self._pending_lag_event_indexes.append(len(self.lag_events) - 1)
        self._pending_payload_ms = 0.0
        self._pending_script_delays = []
        return entry

    def cmd(self, command_str):
        command = str(command_str or "").strip()
        if not command:
            raise ValueError("ctx.cmd requires a non-empty command string.")
        if not self.character:
            raise ValueError("ctx.cmd requires an active test character.")

        _initialize_character_cmdsets(self.character)
        self._ensure_metric_baseline()
        self.command_log.append(command)
        original_msg, output_probe = self._capture_character_output(started_perf=time.perf_counter(), command_label=command)
        started = time.perf_counter()
        try:
            result = self.character.execute_cmd(command)
        except Exception as error:
            self.set_failure("command_execution_failure", str(error))
            if output_probe is not None:
                output_probe.setdefault("entries", []).append(f"ERROR {error}")
            raise
        finally:
            elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
            self._restore_character_output(original_msg, output_probe)
            self._record_timing_entry(command, elapsed_ms, output_probe, kind="command")

        self.room = getattr(self.character, "location", None) or self.room
        if self.auto_snapshot:
            self.snapshot(command)
        return result

    def direct(self, func, *args, **kwargs):
        function_name = getattr(func, "__name__", "callable")
        self._ensure_metric_baseline()
        self.command_log.append(f"DIRECT {function_name}")

        started = time.perf_counter()
        original_msg, output_probe = self._capture_character_output(started_perf=started, command_label=f"DIRECT {function_name}")
        try:
            result = func(*args, **kwargs)
            if output_probe is not None:
                output_probe.setdefault("entries", []).append(f"RETURN {result!r}")
        except Exception as error:
            self.set_failure("direct_execution_failure", str(error))
            if output_probe is not None:
                output_probe.setdefault("entries", []).append(f"ERROR {error}")
            raise
        finally:
            elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
            self._restore_character_output(original_msg, output_probe)
            self._record_timing_entry(f"DIRECT {function_name}", elapsed_ms, output_probe, kind="direct")

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
        self._link_pending_lag_events(label)
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