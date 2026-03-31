"""Lag analysis helpers for DireTest runs."""

from __future__ import annotations

import math
import statistics


LAG_SCHEMA = {
    "avg_ms": float,
    "max_ms": float,
    "min_ms": float,
    "p95_ms": float,
    "spike_count": int,
    "slow_count": int,
    "jitter": float,
    "status": str,
}


LAG_THRESHOLDS = {
    "warning_ms": 150,
    "bad_ms": 250,
    "critical_ms": 500,
    "spike_ms": 300,
}


def _coerce_ms(entry):
    if isinstance(entry, dict):
        entry = entry.get("ms", 0.0)
    try:
        return max(0.0, float(entry or 0.0))
    except (TypeError, ValueError):
        return 0.0


def percentile(values, fraction):
    ordered = sorted(float(value) for value in list(values or []))
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, float(fraction))) * (len(ordered) - 1)
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return ordered[lower_index]
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    blend = position - lower_index
    return lower_value + ((upper_value - lower_value) * blend)


def detect_spikes(timings):
    threshold = float(LAG_THRESHOLDS["spike_ms"])
    spikes = []
    for entry in list(timings or []):
        ms = _coerce_ms(entry)
        if ms > threshold:
            if isinstance(entry, dict):
                spikes.append(dict(entry))
            else:
                spikes.append({"ms": ms})
    return spikes


def calculate_jitter(timings):
    values = [_coerce_ms(entry) for entry in list(timings or [])]
    if len(values) < 2:
        return 0.0
    try:
        return float(statistics.stdev(values))
    except statistics.StatisticsError:
        return 0.0


def compute_status_level(timings, jitter=0.0):
    values = [_coerce_ms(entry) for entry in list(timings or [])]
    if not values:
        return "ok"
    maximum = max(values)
    if maximum > float(LAG_THRESHOLDS["critical_ms"]):
        return "critical"
    if maximum > float(LAG_THRESHOLDS["bad_ms"]):
        return "bad"
    if maximum > float(LAG_THRESHOLDS["warning_ms"]):
        return "warning"
    if float(jitter or 0.0) > 75.0:
        return "warning"
    return "ok"


def analyze_latency(command_timings_ms):
    values = [_coerce_ms(entry) for entry in list(command_timings_ms or [])]
    if not values:
        return {
            "avg_ms": 0.0,
            "max_ms": 0.0,
            "min_ms": 0.0,
            "p95_ms": 0.0,
            "spike_count": 0,
            "slow_count": 0,
            "jitter": 0.0,
            "status": "ok",
        }

    spike_count = len(detect_spikes(values))
    slow_threshold = float(LAG_THRESHOLDS["warning_ms"])
    slow_count = len([value for value in values if value > slow_threshold])
    jitter = calculate_jitter(values)
    return {
        "avg_ms": float(sum(values) / len(values)),
        "max_ms": float(max(values)),
        "min_ms": float(min(values)),
        "p95_ms": float(percentile(values, 0.95)),
        "spike_count": int(spike_count),
        "slow_count": int(slow_count),
        "jitter": float(jitter),
        "status": compute_status_level(values, jitter=jitter),
    }