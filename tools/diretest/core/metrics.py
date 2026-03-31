"""Metrics helpers for DireTest runs."""

from __future__ import annotations


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

    return {
        "command_count": len(list(getattr(ctx, "command_log", []) or [])),
        "command_timings_ms": [int(value) for value in list((getattr(ctx, "metrics", {}) or {}).get("command_timings_ms", []) or [])],
        "item_delta_count": _safe_int(final.get("item_count", 0)) - _safe_int(initial.get("item_count", 0)),
        "coin_delta": _safe_int(final.get("coins", 0)) - _safe_int(initial.get("coins", 0)),
        "xp_delta": _safe_int(final.get("total_xp", 0)) - _safe_int(initial.get("total_xp", 0)),
        "mindstate_delta": mindstate_delta(initial.get("mindstate", {}), final.get("mindstate", {})),
        "state_transition_count": len(diffs),
        "scenario_duration_ms": int(max(0, round(_safe_float(duration_ms, 0.0)))),
        "leaks": list(leaks or []),
    }