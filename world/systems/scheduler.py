"""Thin scheduler wrapper used for engine-timed work."""

from __future__ import annotations

from threading import RLock
import time
from uuid import uuid4

from evennia.utils import delay as evennia_delay
from evennia.utils import logger

from world.systems.metrics import increment_counter, measure, observe_max, set_gauge


_LOCK = RLock()
_ACTIVE_JOBS = {}
_KEY_TO_JOB_ID = {}


class _DeferredTask:
    def __init__(self, callback=None):
        self.cancelled = False
        self.callback = callback

    def cancel(self):
        self.cancelled = True
        return True


def _normalize_key(key):
    raw = str(key or "").strip()
    return raw or None


def _update_queue_metrics():
    current = len(_ACTIVE_JOBS)
    set_gauge("scheduler.queue.current", current)
    observe_max("scheduler.queue.peak", current)
    return current


def _pop_job(job_id):
    record = _ACTIVE_JOBS.pop(job_id, None)
    if not record:
        _update_queue_metrics()
        return None
    key = record.get("key")
    if key and _KEY_TO_JOB_ID.get(key) == job_id:
        _KEY_TO_JOB_ID.pop(key, None)
    _update_queue_metrics()
    return record


def _cancel_task(task):
    if hasattr(task, "cancel"):
        try:
            task.cancel()
        except Exception:
            return False
        return True
    return False


def _execute_job(job_id):
    with _LOCK:
        record = _ACTIVE_JOBS.get(job_id)
        if not record:
            return False
        task = record.get("task")
        if getattr(task, "cancelled", False):
            _pop_job(job_id)
            return False
        callback = record.get("wrapped_callback")
    if not callback:
        return False
    callback(*record.get("args", ()), **record.get("kwargs", {}))
    return True


def _use_live_delay():
    try:
        from tools.diretest.core.runtime import is_diretest_mode

        return not bool(is_diretest_mode())
    except Exception:
        return True


def schedule(delay, callback, key=None, *args, source="", timing_mode="scheduled", **kwargs):
    delay_seconds = max(0.0, float(delay or 0.0))
    callback_name = getattr(callback, "__name__", "callback")
    normalized_key = _normalize_key(key)

    if normalized_key:
        cancel(normalized_key)

    job_id = uuid4().hex
    metadata = {
        "key": normalized_key,
        "source": str(source or callback_name),
        "timing_mode": str(timing_mode or "scheduled"),
        "delay_s": delay_seconds,
    }

    def _wrapped_callback(*cb_args, **cb_kwargs):
        increment_counter("scheduler.execute")
        try:
            with measure("scheduler.execute", metadata=metadata):
                return callback(*cb_args, **cb_kwargs)
        finally:
            with _LOCK:
                _pop_job(job_id)

    due_at = time.time() + delay_seconds
    task = evennia_delay(delay_seconds, _wrapped_callback, *args, **kwargs) if _use_live_delay() else _DeferredTask(callback=_wrapped_callback)

    record = {
        "job_id": job_id,
        "key": normalized_key,
        "callback": callback,
        "wrapped_callback": _wrapped_callback,
        "args": tuple(args),
        "kwargs": dict(kwargs),
        "source": metadata["source"],
        "timing_mode": metadata["timing_mode"],
        "delay_s": delay_seconds,
        "due_at": due_at,
        "task": task,
    }

    with _LOCK:
        _ACTIVE_JOBS[job_id] = record
        if normalized_key:
            _KEY_TO_JOB_ID[normalized_key] = job_id
        _update_queue_metrics()

    increment_counter("scheduler.schedule")
    logger.log_info(f"[Scheduler] {metadata['source']} scheduled (delay={delay_seconds:.2f}s key={normalized_key or '-'})")
    return task


def cancel(key):
    normalized_key = _normalize_key(key)
    if not normalized_key:
        return False
    with _LOCK:
        job_id = _KEY_TO_JOB_ID.get(normalized_key)
        record = _ACTIVE_JOBS.get(job_id) if job_id else None
        if not record:
            return False
        _pop_job(job_id)
    increment_counter("scheduler.cancel")
    return _cancel_task(record.get("task"))


def reschedule(key, delay):
    normalized_key = _normalize_key(key)
    if not normalized_key:
        return None
    with _LOCK:
        job_id = _KEY_TO_JOB_ID.get(normalized_key)
        record = _ACTIVE_JOBS.get(job_id) if job_id else None
    if not record:
        return None
    cancel(normalized_key)
    increment_counter("scheduler.reschedule")
    return schedule(
        delay,
        record["callback"],
        key=normalized_key,
        *record["args"],
        source=record.get("source", ""),
        timing_mode=record.get("timing_mode", "scheduled"),
        **record["kwargs"],
    )


def get_scheduler_snapshot():
    with _LOCK:
        active_jobs = [
            {
                "job_id": job_id,
                "key": record.get("key"),
                "source": record.get("source"),
                "timing_mode": record.get("timing_mode"),
                "delay_s": float(record.get("delay_s", 0.0) or 0.0),
                "due_at": float(record.get("due_at", 0.0) or 0.0),
            }
            for job_id, record in _ACTIVE_JOBS.items()
        ]
    return {
        "active_jobs": active_jobs,
        "active_job_count": len(active_jobs),
    }


def flush_due(now=None):
    target_time = float(now if now is not None else time.time())
    with _LOCK:
        due_job_ids = [
            job_id
            for job_id, record in _ACTIVE_JOBS.items()
            if isinstance(record.get("task"), _DeferredTask)
            and float(record.get("due_at", 0.0) or 0.0) <= target_time
            and not getattr(record.get("task"), "cancelled", False)
        ]
    executed = 0
    for job_id in due_job_ids:
        if _execute_job(job_id):
            executed += 1
    return executed
