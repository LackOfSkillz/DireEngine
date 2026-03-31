"""DireTest scenario runner."""

from __future__ import annotations

import sys
import time
import traceback

from .artifacts import write_artifacts
from .context import DireTestContext
from .harness import DireTestHarness, cleanup_test_objects
from .seed import set_seed


def _normalize_mode(mode):
    normalized = str(mode or "").strip().lower()
    if normalized not in {"command", "direct"}:
        raise ValueError("DireTest mode must be 'command' or 'direct'.")
    return normalized


def _coerce_seed(seed):
    if seed is None:
        return int(time.time_ns() % 1000000000)
    return int(seed)


def _build_run_id(name, mode, seed):
    slug = str(name or "scenario").strip().lower().replace(" ", "_")
    return f"{slug}_{mode}_{seed}"


def run_scenario(scenario_func, seed: int, mode: str, auto_snapshot: bool = False, name: str | None = None):
    normalized_mode = _normalize_mode(mode)
    normalized_seed = _coerce_seed(seed)
    set_seed(normalized_seed)

    preexisting_cleanup = cleanup_test_objects()
    preexisting_leaks = list(preexisting_cleanup.get("remaining", []) or [])

    harness = DireTestHarness()
    ctx = DireTestContext(harness=harness, mode=normalized_mode, auto_snapshot=auto_snapshot)
    scenario_name = str(name or getattr(scenario_func, "__name__", "scenario") or "scenario")
    run_id = _build_run_id(scenario_name, normalized_mode, normalized_seed)
    result = None
    traceback_text = ""
    exit_code = 0
    teardown_data = {"deletion_failures": [], "leaks": []}

    if preexisting_leaks:
        exit_code = 1
        traceback_text = "Preexisting leaked TEST_ objects blocked scenario start."
    else:
        try:
            result = scenario_func(ctx)
        except Exception:
            exit_code = 1
            traceback_text = traceback.format_exc()
        finally:
            try:
                teardown_data = harness.teardown()
            except Exception:
                exit_code = 1
                teardown_traceback = traceback.format_exc()
                traceback_text = f"{traceback_text}\n{teardown_traceback}".strip()

    if teardown_data.get("leaks"):
        exit_code = 1
        leak_count = len(teardown_data.get("leaks", []) or [])
        print(f"Leak detected: {leak_count} test objects were not cleaned up.", file=sys.stderr)
    if preexisting_leaks:
        leak_count = len(preexisting_leaks)
        print(f"Leak detected: {leak_count} preexisting test objects could not be cleaned up.", file=sys.stderr)

    artifact_dir = write_artifacts(
        run_id,
        {
            "scenario": {
                "name": scenario_name,
                "mode": normalized_mode,
                "seed": normalized_seed,
            },
            "seed": normalized_seed,
            "command_log": list(ctx.command_log or []),
            "snapshots": list(ctx.snapshots or []),
            "metrics": {
                "exit_code": exit_code,
                "result": result,
                "preexisting_cleanup_failures": list(preexisting_cleanup.get("deletion_failures", []) or []),
                "preexisting_leaks": list(preexisting_leaks),
                "deletion_failures": list(teardown_data.get("deletion_failures", []) or []),
                "leaks": list(teardown_data.get("leaks", []) or []),
                "invariant_results": list(ctx.invariant_results or []),
                "output_log": list(ctx.output_log or []),
                "snapshot_labels": list(ctx.get_snapshot_labels() if hasattr(ctx, "get_snapshot_labels") else []),
            },
            "traceback": traceback_text,
        },
    )
    return {
        "artifact_dir": str(artifact_dir),
        "exit_code": exit_code,
        "deletion_failures": list(teardown_data.get("deletion_failures", []) or []),
        "invariant_results": list(ctx.invariant_results or []),
        "leaks": list(teardown_data.get("leaks", []) or []),
        "output_log": list(ctx.output_log or []),
        "preexisting_cleanup_failures": list(preexisting_cleanup.get("deletion_failures", []) or []),
        "preexisting_leaks": list(preexisting_leaks),
        "result": result,
        "seed": normalized_seed,
        "traceback": traceback_text,
    }