"""In-memory timing and event metrics for engine hardening work."""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock
import time


_LOCK = RLock()
_COUNTERS = defaultdict(int)
_EVENTS = defaultdict(list)
_GAUGES = {}


def _safe_float(value, default=0.0):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return int(default)


def reset_metrics():
    with _LOCK:
        _COUNTERS.clear()
        _EVENTS.clear()
        _GAUGES.clear()


def increment_counter(name: str, amount: int = 1):
    key = str(name or "").strip()
    if not key:
        return 0
    with _LOCK:
        _COUNTERS[key] += _safe_int(amount, 0)
        return _COUNTERS[key]


def set_gauge(name: str, value):
    key = str(name or "").strip()
    if not key:
        return None
    numeric = _safe_float(value, 0.0)
    with _LOCK:
        _GAUGES[key] = numeric
        return numeric


def observe_max(name: str, value):
    key = str(name or "").strip()
    if not key:
        return None
    numeric = _safe_float(value, 0.0)
    with _LOCK:
        _GAUGES[key] = max(numeric, _safe_float(_GAUGES.get(key, 0.0), 0.0))
        return _GAUGES[key]


def record_event(name: str, duration_ms: float, metadata=None):
    key = str(name or "").strip()
    if not key:
        return {}
    payload = {
        "duration_ms": max(0.0, _safe_float(duration_ms, 0.0)),
        "metadata": dict(metadata or {}),
        "timestamp": time.time(),
    }
    with _LOCK:
        _EVENTS[key].append(payload)
    return payload


@contextmanager
def measure(name: str, metadata=None):
    started = time.perf_counter()
    try:
        yield
    finally:
        record_event(name, (time.perf_counter() - started) * 1000.0, metadata=metadata)


def _event_stats(entries):
    values = [_safe_float((entry or {}).get("duration_ms", 0.0), 0.0) for entry in list(entries or [])]
    count = len(values)
    total_ms = float(sum(values)) if values else 0.0
    return {
        "count": count,
        "total_ms": total_ms,
        "avg_ms": (total_ms / count) if count else 0.0,
        "max_ms": max(values) if values else 0.0,
        "entries": deepcopy(list(entries or [])),
    }


def snapshot_metrics():
    with _LOCK:
        counters = dict(_COUNTERS)
        gauges = dict(_GAUGES)
        events = {name: _event_stats(entries) for name, entries in _EVENTS.items()}
    return {
        "counters": counters,
        "gauges": gauges,
        "events": events,
    }
