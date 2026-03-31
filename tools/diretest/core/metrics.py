"""Metrics helpers for DireTest runs."""

from __future__ import annotations

from .lag import LAG_THRESHOLDS, analyze_latency, detect_spikes


METRICS_SCHEMA = {
    "command_count": int,
    "command_timings_ms": list,
    "scheduler_events": int,
    "max_command_time_ms": float,
    "item_delta_count": int,
    "coin_delta": int,
    "xp_delta": int,
    "mindstate_delta": dict,
    "state_transition_count": int,
    "scenario_duration_ms": int,
    "leaks": list,
    "interest": dict,
}


def _safe_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return float(default)


def _mean(values):
    values = [float(value) for value in list(values or []) if value is not None]
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _aggregate_delay_sources(timing_entries, prefix):
    grouped = {}
    normalized_prefix = str(prefix or "")
    for entry in list(timing_entries or []):
        for source_entry in list((entry or {}).get("script_delay_sources", []) or []):
            source = str((source_entry or {}).get("source", "") or "")
            if not source.startswith(normalized_prefix):
                continue
            bucket = grouped.setdefault(source, {"source": source, "count": 0, "total_ms": 0.0})
            bucket["count"] += 1
            bucket["total_ms"] += _safe_float((source_entry or {}).get("ms", 0.0), 0.0)
    ordered = sorted(grouped.values(), key=lambda item: item["source"])
    return {
        "count": len(ordered),
        "sources": ordered,
        "total_ms": sum(item["total_ms"] for item in ordered),
    }


def _build_scheduler_visibility(runtime_events, runtime_counters, runtime_gauges, final_scheduler_snapshot):
    scheduler_execute_stats = dict((runtime_events or {}).get("scheduler.execute", {}) or {})
    execute_entries = list(scheduler_execute_stats.get("entries", []) or [])
    timing_mode_counts = {}
    system_counts = {}
    key_counts = {}
    timing_modes_exercised = set()
    systems_exercised = set()
    for entry in execute_entries:
        metadata = dict((entry or {}).get("metadata", {}) or {})
        timing_mode = str(metadata.get("timing_mode", "") or "").strip()
        system = str(metadata.get("system", metadata.get("source", "")) or "").strip()
        key = str(metadata.get("key", "") or "").strip()
        if timing_mode:
            timing_mode_counts[timing_mode] = int(timing_mode_counts.get(timing_mode, 0) or 0) + 1
            timing_modes_exercised.add(timing_mode)
        if system:
            system_counts[system] = int(system_counts.get(system, 0) or 0) + 1
            systems_exercised.add(system)
        if key:
            key_counts[key] = int(key_counts.get(key, 0) or 0) + 1

    return {
        "events": _safe_int((runtime_counters or {}).get("scheduler.execute", scheduler_execute_stats.get("count", 0))),
        "scheduled_total": _safe_int((runtime_counters or {}).get("scheduler.schedule", 0)),
        "defer_total": _safe_int((runtime_counters or {}).get("scheduler.defer", 0)),
        "skip_total": _safe_int((runtime_counters or {}).get("scheduler.skip", 0)),
        "cancel_total": _safe_int((runtime_counters or {}).get("scheduler.cancel", 0)),
        "reschedule_total": _safe_int((runtime_counters or {}).get("scheduler.reschedule", 0)),
        "flush_total": _safe_int((runtime_counters or {}).get("scheduler.flush", 0)),
        "flush_executed_total": _safe_int((runtime_counters or {}).get("scheduler.flush.executed", 0)),
        "queue_current": _safe_float((runtime_gauges or {}).get("scheduler.queue.current", 0.0), 0.0),
        "queue_peak": _safe_float((runtime_gauges or {}).get("scheduler.queue.peak", 0.0), 0.0),
        "active_job_count": _safe_int((final_scheduler_snapshot or {}).get("active_job_count", 0)),
        "active_jobs": list((final_scheduler_snapshot or {}).get("active_jobs", []) or []),
        "timing_mode_counts": dict(sorted(timing_mode_counts.items())),
        "system_counts": dict(sorted(system_counts.items())),
        "job_key_breakdown": dict(sorted(key_counts.items())),
        "timing_modes_exercised": sorted(timing_modes_exercised),
        "systems_exercised": sorted(systems_exercised),
    }


def _build_interest_visibility(runtime_events, runtime_counters, runtime_gauges):
    transition_stats = dict((runtime_events or {}).get("interest.transition", {}) or {})
    transition_entries = list(transition_stats.get("entries", []) or [])
    transition_event_counts = {}
    source_types = ("room", "proximity", "zone", "direct", "scheduled")

    for entry in transition_entries:
        metadata = dict((entry or {}).get("metadata", {}) or {})
        event = str(metadata.get("event", "") or "").strip().lower()
        if event:
            transition_event_counts[event] = int(transition_event_counts.get(event, 0) or 0) + 1

    current_source_counts = {}
    peak_source_counts = {}
    source_add_totals = {}
    source_remove_totals = {}
    active_source_types = []
    exercised_source_types = []
    for source_type in source_types:
        current_count = _safe_int((runtime_gauges or {}).get(f"interest.source.current.{source_type}", 0))
        peak_count = _safe_int((runtime_gauges or {}).get(f"interest.source.peak.{source_type}", 0))
        add_total = _safe_int((runtime_counters or {}).get(f"interest.source.add.{source_type}", 0))
        remove_total = _safe_int((runtime_counters or {}).get(f"interest.source.remove.{source_type}", 0))
        current_source_counts[source_type] = current_count
        peak_source_counts[source_type] = peak_count
        source_add_totals[source_type] = add_total
        source_remove_totals[source_type] = remove_total
        if current_count > 0:
            active_source_types.append(source_type)
        if peak_count > 0 or add_total > 0 or remove_total > 0:
            exercised_source_types.append(source_type)

    return {
        "active_object_count": _safe_int((runtime_gauges or {}).get("interest.active_object_count", 0)),
        "active_object_peak": _safe_int((runtime_gauges or {}).get("interest.active_object_peak", 0)),
        "source_count_current": _safe_int((runtime_gauges or {}).get("interest.source_count.current", 0)),
        "source_count_peak": _safe_int((runtime_gauges or {}).get("interest.source_count.peak", 0)),
        "transition_total": _safe_int((transition_stats or {}).get("count", 0)),
        "transition_counts": {
            "activate": _safe_int((runtime_counters or {}).get("interest.transition.activate", 0)),
            "deactivate": _safe_int((runtime_counters or {}).get("interest.transition.deactivate", 0)),
        },
        "transition_event_counts": dict(sorted(transition_event_counts.items())),
        "source_counts": dict(sorted(current_source_counts.items())),
        "source_peak_counts": dict(sorted(peak_source_counts.items())),
        "source_add_totals": dict(sorted(source_add_totals.items())),
        "source_remove_totals": dict(sorted(source_remove_totals.items())),
        "active_source_types": sorted(active_source_types),
        "exercised_source_types": sorted(exercised_source_types),
    }


def _build_ticker_performance(runtime_events, timing_entries):
    ticker_execute_stats = dict((runtime_events or {}).get("ticker.execute", {}) or {})
    performance = {}
    for entry in list(ticker_execute_stats.get("entries", []) or []):
        payload = dict(entry or {})
        metadata = dict(payload.get("metadata", {}) or {})
        ticker_name = str(metadata.get("ticker", "") or "").strip()
        if not ticker_name:
            continue
        bucket = performance.setdefault(ticker_name, {"count": 0, "total_ms": 0.0, "avg_ms": 0.0, "max_ms": 0.0})
        duration_ms = _safe_float(payload.get("duration_ms", 0.0), 0.0)
        bucket["count"] += 1
        bucket["total_ms"] += duration_ms
        bucket["max_ms"] = max(bucket["max_ms"], duration_ms)
        bucket["avg_ms"] = bucket["total_ms"] / bucket["count"] if bucket["count"] else 0.0

    usage = _aggregate_delay_sources(timing_entries, "ticker:")
    usage["performance"] = dict(sorted(performance.items()))
    usage["execution_count"] = sum(int(item.get("count", 0) or 0) for item in performance.values())
    usage["max_ms"] = max((float(item.get("max_ms", 0.0) or 0.0) for item in performance.values()), default=0.0)
    usage["avg_ms"] = (
        sum(float(item.get("total_ms", 0.0) or 0.0) for item in performance.values()) / usage["execution_count"]
        if usage["execution_count"]
        else 0.0
    )
    return usage


def _coerce_timing_entry(entry):
    payload = dict(entry or {})
    return {
        "command": str(payload.get("command", "") or ""),
        "kind": str(payload.get("kind", "command") or "command"),
        "ms": _safe_float(payload.get("ms", 0.0), 0.0),
        "first_response_ms": _safe_float(payload.get("first_response_ms", 0.0), 0.0) if payload.get("first_response_ms") is not None else None,
        "npc_response_delay_ms": _safe_float(payload.get("npc_response_delay_ms", 0.0), 0.0) if payload.get("npc_response_delay_ms") is not None else None,
        "combat_response_ms": _safe_float(payload.get("combat_response_ms", 0.0), 0.0) if payload.get("combat_response_ms") is not None else None,
        "payload_ms": _safe_float(payload.get("payload_ms", 0.0), 0.0),
        "script_delay_ms": _safe_float(payload.get("script_delay_ms", 0.0), 0.0),
        "script_delay_sources": list(payload.get("script_delay_sources", []) or []),
        "snapshot": str(payload.get("snapshot", "") or "") or None,
    }


def build_lag_artifact(ctx, metrics_summary):
    timing_entries = list((metrics_summary or {}).get("command_timing_entries", []) or [])
    spike_events = detect_spikes(timing_entries)
    return {
        "lag": dict((metrics_summary or {}).get("lag", {}) or {}),
        "timing_entries": timing_entries,
        "spike_events": spike_events,
        "slow_commands": list((metrics_summary or {}).get("slow_commands", []) or []),
        "lag_events": list((metrics_summary or {}).get("lag_events", []) or []),
        "first_response_ms": _safe_float((metrics_summary or {}).get("first_response_ms", 0.0), 0.0),
        "npc_response_delay_ms": _safe_float((metrics_summary or {}).get("npc_response_delay_ms", 0.0), 0.0),
        "combat_responsiveness_ms": _safe_float((metrics_summary or {}).get("combat_responsiveness_ms", 0.0), 0.0),
        "payload_timing_ms": _safe_float((metrics_summary or {}).get("payload_timing_ms", 0.0), 0.0),
        "script_delay_ms": _safe_float((metrics_summary or {}).get("script_delay_ms", 0.0), 0.0),
        "replay_comparison": dict((metrics_summary or {}).get("replay_lag_comparison", {}) or {}),
    }


def _mindstate_map(character):
    skills = dict(getattr(getattr(character, "db", None), "skills", {}) or {}) if character else {}
    return {
        str(skill_name): _safe_int((skill_data or {}).get("mindstate", 0))
        for skill_name, skill_data in skills.items()
        if isinstance(skill_data, dict)
    }


def capture_metric_state(character):
    if not character:
        return {
            "coins": 0,
            "item_count": 0,
            "total_xp": 0,
            "mindstate": {},
        }

    inventory_count = len(list(getattr(character, "contents", []) or []))
    worn_count = len(list(character.get_worn_items() or [])) if hasattr(character, "get_worn_items") else 0
    total_xp = _safe_int(getattr(getattr(character, "db", None), "total_xp", 0))

    return {
        "coins": _safe_int(getattr(getattr(character, "db", None), "coins", 0)),
        "item_count": inventory_count + worn_count,
        "total_xp": total_xp,
        "mindstate": _mindstate_map(character),
    }


def mindstate_delta(before, after):
    before_map = dict(before or {})
    after_map = dict(after or {})
    changed = {}
    for key in sorted(set(before_map) | set(after_map)):
        delta = _safe_int(after_map.get(key, 0)) - _safe_int(before_map.get(key, 0))
        if delta:
            changed[key] = delta
    return changed


def summarize_metrics(ctx, duration_ms, leaks=None, final_state=None, runtime_metrics=None, final_scheduler_snapshot=None, scenario_metadata=None):
    initial = dict(getattr(ctx, "metric_baseline", {}) or {})
    final = dict(final_state or capture_metric_state(ctx.get_character()) or {})
    diffs = list(getattr(ctx, "diffs", []) or [])
    timing_entries = [_coerce_timing_entry(entry) for entry in list((getattr(ctx, "metrics", {}) or {}).get("command_timing_entries", []) or [])]
    lag_summary = analyze_latency(timing_entries)
    slow_threshold = float(LAG_THRESHOLDS["warning_ms"])
    slow_commands = [{"cmd": entry["command"], "ms": entry["ms"]} for entry in timing_entries if float(entry.get("ms", 0.0) or 0.0) > slow_threshold]
    first_response_values = [entry.get("first_response_ms") for entry in timing_entries if entry.get("first_response_ms") is not None]
    npc_response_values = [entry.get("npc_response_delay_ms") for entry in timing_entries if entry.get("npc_response_delay_ms") is not None]
    combat_response_values = [entry.get("combat_response_ms") for entry in timing_entries if entry.get("combat_response_ms") is not None]
    payload_values = [entry.get("payload_ms") for entry in timing_entries if entry.get("payload_ms") is not None]
    script_delay_values = [entry.get("script_delay_ms") for entry in timing_entries if entry.get("script_delay_ms") is not None]
    runtime_snapshot = dict(runtime_metrics or {})
    runtime_events = dict(runtime_snapshot.get("events", {}) or {})
    runtime_counters = dict(runtime_snapshot.get("counters", {}) or {})
    runtime_gauges = dict(runtime_snapshot.get("gauges", {}) or {})
    command_execute_stats = dict(runtime_events.get("command.execute", {}) or {})
    scheduler_execute_stats = dict(runtime_events.get("scheduler.execute", {}) or {})
    command_count = len(list(getattr(ctx, "command_log", []) or []))
    scheduler_visibility = _build_scheduler_visibility(runtime_events, runtime_counters, runtime_gauges, final_scheduler_snapshot)
    interest_visibility = _build_interest_visibility(runtime_events, runtime_counters, runtime_gauges)
    scheduler_event_count = _safe_int(scheduler_visibility.get("events", 0))
    max_command_time_ms = _safe_float(command_execute_stats.get("max_ms", 0.0), 0.0)
    ticker_usage = _build_ticker_performance(runtime_events, timing_entries)
    script_activity = _aggregate_delay_sources(timing_entries, "script:")

    return {
        "command_count": command_count,
        "command_timings_ms": [_safe_float(entry.get("ms", 0.0), 0.0) for entry in timing_entries],
        "command_timing_entries": timing_entries,
        "scheduler_events": scheduler_event_count,
        "max_command_time_ms": max_command_time_ms,
        "item_delta_count": _safe_int(final.get("item_count", 0)) - _safe_int(initial.get("item_count", 0)),
        "coin_delta": _safe_int(final.get("coins", 0)) - _safe_int(initial.get("coins", 0)),
        "xp_delta": _safe_int(final.get("total_xp", 0)) - _safe_int(initial.get("total_xp", 0)),
        "mindstate_delta": mindstate_delta(initial.get("mindstate", {}), final.get("mindstate", {})),
        "state_transition_count": len(diffs),
        "scenario_duration_ms": int(max(0, round(_safe_float(duration_ms, 0.0)))),
        "leaks": list(leaks or []),
        "lag": lag_summary,
        "slow_commands": slow_commands,
        "lag_events": list(getattr(ctx, "lag_events", []) or []),
        "first_response_ms": _mean(first_response_values),
        "npc_response_delay_ms": _mean(npc_response_values),
        "combat_responsiveness_ms": _mean(combat_response_values),
        "payload_timing_ms": _mean(payload_values),
        "script_delay_ms": _mean(script_delay_values),
        "commands": {
            "count": command_count,
            "max_ms": max_command_time_ms,
            "timings_ms": [_safe_float(entry.get("ms", 0.0), 0.0) for entry in timing_entries],
        },
        "interest": interest_visibility,
        "scheduler": scheduler_visibility,
        "ticker": ticker_usage,
        "scripts": script_activity,
        "timing_model": {
            "timing_modes_exercised": list(scheduler_visibility.get("timing_modes_exercised", []) or []),
            "scheduler_job_count": _safe_int(scheduler_visibility.get("active_job_count", 0)),
            "scheduler_job_key_breakdown": dict(scheduler_visibility.get("job_key_breakdown", {}) or {}),
            "ticker_usage": ticker_usage,
            "script_activity": script_activity,
            "flush_usage": {
                "flush_total": _safe_int(scheduler_visibility.get("flush_total", 0)),
                "flush_executed_total": _safe_int(scheduler_visibility.get("flush_executed_total", 0)),
            },
            "lag_policy": {
                "fail_on_critical_lag": bool(dict(scenario_metadata or {}).get("fail_on_critical_lag", True)),
                "reason": str(dict(scenario_metadata or {}).get("lag_policy_reason", "") or ""),
            },
        },
        "timings": {
            "command_execute": command_execute_stats,
            "scheduler_execute": scheduler_execute_stats,
        },
    }