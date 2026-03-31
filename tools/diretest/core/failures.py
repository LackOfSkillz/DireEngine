"""Failure classification for DireTest."""

from __future__ import annotations


FAILURE_TYPES = [
    "scenario_lookup_failure",
    "command_execution_failure",
    "direct_execution_failure",
    "invariant_failure",
    "lag_failure",
    "teardown_failure",
    "leak_failure",
    "snapshot_failure",
    "artifact_write_failure",
    "unexpected_exception",
]


def normalize_failure_type(value):
    failure_type = str(value or "").strip()
    if not failure_type:
        return None
    if failure_type not in FAILURE_TYPES:
        return "unexpected_exception"
    return failure_type


def build_failure_summary(failure_type=None, message="", scenario="", seed=0, mode="direct", lag_status=None):
    return {
        "failure_type": normalize_failure_type(failure_type),
        "lag_status": str(lag_status or "") or None,
        "message": str(message or ""),
        "scenario": str(scenario or ""),
        "seed": int(seed or 0),
        "mode": str(mode or "direct"),
    }