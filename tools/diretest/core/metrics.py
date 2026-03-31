"""Metrics helpers for DireTest runs."""

from __future__ import annotations

from .lag import LAG_THRESHOLDS, analyze_latency, detect_spikes


METRICS_SCHEMA = {
    "command_count": int,
    "command_timings_ms": list,
    "item_delta_count": int,
    "coin_delta": int,
    "xp_delta": int,
    "mindstate_delta": dict,
    "state_transition_count": int,
    "scenario_duration_ms": int,
    "leaks": list,
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


def summarize_metrics(ctx, duration_ms, leaks=None, final_state=None):
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

    return {
        "command_count": len(list(getattr(ctx, "command_log", []) or [])),
        "command_timings_ms": [_safe_float(entry.get("ms", 0.0), 0.0) for entry in timing_entries],
        "command_timing_entries": timing_entries,
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
    }