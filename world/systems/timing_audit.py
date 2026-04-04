"""Unified timing audit helpers for scheduler, ticker, and script visibility."""

from __future__ import annotations

from collections import Counter
from threading import RLock

from evennia.utils import logger

from world.systems.metrics import snapshot_metrics
from world.systems.scheduler import get_scheduler_snapshot
from world.systems.tick_audit import scan_for_tick_violations
from world.systems.time_model import CONTROLLER


_LOCK = RLock()
_TICKER_REGISTRATIONS = {}
_WARNED_MESSAGES = set()
_SCRIPT_TIMING_CLASSIFICATIONS = {
    "typeclasses.scripts.BleedTicker": "invalid",
    "typeclasses.scripts.CorpseDecayScript": CONTROLLER,
    "typeclasses.scripts.GraveMaintenanceScript": CONTROLLER,
    "typeclasses.onboarding_scripts.OnboardingRoleplayScript": CONTROLLER,
    "typeclasses.onboarding_scripts.OnboardingInvasionScript": CONTROLLER,
}
_SCRIPT_BEHAVIOR_CLASSIFICATIONS = {
    "typeclasses.scripts.BleedTicker": "poller",
    "typeclasses.scripts.CorpseDecayScript": "mixed",
    "typeclasses.scripts.GraveMaintenanceScript": "mixed",
    "typeclasses.onboarding_scripts.OnboardingRoleplayScript": "mixed",
    "typeclasses.onboarding_scripts.OnboardingInvasionScript": "controller",
}


def _ticker_registry_key(interval, idstring, persistent):
    return (int(interval or 0), str(idstring or "").strip(), bool(persistent))


def _warn_once(message):
    text = str(message or "").strip()
    if not text:
        return
    with _LOCK:
        if text in _WARNED_MESSAGES:
            return
        _WARNED_MESSAGES.add(text)
    logger.log_warn(text)


def register_ticker_metadata(interval, callback, *, idstring="", persistent=True, system="", reason=""):
    callback_name = getattr(callback, "__name__", "callback")
    record = {
        "interval": int(interval or 0),
        "callback": callback_name,
        "idstring": str(idstring or callback_name).strip(),
        "persistent": bool(persistent),
        "system": str(system or callback_name).strip(),
        "reason": str(reason or "").strip(),
    }
    if not str(system or "").strip():
        _warn_once(f"[TimingAudit] Shared ticker registration missing explicit system metadata for callback={callback_name} idstring={record['idstring']}.")
    if not str(reason or "").strip():
        _warn_once(f"[TimingAudit] Shared ticker registration missing reason metadata for callback={callback_name} idstring={record['idstring']}.")
    with _LOCK:
        _TICKER_REGISTRATIONS[_ticker_registry_key(record["interval"], record["idstring"], record["persistent"])] = record
    return dict(record)


def unregister_ticker_metadata(interval, *, idstring="", persistent=True):
    with _LOCK:
        return _TICKER_REGISTRATIONS.pop(_ticker_registry_key(interval, idstring, persistent), None)


def get_ticker_snapshot():
    with _LOCK:
        registrations = [dict(record) for _, record in sorted(_TICKER_REGISTRATIONS.items(), key=lambda item: item[0])]
    runtime_metrics = dict(snapshot_metrics() or {})
    runtime_events = dict(runtime_metrics.get("events", {}) or {})
    ticker_execute_stats = dict(runtime_events.get("ticker.execute", {}) or {})
    performance = {}
    for entry in list(ticker_execute_stats.get("entries", []) or []):
        payload = dict(entry or {})
        metadata = dict(payload.get("metadata", {}) or {})
        ticker_name = str(metadata.get("ticker", "") or "").strip()
        if not ticker_name:
            continue
        bucket = performance.setdefault(ticker_name, {"count": 0, "total_ms": 0.0, "avg_ms": 0.0, "max_ms": 0.0})
        duration_ms = float(payload.get("duration_ms", 0.0) or 0.0)
        bucket["count"] += 1
        bucket["total_ms"] += duration_ms
        bucket["max_ms"] = max(bucket["max_ms"], duration_ms)
        bucket["avg_ms"] = bucket["total_ms"] / bucket["count"] if bucket["count"] else 0.0
    return {
        "registered_tickers": registrations,
        "registered_ticker_count": len(registrations),
        "performance": dict(sorted(performance.items())),
    }


def get_script_controller_snapshot():
    try:
        from evennia.scripts.models import ScriptDB
    except Exception:
        return {
            "active_scripts": [],
            "active_script_count": 0,
            "unclassified_scripts": [],
        }

    active_scripts = []
    unclassified = []
    for script in ScriptDB.objects.all().order_by("id"):
        typeclass_path = str(
            getattr(script, "typeclass_path", None)
            or getattr(script, "db_typeclass_path", None)
            or ""
        ).strip()
        if not typeclass_path.startswith("typeclasses."):
            continue
        obj = getattr(script, "obj", None)
        timing_classification = _SCRIPT_TIMING_CLASSIFICATIONS.get(typeclass_path)
        behavior_classification = _SCRIPT_BEHAVIOR_CLASSIFICATIONS.get(typeclass_path)
        interval = int(getattr(script, "interval", 0) or 0)
        record = {
            "key": str(getattr(script, "key", "") or ""),
            "typeclass_path": typeclass_path,
            "classification": timing_classification or "unclassified",
            "behavior_classification": behavior_classification or "unclassified",
            "interval": interval,
            "persistent": bool(getattr(script, "persistent", False)),
            "is_active": bool(getattr(script, "is_active", False)),
            "object_key": getattr(obj, "key", None),
            "object_id": getattr(obj, "id", None),
        }
        active_scripts.append(record)
        if interval > 0 and (not timing_classification or not behavior_classification):
            missing = []
            if not timing_classification:
                missing.append("timing_classification")
            if not behavior_classification:
                missing.append("behavior_classification")
            _warn_once(
                f"[TimingAudit] Timed Script missing {' and '.join(missing)} metadata: {typeclass_path} key={record['key'] or '-'}"
            )
        if not timing_classification or not behavior_classification:
            unclassified.append(record)
    return {
        "active_scripts": active_scripts,
        "active_script_count": len(active_scripts),
        "unclassified_scripts": unclassified,
    }


def _build_scheduler_breakdown(active_jobs):
    by_system = Counter()
    by_timing_mode = Counter()
    by_key = Counter()
    for job in list(active_jobs or []):
        system = str((job or {}).get("system", "") or "").strip()
        timing_mode = str((job or {}).get("timing_mode", "") or "").strip()
        key = str((job or {}).get("key", "") or "").strip()
        if system:
            by_system[system] += 1
        if timing_mode:
            by_timing_mode[timing_mode] += 1
        if key:
            by_key[key] += 1
    return {
        "by_system": dict(sorted(by_system.items())),
        "by_timing_mode": dict(sorted(by_timing_mode.items())),
        "by_key": dict(sorted(by_key.items())),
    }


def collect_timing_audit(max_tick_warnings=25):
    scheduler = dict(get_scheduler_snapshot() or {})
    scheduler["breakdown"] = _build_scheduler_breakdown(scheduler.get("active_jobs", []))
    tickers = get_ticker_snapshot()
    scripts = get_script_controller_snapshot()
    warnings = list(scan_for_tick_violations()[: max(0, int(max_tick_warnings or 0))])

    unclassified = []
    for job in list(scheduler.get("active_jobs", []) or []):
        if not str((job or {}).get("system", "") or "").strip() or not str((job or {}).get("timing_mode", "") or "").strip():
            unclassified.append({"kind": "scheduler", **dict(job or {})})
    for ticker in list(tickers.get("registered_tickers", []) or []):
        if not str((ticker or {}).get("system", "") or "").strip() or not str((ticker or {}).get("reason", "") or "").strip():
            unclassified.append({"kind": "ticker", **dict(ticker or {})})
    for script in list(scripts.get("unclassified_scripts", []) or []):
        unclassified.append({"kind": "script", **dict(script or {})})

    return {
        "scheduler": scheduler,
        "tickers": tickers,
        "scripts": scripts,
        "tick_audit_warnings": warnings,
        "unclassified_registrations": unclassified,
    }


def render_timing_audit_text(report):
    payload = dict(report or {})
    scheduler = dict(payload.get("scheduler", {}) or {})
    scheduler_breakdown = dict(scheduler.get("breakdown", {}) or {})
    tickers = dict(payload.get("tickers", {}) or {})
    scripts = dict(payload.get("scripts", {}) or {})
    warnings = list(payload.get("tick_audit_warnings", []) or [])
    unclassified = list(payload.get("unclassified_registrations", []) or [])

    lines = ["Timing Audit"]
    lines.append(f"Scheduler jobs: {int(scheduler.get('active_job_count', 0) or 0)}")
    for system, count in dict(scheduler_breakdown.get("by_system", {}) or {}).items():
        lines.append(f"  scheduler system {system}: {int(count or 0)}")
    for timing_mode, count in dict(scheduler_breakdown.get("by_timing_mode", {}) or {}).items():
        lines.append(f"  scheduler mode {timing_mode}: {int(count or 0)}")

    lines.append(f"Ticker registrations: {int(tickers.get('registered_ticker_count', 0) or 0)}")
    for ticker in list(tickers.get("registered_tickers", []) or []):
        performance = dict((tickers.get("performance", {}) or {}).get(str(ticker.get("callback", "") or ""), {}) or {})
        lines.append(
            f"  {ticker.get('idstring')} [{ticker.get('system')}] interval={int(ticker.get('interval', 0) or 0)} persistent={bool(ticker.get('persistent', False))} count={int(performance.get('count', 0) or 0)} avg_ms={float(performance.get('avg_ms', 0.0) or 0.0):.2f} max_ms={float(performance.get('max_ms', 0.0) or 0.0):.2f}"
        )

    lines.append(f"Active custom scripts: {int(scripts.get('active_script_count', 0) or 0)}")
    for script in list(scripts.get("active_scripts", []) or []):
        lines.append(
            f"  {script.get('key')} [{script.get('classification')}/{script.get('behavior_classification')}] {script.get('typeclass_path')} obj={script.get('object_key') or '-'}"
        )

    lines.append(f"Tick audit warnings: {len(warnings)}")
    for warning in warnings[:10]:
        lines.append(
            f"  {warning.get('kind')}: {warning.get('path')}:{int(warning.get('line', 0) or 0)} - {warning.get('message', '')}"
        )
    if len(warnings) > 10:
        lines.append(f"  ... {len(warnings) - 10} more")

    lines.append(f"Unclassified registrations: {len(unclassified)}")
    for item in unclassified[:10]:
        lines.append(f"  {item.get('kind')}: {item}")
    if len(unclassified) > 10:
        lines.append(f"  ... {len(unclassified) - 10} more")

    return "\n".join(lines)


__all__ = [
    "collect_timing_audit",
    "get_script_controller_snapshot",
    "get_ticker_snapshot",
    "register_ticker_metadata",
    "render_timing_audit_text",
    "unregister_ticker_metadata",
]