"""Thin scheduler wrapper used for engine-timed work."""

from __future__ import annotations

import re
from threading import RLock
import time
from uuid import uuid4

from evennia.utils import delay as evennia_delay
from evennia.utils import logger

from world.systems.interest import add_scheduled_interest, remove_scheduled_interest
from world.systems.metrics import increment_counter, measure, observe_max, record_event, set_gauge
from world.systems.time_model import SCHEDULED_EXPIRY, VALID_TIMING_MODES


_LOCK = RLock()
_ACTIVE_JOBS = {}
_KEY_TO_JOB_ID = {}
_SCHEDULER_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*){2,}$")
_WARNED_MESSAGES = set()
DEFAULT_INACTIVE_POLICY = "defer"
VALID_INACTIVE_POLICIES = {"skip", "defer"}
DEFAULT_INACTIVE_DEFER_DELAY = 0.25
DEFAULT_MAX_INACTIVE_DEFERS = 3


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


def _warn_once(message):
    text = str(message or "").strip()
    if not text:
        return
    with _LOCK:
        if text in _WARNED_MESSAGES:
            return
        _WARNED_MESSAGES.add(text)
    logger.log_warn(text)


def _normalize_system_name(system, fallback):
    normalized = str(system or fallback or "").strip().lower()
    return normalized or str(fallback or "callback").strip().lower() or "callback"


def _normalize_timing_mode(timing_mode):
    normalized = str(timing_mode or "").strip().lower()
    if not normalized:
        return SCHEDULED_EXPIRY
    if normalized not in VALID_TIMING_MODES:
        _warn_once(f"[Scheduler] Unknown timing mode '{normalized}', defaulting to {SCHEDULED_EXPIRY}.")
        return SCHEDULED_EXPIRY
    return normalized


def _normalize_inactive_policy(inactive_policy):
    normalized = str(inactive_policy or "").strip().lower() or DEFAULT_INACTIVE_POLICY
    if normalized not in VALID_INACTIVE_POLICIES:
        _warn_once(f"[Scheduler] Unknown inactive policy '{normalized}', defaulting to {DEFAULT_INACTIVE_POLICY}.")
        return DEFAULT_INACTIVE_POLICY
    return normalized


def _is_canonical_scheduler_key(key):
    if not key:
        return False
    return bool(_SCHEDULER_KEY_RE.match(str(key)))


def _build_metadata(delay_seconds, callback, key=None, system="", source="", timing_mode=""):
    callback_name = getattr(callback, "__name__", "callback")
    normalized_key = _normalize_key(key)
    normalized_system = _normalize_system_name(system or source, callback_name)
    normalized_timing_mode = _normalize_timing_mode(timing_mode)

    if not str(system or source or "").strip():
        _warn_once(f"[Scheduler] Missing explicit system/source metadata for callback={callback_name}; normalized to {normalized_system}.")
    if not str(timing_mode or "").strip():
        _warn_once(f"[Scheduler] Missing explicit timing_mode metadata for system={normalized_system}; defaulting to {normalized_timing_mode}.")

    if normalized_timing_mode == SCHEDULED_EXPIRY and not normalized_key:
        _warn_once(f"[Scheduler] Missing stable key for scheduled expiry system={normalized_system}")
    elif normalized_key and not _is_canonical_scheduler_key(normalized_key):
        _warn_once(f"[Scheduler] Non-canonical scheduler key for system={normalized_system}: {normalized_key}")

    return {
        "key": normalized_key,
        "system": normalized_system,
        "source": normalized_system,
        "timing_mode": normalized_timing_mode,
        "delay_s": delay_seconds,
    }


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


def _resolve_interest_object(callback, keep_active_obj=None):
    candidate = keep_active_obj if keep_active_obj is not None else getattr(callback, "__self__", None)
    if candidate is None:
        return None
    if getattr(candidate, "id", None) is None and getattr(candidate, "dbref", None) is None:
        return None
    return candidate


def _sync_scheduled_interest_add(record):
    interest_obj = record.get("interest_obj")
    if interest_obj is None:
        return
    try:
        add_scheduled_interest(
            interest_obj,
            schedule_key=record.get("key"),
            system=record.get("system", record.get("source", "")),
            job_id=record.get("job_id"),
        )
    except Exception as error:
        logger.log_warn(f"[Scheduler] Failed to add scheduled interest for {record.get('job_id')}: {error}")


def _sync_scheduled_interest_remove(record):
    if not record:
        return
    interest_obj = record.get("interest_obj")
    if interest_obj is None:
        return
    try:
        remove_scheduled_interest(
            interest_obj,
            schedule_key=record.get("key"),
            system=record.get("system", record.get("source", "")),
            job_id=record.get("job_id"),
        )
    except Exception as error:
        logger.log_warn(f"[Scheduler] Failed to remove scheduled interest for {record.get('job_id')}: {error}")


def _should_execute_record(record):
    interest_obj = record.get("interest_obj")
    if interest_obj is None:
        return True, "no-interest-owner"
    try:
        from world.systems.interest import is_active

        if not is_active(interest_obj):
            return False, "inactive"
    except Exception as error:
        logger.log_warn(f"[Scheduler] Activation check failed for {record.get('job_id')}: {error}")
    return True, "active"


def _build_inactive_metadata(record, reason):
    return {
        "job_id": record.get("job_id"),
        "key": record.get("key"),
        "system": record.get("system", record.get("source", "")),
        "source": record.get("source"),
        "timing_mode": record.get("timing_mode"),
        "reason": str(reason or "inactive").strip().lower() or "inactive",
        "inactive_policy": record.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
        "inactive_defer_count": int(record.get("inactive_defer_count", 0) or 0),
    }


def _skip_job(job_id, reason):
    skipped_record = None
    with _LOCK:
        skipped_record = _pop_job(job_id)
    _sync_scheduled_interest_remove(skipped_record)
    if not skipped_record:
        return False
    metadata = _build_inactive_metadata(skipped_record, reason)
    increment_counter("scheduler.skip")
    increment_counter(f"scheduler.skip.{metadata['reason']}")
    record_event("scheduler.skip", 0.0, metadata=metadata)
    logger.log_info(
        f"[Scheduler] skipped job system={metadata['system']} key={metadata['key'] or '-'} reason={metadata['reason']}"
    )
    return False


def _defer_job(job_id, reason):
    deferred_record = None
    with _LOCK:
        deferred_record = _pop_job(job_id)
    if not deferred_record:
        return False

    _sync_scheduled_interest_remove(deferred_record)
    _cancel_task(deferred_record.get("task"))

    current_defer_count = int(deferred_record.get("inactive_defer_count", 0) or 0)
    max_inactive_defers = int(deferred_record.get("max_inactive_defers", DEFAULT_MAX_INACTIVE_DEFERS) or DEFAULT_MAX_INACTIVE_DEFERS)
    if current_defer_count >= max_inactive_defers:
        return _skip_job(job_id, f"{reason}-max-defer")

    defer_delay = max(0.05, float(deferred_record.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY) or DEFAULT_INACTIVE_DEFER_DELAY))
    metadata = _build_inactive_metadata(deferred_record, reason)
    metadata["inactive_defer_count"] = current_defer_count + 1
    metadata["defer_delay_s"] = defer_delay

    increment_counter("scheduler.defer")
    increment_counter(f"scheduler.defer.{metadata['reason']}")
    record_event("scheduler.defer", 0.0, metadata=metadata)
    logger.log_info(
        f"[Scheduler] deferred job system={metadata['system']} key={metadata['key'] or '-'} reason={metadata['reason']} delay={defer_delay:.2f}s"
    )

    schedule(
        defer_delay,
        deferred_record["callback"],
        key=deferred_record.get("key"),
        *deferred_record.get("args", ()),
        system=deferred_record.get("system", deferred_record.get("source", "")),
        timing_mode=deferred_record.get("timing_mode", SCHEDULED_EXPIRY),
        keep_active_obj=deferred_record.get("interest_obj"),
        inactive_policy=deferred_record.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
        inactive_defer_delay=deferred_record.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY),
        max_inactive_defers=max_inactive_defers,
        inactive_defer_count=current_defer_count + 1,
        **deferred_record.get("kwargs", {}),
    )
    return False


def _execute_job(job_id):
    cancelled_record = None
    execution_record = None
    with _LOCK:
        record = _ACTIVE_JOBS.get(job_id)
        if not record:
            return False
        task = record.get("task")
        if getattr(task, "cancelled", False):
            cancelled_record = _pop_job(job_id)
        else:
            execution_record = dict(record)
    if cancelled_record:
        _sync_scheduled_interest_remove(cancelled_record)
        return False
    if not execution_record:
        return False
    should_execute, reason = _should_execute_record(execution_record)
    if not should_execute:
        inactive_policy = str(execution_record.get("inactive_policy", DEFAULT_INACTIVE_POLICY) or DEFAULT_INACTIVE_POLICY).strip().lower()
        if inactive_policy == "defer":
            return _defer_job(job_id, reason)
        return _skip_job(job_id, reason)
    with _LOCK:
        record = _ACTIVE_JOBS.get(job_id)
        if not record:
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


def schedule(
    delay,
    callback,
    key=None,
    *args,
    source="",
    system="",
    timing_mode="",
    keep_active_obj=None,
    inactive_policy=DEFAULT_INACTIVE_POLICY,
    inactive_defer_delay=DEFAULT_INACTIVE_DEFER_DELAY,
    max_inactive_defers=DEFAULT_MAX_INACTIVE_DEFERS,
    inactive_defer_count=0,
    **kwargs,
):
    delay_seconds = max(0.0, float(delay or 0.0))
    metadata = _build_metadata(
        delay_seconds,
        callback,
        key=key,
        system=system,
        source=source,
        timing_mode=timing_mode,
    )
    normalized_key = metadata["key"]
    interest_obj = _resolve_interest_object(callback, keep_active_obj=keep_active_obj)
    normalized_inactive_policy = _normalize_inactive_policy(inactive_policy)

    if normalized_key:
        cancel(normalized_key)

    job_id = uuid4().hex

    def _wrapped_callback(*cb_args, **cb_kwargs):
        increment_counter("scheduler.execute")
        popped_record = None
        try:
            with measure("scheduler.execute", metadata=metadata):
                return callback(*cb_args, **cb_kwargs)
        finally:
            with _LOCK:
                popped_record = _pop_job(job_id)
            _sync_scheduled_interest_remove(popped_record)

    due_at = time.time() + delay_seconds
    task = evennia_delay(delay_seconds, _wrapped_callback, *args, **kwargs) if _use_live_delay() else _DeferredTask(callback=_wrapped_callback)

    record = {
        "job_id": job_id,
        "key": normalized_key,
        "callback": callback,
        "wrapped_callback": _wrapped_callback,
        "args": tuple(args),
        "kwargs": dict(kwargs),
        "system": metadata["system"],
        "source": metadata["source"],
        "timing_mode": metadata["timing_mode"],
        "delay_s": delay_seconds,
        "due_at": due_at,
        "task": task,
        "interest_obj": interest_obj,
        "inactive_policy": normalized_inactive_policy,
        "inactive_defer_delay": max(0.05, float(inactive_defer_delay or DEFAULT_INACTIVE_DEFER_DELAY)),
        "max_inactive_defers": max(0, int(max_inactive_defers or 0)),
        "inactive_defer_count": max(0, int(inactive_defer_count or 0)),
    }

    with _LOCK:
        _ACTIVE_JOBS[job_id] = record
        if normalized_key:
            _KEY_TO_JOB_ID[normalized_key] = job_id
        _update_queue_metrics()

    _sync_scheduled_interest_add(record)

    increment_counter("scheduler.schedule")
    increment_counter(f"scheduler.schedule.{metadata['timing_mode']}")
    logger.log_info(f"[Scheduler] {metadata['system']} scheduled (delay={delay_seconds:.2f}s key={normalized_key or '-'})")
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
        record = _pop_job(job_id)
    _sync_scheduled_interest_remove(record)
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
        system=record.get("system", record.get("source", "")),
        timing_mode=record.get("timing_mode", SCHEDULED_EXPIRY),
        keep_active_obj=record.get("interest_obj"),
        inactive_policy=record.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
        inactive_defer_delay=record.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY),
        max_inactive_defers=record.get("max_inactive_defers", DEFAULT_MAX_INACTIVE_DEFERS),
        inactive_defer_count=record.get("inactive_defer_count", 0),
        **record["kwargs"],
    )


def get_scheduler_snapshot():
    with _LOCK:
        active_jobs = [
            {
                "job_id": job_id,
                "key": record.get("key"),
                "system": record.get("system", record.get("source")),
                "source": record.get("source"),
                "timing_mode": record.get("timing_mode"),
                "delay_s": float(record.get("delay_s", 0.0) or 0.0),
                "due_at": float(record.get("due_at", 0.0) or 0.0),
                "interest_object_key": (
                    f"#{int(record['interest_obj'].id)}"
                    if record.get("interest_obj") is not None and getattr(record.get("interest_obj"), "id", None) is not None
                    else None
                ),
                "interest_object_label": (
                    getattr(record.get("interest_obj"), "key", None) if record.get("interest_obj") is not None else None
                ),
                "inactive_policy": record.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
                "inactive_defer_count": int(record.get("inactive_defer_count", 0) or 0),
            }
            for job_id, record in _ACTIVE_JOBS.items()
        ]
    return {
        "active_jobs": active_jobs,
        "active_job_count": len(active_jobs),
    }


def flush_due(now=None):
    target_time = float(now if now is not None else time.time())
    increment_counter("scheduler.flush")
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
    if executed:
        increment_counter("scheduler.flush.executed", executed)
    return executed
