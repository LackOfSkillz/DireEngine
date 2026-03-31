"""DireTest scenario runner."""

from __future__ import annotations

import sys
import time
import traceback

from .artifacts import write_artifacts
from .context import DireTestContext
from .failures import build_failure_summary
from .harness import DireTestHarness, cleanup_test_objects
from .metrics import capture_metric_state, summarize_metrics
from .runtime import clear_active_context, set_active_context
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
    started_at = time.time()
    started_perf = time.perf_counter()

    preexisting_cleanup = cleanup_test_objects()
    preexisting_leaks = list(preexisting_cleanup.get("remaining", []) or [])

    harness = DireTestHarness()
    ctx = DireTestContext(harness=harness, mode=normalized_mode, auto_snapshot=auto_snapshot)
    scenario_name = str(name or getattr(scenario_func, "__name__", "scenario") or "scenario")
    run_id = _build_run_id(scenario_name, normalized_mode, normalized_seed)
    result = None
    traceback_text = ""
    exit_code = 0
    failure_type = None
    failure_message = ""
    final_metric_state = None
    teardown_data = {"deletion_failures": [], "leaks": []}
    set_active_context(ctx)

    if preexisting_leaks:
        exit_code = 1
        failure_type = "leak_failure"
        traceback_text = "Preexisting leaked TEST_ objects blocked scenario start."
        failure_message = traceback_text
    else:
        try:
            result = scenario_func(ctx)
        except Exception:
            exit_code = 1
            traceback_text = traceback.format_exc()
            failure_type = getattr(ctx, "failure_type", None) or "unexpected_exception"
            failure_message = getattr(ctx, "failure_message", "") or traceback_text.strip().splitlines()[-1]
        finally:
            try:
                if ctx.get_character() is not None:
                    labels = ctx.get_snapshot_labels()
                    if not labels or labels[-1] != "final":
                        ctx.snapshot("final")
                    final_metric_state = capture_metric_state(ctx.get_character())
            except Exception:
                exit_code = 1
                failure_type = failure_type or getattr(ctx, "failure_type", None) or "snapshot_failure"
                snapshot_traceback = traceback.format_exc()
                traceback_text = f"{traceback_text}\n{snapshot_traceback}".strip()
                failure_message = failure_message or snapshot_traceback.strip().splitlines()[-1]
            try:
                teardown_data = harness.teardown()
            except Exception:
                exit_code = 1
                failure_type = failure_type or "teardown_failure"
                teardown_traceback = traceback.format_exc()
                traceback_text = f"{traceback_text}\n{teardown_traceback}".strip()
                failure_message = failure_message or teardown_traceback.strip().splitlines()[-1]

    if teardown_data.get("leaks"):
        exit_code = 1
        failure_type = failure_type or "leak_failure"
        leak_count = len(teardown_data.get("leaks", []) or [])
        failure_message = failure_message or f"{leak_count} test objects were not cleaned up."
        print(f"Leak detected: {leak_count} test objects were not cleaned up.", file=sys.stderr)
    if preexisting_leaks:
        leak_count = len(preexisting_leaks)
        print(f"Leak detected: {leak_count} preexisting test objects could not be cleaned up.", file=sys.stderr)

    duration_ms = int(max(0, round((time.perf_counter() - started_perf) * 1000.0)))
    metrics_summary = summarize_metrics(
        ctx,
        duration_ms,
        leaks=list(teardown_data.get("leaks", []) or []),
        final_state=final_metric_state,
    )

    if isinstance(result, dict):
        result["snapshot_count"] = len(ctx.snapshots)
        result["snapshot_labels"] = list(ctx.get_snapshot_labels())

    failure_summary = build_failure_summary(
        failure_type=failure_type,
        message=failure_message,
        scenario=scenario_name,
        seed=normalized_seed,
        mode=normalized_mode,
    )

    try:
        artifact_dir = write_artifacts(
            run_id,
            {
                "scenario": {
                    "name": scenario_name,
                    "mode": normalized_mode,
                    "seed": normalized_seed,
                    "started_at": started_at,
                },
                "seed": normalized_seed,
                "command_log": list(ctx.command_log or []),
                "snapshots": list(ctx.snapshots or []),
                "diffs": list(ctx.diffs or []),
                "metrics": {
                    "exit_code": exit_code,
                    "result": result,
                    "failure_type": failure_summary["failure_type"],
                    "started_at": started_at,
                    "ended_at": time.time(),
                    "preexisting_cleanup_failures": list(preexisting_cleanup.get("deletion_failures", []) or []),
                    "preexisting_leaks": list(preexisting_leaks),
                    "deletion_failures": list(teardown_data.get("deletion_failures", []) or []),
                    "leaks": list(teardown_data.get("leaks", []) or []),
                    "invariant_results": list(ctx.invariant_results or []),
                    "output_log": list(ctx.output_log or []),
                    "snapshot_labels": list(ctx.get_snapshot_labels() if hasattr(ctx, "get_snapshot_labels") else []),
                    **metrics_summary,
                },
                "failure_summary": failure_summary,
                "traceback": traceback_text,
            },
        )
    finally:
        clear_active_context(ctx)
    return {
        "artifact_dir": str(artifact_dir),
        "exit_code": exit_code,
        "deletion_failures": list(teardown_data.get("deletion_failures", []) or []),
        "diffs": list(ctx.diffs or []),
        "failure_summary": failure_summary,
        "invariant_results": list(ctx.invariant_results or []),
        "leaks": list(teardown_data.get("leaks", []) or []),
        "metrics": metrics_summary,
        "output_log": list(ctx.output_log or []),
        "preexisting_cleanup_failures": list(preexisting_cleanup.get("deletion_failures", []) or []),
        "preexisting_leaks": list(preexisting_leaks),
        "result": result,
        "seed": normalized_seed,
        "traceback": traceback_text,
    }