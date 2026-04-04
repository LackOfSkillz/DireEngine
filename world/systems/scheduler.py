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
_DELAYED_RETRY_JOBS = {}
_DELAYED_KEY_TO_JOB_ID = {}
_SCHEDULER_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*){2,}$")
_SYSTEM_METRIC_KEY_RE = re.compile(r"[^a-z0-9]+")
_WARNED_MESSAGES = set()
_SYSTEM_GAUGE_KEYS = set()
DEFAULT_INACTIVE_POLICY = "defer"
VALID_INACTIVE_POLICIES = {"skip", "defer"}
DEFAULT_INACTIVE_DEFER_DELAY = 0.25
DEFAULT_MAX_INACTIVE_DEFERS = 3
DEFAULT_KEY_CONFLICT_POLICY = "replace"
VALID_KEY_CONFLICT_POLICIES = {"replace", "reject"}
MAX_JOBS_PER_OWNER = 5
MAX_JOBS_PER_SYSTEM = 100
MAX_TOTAL_JOBS = 1000
DEFAULT_QUOTA_BEHAVIOR = "reject"
VALID_QUOTA_BEHAVIORS = {"reject", "replace_oldest", "delay"}
OWNER_QUOTA_BEHAVIOR = DEFAULT_QUOTA_BEHAVIOR
SYSTEM_QUOTA_BEHAVIOR = DEFAULT_QUOTA_BEHAVIOR
GLOBAL_QUOTA_BEHAVIOR = DEFAULT_QUOTA_BEHAVIOR
DEFAULT_QUOTA_DELAY_SECONDS = 0.25
DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS = 3


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
    normalized = str(system or "").strip().lower()
    if normalized:
        return normalized
    fallback_name = str(fallback or "").strip().lower()
    return fallback_name or None


def _normalize_owner(owner):
    if owner is None:
        return None, None, None

    owner_id = getattr(owner, "id", None)
    if owner_id is not None:
        owner_ref = f"#{int(owner_id)}"
        owner_label = str(getattr(owner, "key", owner_ref) or owner_ref)
        return owner, owner_ref, owner_label

    dbref = str(getattr(owner, "dbref", "") or "").strip()
    if dbref:
        owner_label = str(getattr(owner, "key", dbref) or dbref)
        return owner, dbref, owner_label

    normalized = str(owner or "").strip()
    if not normalized:
        return None, None, None
    return None, normalized, normalized


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


def _normalize_key_conflict_policy(key_conflict):
    normalized = str(key_conflict or "").strip().lower() or DEFAULT_KEY_CONFLICT_POLICY
    if normalized not in VALID_KEY_CONFLICT_POLICIES:
        _warn_once(f"[Scheduler] Unknown key conflict policy '{normalized}', defaulting to {DEFAULT_KEY_CONFLICT_POLICY}.")
        return DEFAULT_KEY_CONFLICT_POLICY
    return normalized


def _normalize_quota_behavior(behavior):
    normalized = str(behavior or "").strip().lower() or DEFAULT_QUOTA_BEHAVIOR
    if normalized not in VALID_QUOTA_BEHAVIORS:
        _warn_once(f"[Scheduler] Unknown quota behavior '{normalized}', defaulting to {DEFAULT_QUOTA_BEHAVIOR}.")
        return DEFAULT_QUOTA_BEHAVIOR
    return normalized


def _is_canonical_scheduler_key(key):
    if not key:
        return False
    return bool(_SCHEDULER_KEY_RE.match(str(key)))


def _build_metadata(delay_seconds, callback, key=None, owner=None, system="", source="", timing_mode=""):
    callback_name = getattr(callback, "__name__", "callback")
    normalized_key = _normalize_key(key)
    normalized_system = _normalize_system_name(system or source, None)
    normalized_timing_mode = _normalize_timing_mode(timing_mode)
    _, owner_ref, owner_label = _normalize_owner(owner)

    if not normalized_system and not owner_ref:
        raise ValueError(f"Scheduler jobs require owner or system metadata: callback={callback_name}")
    if not str(timing_mode or "").strip():
        _warn_once(
            f"[Scheduler] Missing explicit timing_mode metadata for system={normalized_system or '-'} owner={owner_ref or '-'}; defaulting to {normalized_timing_mode}."
        )

    if normalized_timing_mode == SCHEDULED_EXPIRY and not normalized_key:
        _warn_once(f"[Scheduler] Missing stable key for scheduled expiry system={normalized_system or '-'} owner={owner_ref or '-'}")
    elif normalized_key and not _is_canonical_scheduler_key(normalized_key):
        _warn_once(f"[Scheduler] Non-canonical scheduler key for system={normalized_system or '-'} owner={owner_ref or '-'}: {normalized_key}")

    return {
        "key": normalized_key,
        "system": normalized_system,
        "source": normalized_system,
        "owner": owner_ref,
        "owner_label": owner_label,
        "timing_mode": normalized_timing_mode,
        "delay_s": delay_seconds,
        "created_at": time.time(),
    }


def _update_queue_metrics():
    current = len(_ACTIVE_JOBS)
    delayed_current = len(_DELAYED_RETRY_JOBS)
    by_system = {}
    for record in _ACTIVE_JOBS.values():
        system_name = str(record.get("system", record.get("source", "")) or "").strip().lower()
        if not system_name:
            continue
        by_system[system_name] = int(by_system.get(system_name, 0) or 0) + 1

    set_gauge("scheduler.queue.current", current)
    observe_max("scheduler.queue.peak", current)
    set_gauge("scheduler.delay_queue.current", delayed_current)
    observe_max("scheduler.delay_queue.peak", delayed_current)

    gauge_keys = set()
    for system_name, count in by_system.items():
        metric_suffix = _SYSTEM_METRIC_KEY_RE.sub("_", system_name).strip("_") or "unknown"
        gauge_key = f"scheduler.queue.system.{metric_suffix}"
        set_gauge(gauge_key, count)
        gauge_keys.add(gauge_key)

    stale_gauge_keys = _SYSTEM_GAUGE_KEYS.difference(gauge_keys)
    for gauge_key in stale_gauge_keys:
        set_gauge(gauge_key, 0)

    _SYSTEM_GAUGE_KEYS.clear()
    _SYSTEM_GAUGE_KEYS.update(gauge_keys)
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


def _pop_delayed_retry(job_id):
    record = _DELAYED_RETRY_JOBS.pop(job_id, None)
    if not record:
        _update_queue_metrics()
        return None
    key = record.get("key")
    if key and _DELAYED_KEY_TO_JOB_ID.get(key) == job_id:
        _DELAYED_KEY_TO_JOB_ID.pop(key, None)
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


def _resolve_owner(owner=None, callback=None, keep_active_obj=None):
    explicit_owner, explicit_owner_ref, explicit_owner_label = _normalize_owner(owner)
    if explicit_owner_ref:
        return explicit_owner, explicit_owner_ref, explicit_owner_label

    interest_obj = _resolve_interest_object(callback, keep_active_obj=keep_active_obj)
    resolved_owner, resolved_owner_ref, resolved_owner_label = _normalize_owner(interest_obj)
    if resolved_owner_ref:
        return resolved_owner, resolved_owner_ref, resolved_owner_label

    return None, None, None


def _build_rejection_metadata(record_or_metadata, reason, **extra):
    payload = dict(record_or_metadata or {})
    payload.update(extra)
    return {
        "job_id": payload.get("job_id"),
        "key": payload.get("key"),
        "system": payload.get("system", payload.get("source")),
        "owner": payload.get("owner"),
        "owner_label": payload.get("owner_label"),
        "timing_mode": payload.get("timing_mode"),
        "reason": str(reason or "rejected").strip().lower() or "rejected",
        "quota_scope": payload.get("quota_scope"),
        "quota_behavior": payload.get("quota_behavior"),
        "quota_limit": payload.get("quota_limit"),
        "quota_current_count": payload.get("quota_current_count"),
        "total_jobs": payload.get("total_jobs"),
    }


def _build_schedule_request(
    delay_seconds,
    callback,
    *,
    key,
    args,
    kwargs,
    owner_obj,
    owner_ref,
    owner_label,
    source,
    system,
    timing_mode,
    keep_active_obj,
    key_conflict,
    inactive_policy,
    inactive_defer_delay,
    max_inactive_defers,
    inactive_defer_count,
    quota_delay_attempt,
    quota_delay_seconds,
    max_quota_delay_attempts,
):
    return {
        "delay_s": delay_seconds,
        "callback": callback,
        "key": key,
        "args": tuple(args),
        "kwargs": dict(kwargs),
        "owner_obj": owner_obj,
        "owner": owner_ref,
        "owner_label": owner_label,
        "source": source,
        "system": system,
        "timing_mode": timing_mode,
        "keep_active_obj": keep_active_obj,
        "key_conflict": key_conflict,
        "inactive_policy": inactive_policy,
        "inactive_defer_delay": inactive_defer_delay,
        "max_inactive_defers": max_inactive_defers,
        "inactive_defer_count": inactive_defer_count,
        "quota_delay_attempt": quota_delay_attempt,
        "quota_delay_seconds": quota_delay_seconds,
        "max_quota_delay_attempts": max_quota_delay_attempts,
    }


def _reject_job(record_or_metadata, reason, **extra):
    metadata = _build_rejection_metadata(record_or_metadata, reason, **extra)
    increment_counter("scheduler.reject")
    increment_counter(f"scheduler.reject.{metadata['reason']}")
    record_event("scheduler.reject", 0.0, metadata=metadata)
    logger.log_warn(
        f"[Scheduler] rejected job system={metadata['system'] or '-'} owner={metadata['owner'] or '-'} key={metadata['key'] or '-'} reason={metadata['reason']}"
    )
    return None


def _find_oldest_job_id_locked(scope, owner=None, system=None):
    scope_name = str(scope or "").strip().lower()
    owner_ref = str(owner or "").strip()
    system_name = str(system or "").strip().lower()
    candidates = []

    for job_id, record in _ACTIVE_JOBS.items():
        if scope_name == "owner":
            if not owner_ref or str(record.get("owner", "") or "").strip() != owner_ref:
                continue
        elif scope_name == "system":
            if not system_name or str(record.get("system", "") or "").strip().lower() != system_name:
                continue
        elif scope_name != "global":
            continue

        candidates.append(
            (
                float(record.get("created_at", 0.0) or 0.0),
                float(record.get("due_at", 0.0) or 0.0),
                str(job_id),
            )
        )

    if not candidates:
        return None
    candidates.sort()
    return candidates[0][2]


def _replace_oldest_for_quota(record_or_metadata, violation):
    payload = dict(violation or {})
    evicted_record = None
    with _LOCK:
        oldest_job_id = _find_oldest_job_id_locked(payload.get("scope"), owner=payload.get("owner"), system=payload.get("system"))
        if oldest_job_id:
            evicted_record = _pop_job(oldest_job_id)

    if not evicted_record:
        _reject_job(
            record_or_metadata,
            payload.get("reason", "quota"),
            quota_scope=payload.get("scope"),
            quota_behavior=payload.get("behavior"),
            quota_limit=payload.get("limit"),
            quota_current_count=payload.get("current_count"),
            total_jobs=payload.get("total_jobs"),
        )
        return False

    _sync_scheduled_interest_remove(evicted_record)
    _cancel_task(evicted_record.get("task"))
    metadata = {
        "reason": str(payload.get("reason", "quota") or "quota").strip().lower() or "quota",
        "quota_scope": payload.get("scope"),
        "quota_behavior": _normalize_quota_behavior(payload.get("behavior", DEFAULT_QUOTA_BEHAVIOR)),
        "quota_limit": payload.get("limit"),
        "quota_current_count": payload.get("current_count"),
        "total_jobs": payload.get("total_jobs"),
        "evicted_job_id": evicted_record.get("job_id"),
        "evicted_key": evicted_record.get("key"),
        "evicted_owner": evicted_record.get("owner"),
        "evicted_system": evicted_record.get("system", evicted_record.get("source")),
        "new_key": dict(record_or_metadata or {}).get("key"),
        "new_owner": dict(record_or_metadata or {}).get("owner"),
        "new_system": dict(record_or_metadata or {}).get("system", dict(record_or_metadata or {}).get("source")),
    }
    increment_counter("scheduler.replace")
    increment_counter(f"scheduler.replace.{metadata['reason']}")
    record_event("scheduler.replace", 0.0, metadata=metadata)
    logger.log_warn(
        f"[Scheduler] replaced queued job scope={metadata['quota_scope'] or '-'} evicted_key={metadata['evicted_key'] or '-'} new_key={metadata['new_key'] or '-'} reason={metadata['reason']}"
    )
    return True


def _retry_delayed_schedule(job_id):
    delayed_record = None
    with _LOCK:
        delayed_record = _DELAYED_RETRY_JOBS.get(job_id)
        if not delayed_record:
            return False
        task = delayed_record.get("task")
        if getattr(task, "cancelled", False):
            _pop_delayed_retry(job_id)
            return False
        delayed_record = _pop_delayed_retry(job_id)
    if not delayed_record:
        return False

    increment_counter("scheduler.delay.execute")
    request = dict(delayed_record.get("request", {}) or {})
    schedule(
        request.get("delay_s", 0.0),
        request.get("callback"),
        key=request.get("key"),
        *request.get("args", ()),
        owner=request.get("owner_obj") or request.get("owner"),
        source=request.get("source", ""),
        system=request.get("system", ""),
        timing_mode=request.get("timing_mode", ""),
        keep_active_obj=request.get("keep_active_obj"),
        key_conflict=request.get("key_conflict", DEFAULT_KEY_CONFLICT_POLICY),
        inactive_policy=request.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
        inactive_defer_delay=request.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY),
        max_inactive_defers=request.get("max_inactive_defers", DEFAULT_MAX_INACTIVE_DEFERS),
        inactive_defer_count=request.get("inactive_defer_count", 0),
        quota_delay_attempt=request.get("quota_delay_attempt", 0),
        quota_delay_seconds=request.get("quota_delay_seconds", DEFAULT_QUOTA_DELAY_SECONDS),
        max_quota_delay_attempts=request.get("max_quota_delay_attempts", DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS),
        **request.get("kwargs", {}),
    )
    return True


def _queue_delayed_retry(record_or_metadata, violation):
    request = dict(record_or_metadata or {})
    payload = dict(violation or {})
    current_attempt = int(request.get("quota_delay_attempt", 0) or 0)
    max_attempts = max(1, int(request.get("max_quota_delay_attempts", DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS) or DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS))
    if current_attempt >= max_attempts:
        _reject_job(
            request,
            payload.get("reason", "quota"),
            quota_scope=payload.get("scope"),
            quota_behavior="delay",
            quota_limit=payload.get("limit"),
            quota_current_count=payload.get("current_count"),
            total_jobs=payload.get("total_jobs"),
            quota_delay_attempt=current_attempt,
        )
        return False

    delayed_seconds = max(0.05, float(request.get("quota_delay_seconds", DEFAULT_QUOTA_DELAY_SECONDS) or DEFAULT_QUOTA_DELAY_SECONDS))
    delayed_request = dict(request)
    delayed_request["quota_delay_attempt"] = current_attempt + 1
    delayed_job_id = uuid4().hex
    due_at = time.time() + delayed_seconds

    def _retry_callback():
        return _retry_delayed_schedule(delayed_job_id)

    task = evennia_delay(delayed_seconds, _retry_callback) if _use_live_delay() else _DeferredTask(callback=_retry_callback)
    delayed_record = {
        "job_id": delayed_job_id,
        "key": request.get("key"),
        "owner": request.get("owner"),
        "owner_label": request.get("owner_label"),
        "system": request.get("system", request.get("source")),
        "source": request.get("source", request.get("system", "")),
        "timing_mode": request.get("timing_mode"),
        "delay_s": delayed_seconds,
        "created_at": time.time(),
        "due_at": due_at,
        "task": task,
        "request": delayed_request,
        "reason": str(payload.get("reason", "quota") or "quota").strip().lower() or "quota",
        "quota_scope": payload.get("scope"),
        "quota_behavior": "delay",
        "quota_limit": payload.get("limit"),
        "quota_current_count": payload.get("current_count"),
        "total_jobs": payload.get("total_jobs"),
    }

    with _LOCK:
        _DELAYED_RETRY_JOBS[delayed_job_id] = delayed_record
        if delayed_record.get("key"):
            _DELAYED_KEY_TO_JOB_ID[delayed_record["key"]] = delayed_job_id
        _update_queue_metrics()

    metadata = {
        "job_id": delayed_job_id,
        "key": delayed_record.get("key"),
        "system": delayed_record.get("system"),
        "owner": delayed_record.get("owner"),
        "owner_label": delayed_record.get("owner_label"),
        "timing_mode": delayed_record.get("timing_mode"),
        "reason": delayed_record.get("reason"),
        "quota_scope": delayed_record.get("quota_scope"),
        "quota_behavior": delayed_record.get("quota_behavior"),
        "quota_limit": delayed_record.get("quota_limit"),
        "quota_current_count": delayed_record.get("quota_current_count"),
        "total_jobs": delayed_record.get("total_jobs"),
        "quota_delay_attempt": delayed_request.get("quota_delay_attempt", 0),
        "quota_delay_seconds": delayed_seconds,
    }
    increment_counter("scheduler.delay")
    increment_counter(f"scheduler.delay.{metadata['reason']}")
    record_event("scheduler.delay", 0.0, metadata=metadata)
    logger.log_warn(
        f"[Scheduler] delayed job system={metadata['system'] or '-'} owner={metadata['owner'] or '-'} key={metadata['key'] or '-'} reason={metadata['reason']} attempt={metadata['quota_delay_attempt']} delay={delayed_seconds:.2f}s"
    )
    return False


def _build_quota_state_locked(owner=None, system=None):
    owner_ref = str(owner or "").strip()
    system_name = str(system or "").strip()
    owner_count = 0
    system_count = 0
    total_jobs = len(_ACTIVE_JOBS)

    for record in _ACTIVE_JOBS.values():
        if owner_ref and str(record.get("owner", "") or "").strip() == owner_ref:
            owner_count += 1
        if system_name and str(record.get("system", "") or "").strip() == system_name:
            system_count += 1

    return {
        "owner": owner_ref or None,
        "owner_count": owner_count,
        "system": system_name or None,
        "system_count": system_count,
        "total_jobs": total_jobs,
    }


def _check_quota_violation_locked(owner=None, system=None):
    quota_state = _build_quota_state_locked(owner=owner, system=system)

    if quota_state["owner"] and quota_state["owner_count"] >= int(MAX_JOBS_PER_OWNER or 0):
        return {
            "reason": "owner-quota",
            "scope": "owner",
            "behavior": _normalize_quota_behavior(OWNER_QUOTA_BEHAVIOR),
            "limit": int(MAX_JOBS_PER_OWNER or 0),
            "current_count": quota_state["owner_count"],
            "owner": quota_state["owner"],
            "system": quota_state["system"],
            "total_jobs": quota_state["total_jobs"],
        }

    if quota_state["system"] and quota_state["system_count"] >= int(MAX_JOBS_PER_SYSTEM or 0):
        return {
            "reason": "system-quota",
            "scope": "system",
            "behavior": _normalize_quota_behavior(SYSTEM_QUOTA_BEHAVIOR),
            "limit": int(MAX_JOBS_PER_SYSTEM or 0),
            "current_count": quota_state["system_count"],
            "owner": quota_state["owner"],
            "system": quota_state["system"],
            "total_jobs": quota_state["total_jobs"],
        }

    if quota_state["total_jobs"] >= int(MAX_TOTAL_JOBS or 0):
        return {
            "reason": "global-quota",
            "scope": "global",
            "behavior": _normalize_quota_behavior(GLOBAL_QUOTA_BEHAVIOR),
            "limit": int(MAX_TOTAL_JOBS or 0),
            "current_count": quota_state["total_jobs"],
            "owner": quota_state["owner"],
            "system": quota_state["system"],
            "total_jobs": quota_state["total_jobs"],
        }

    return None


def _apply_quota_violation(record_or_metadata, violation):
    payload = dict(violation or {})
    behavior = _normalize_quota_behavior(payload.get("behavior", DEFAULT_QUOTA_BEHAVIOR))
    if behavior == "reject":
        _reject_job(
            record_or_metadata,
            payload.get("reason", "quota"),
            quota_scope=payload.get("scope"),
            quota_behavior=behavior,
            quota_limit=payload.get("limit"),
            quota_current_count=payload.get("current_count"),
            total_jobs=payload.get("total_jobs"),
        )
        return False
    if behavior == "replace_oldest":
        return _replace_oldest_for_quota(record_or_metadata, payload)
    if behavior == "delay":
        return _queue_delayed_retry(record_or_metadata, payload)
    _reject_job(record_or_metadata, payload.get("reason", "quota"))
    return False


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
        "owner": record.get("owner"),
        "owner_label": record.get("owner_label"),
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
        owner=deferred_record.get("owner_obj") or deferred_record.get("owner") or deferred_record.get("interest_obj"),
        system=deferred_record.get("system", deferred_record.get("source", "")),
        timing_mode=deferred_record.get("timing_mode", SCHEDULED_EXPIRY),
        keep_active_obj=deferred_record.get("interest_obj"),
        key_conflict=deferred_record.get("key_conflict", DEFAULT_KEY_CONFLICT_POLICY),
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
    owner=None,
    source="",
    system="",
    timing_mode="",
    keep_active_obj=None,
    key_conflict=DEFAULT_KEY_CONFLICT_POLICY,
    inactive_policy=DEFAULT_INACTIVE_POLICY,
    inactive_defer_delay=DEFAULT_INACTIVE_DEFER_DELAY,
    max_inactive_defers=DEFAULT_MAX_INACTIVE_DEFERS,
    inactive_defer_count=0,
    quota_delay_attempt=0,
    quota_delay_seconds=DEFAULT_QUOTA_DELAY_SECONDS,
    max_quota_delay_attempts=DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS,
    **kwargs,
):
    delay_seconds = max(0.0, float(delay or 0.0))
    owner_obj, owner_ref, owner_label = _resolve_owner(owner=owner, callback=callback, keep_active_obj=keep_active_obj)
    metadata = _build_metadata(
        delay_seconds,
        callback,
        key=key,
        owner=owner_ref,
        system=system,
        source=source,
        timing_mode=timing_mode,
    )
    normalized_key = metadata["key"]
    interest_obj = _resolve_interest_object(callback, keep_active_obj=keep_active_obj)
    normalized_inactive_policy = _normalize_inactive_policy(inactive_policy)
    normalized_key_conflict = _normalize_key_conflict_policy(key_conflict)
    schedule_request = _build_schedule_request(
        delay_seconds,
        callback,
        key=normalized_key,
        args=args,
        kwargs=kwargs,
        owner_obj=owner_obj,
        owner_ref=owner_ref,
        owner_label=owner_label,
        source=metadata["source"],
        system=metadata["system"],
        timing_mode=metadata["timing_mode"],
        keep_active_obj=keep_active_obj,
        key_conflict=normalized_key_conflict,
        inactive_policy=normalized_inactive_policy,
        inactive_defer_delay=max(0.05, float(inactive_defer_delay or DEFAULT_INACTIVE_DEFER_DELAY)),
        max_inactive_defers=max(0, int(max_inactive_defers or 0)),
        inactive_defer_count=max(0, int(inactive_defer_count or 0)),
        quota_delay_attempt=max(0, int(quota_delay_attempt or 0)),
        quota_delay_seconds=max(0.05, float(quota_delay_seconds or DEFAULT_QUOTA_DELAY_SECONDS)),
        max_quota_delay_attempts=max(1, int(max_quota_delay_attempts or DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS)),
    )

    if normalized_key:
        with _LOCK:
            existing_job_id = _KEY_TO_JOB_ID.get(normalized_key)
            delayed_job_id = _DELAYED_KEY_TO_JOB_ID.get(normalized_key)
        if existing_job_id or delayed_job_id:
            if normalized_key_conflict == "reject":
                return _reject_job(
                    schedule_request,
                    "duplicate-key",
                )
            cancel(normalized_key)

    with _LOCK:
        quota_violation = _check_quota_violation_locked(owner=owner_ref, system=metadata.get("system"))
    if quota_violation:
        if not _apply_quota_violation(schedule_request, quota_violation):
            return None

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
        "owner": owner_ref,
        "owner_label": owner_label,
        "owner_obj": owner_obj,
        "timing_mode": metadata["timing_mode"],
        "delay_s": delay_seconds,
        "created_at": float(metadata["created_at"]),
        "due_at": due_at,
        "task": task,
        "interest_obj": interest_obj,
        "key_conflict": normalized_key_conflict,
        "inactive_policy": normalized_inactive_policy,
        "inactive_defer_delay": schedule_request["inactive_defer_delay"],
        "max_inactive_defers": schedule_request["max_inactive_defers"],
        "inactive_defer_count": schedule_request["inactive_defer_count"],
    }

    with _LOCK:
        _ACTIVE_JOBS[job_id] = record
        if normalized_key:
            _KEY_TO_JOB_ID[normalized_key] = job_id
        _update_queue_metrics()

    _sync_scheduled_interest_add(record)

    increment_counter("scheduler.schedule")
    increment_counter(f"scheduler.schedule.{metadata['timing_mode']}")
    logger.log_info(
        f"[Scheduler] {metadata['system'] or '-'} scheduled (owner={owner_ref or '-'} delay={delay_seconds:.2f}s key={normalized_key or '-'} conflict={normalized_key_conflict})"
    )
    return task


def cancel(key):
    normalized_key = _normalize_key(key)
    if not normalized_key:
        return False
    with _LOCK:
        job_id = _KEY_TO_JOB_ID.get(normalized_key)
        record = _ACTIVE_JOBS.get(job_id) if job_id else None
        if record:
            record = _pop_job(job_id)
        else:
            delayed_job_id = _DELAYED_KEY_TO_JOB_ID.get(normalized_key)
            record = _pop_delayed_retry(delayed_job_id) if delayed_job_id else None
            if not record:
                return False
    if record.get("interest_obj") is not None:
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
        delayed_job_id = _DELAYED_KEY_TO_JOB_ID.get(normalized_key)
        delayed_record = _DELAYED_RETRY_JOBS.get(delayed_job_id) if delayed_job_id else None
    if not record:
        if not delayed_record:
            return None
        cancel(normalized_key)
        increment_counter("scheduler.reschedule")
        request = dict(delayed_record.get("request", {}) or {})
        return schedule(
            delay,
            request.get("callback"),
            key=normalized_key,
            *request.get("args", ()),
            owner=request.get("owner_obj") or request.get("owner"),
            source=request.get("source", ""),
            system=request.get("system", ""),
            timing_mode=request.get("timing_mode", SCHEDULED_EXPIRY),
            keep_active_obj=request.get("keep_active_obj"),
            key_conflict=request.get("key_conflict", DEFAULT_KEY_CONFLICT_POLICY),
            inactive_policy=request.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
            inactive_defer_delay=request.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY),
            max_inactive_defers=request.get("max_inactive_defers", DEFAULT_MAX_INACTIVE_DEFERS),
            inactive_defer_count=request.get("inactive_defer_count", 0),
            quota_delay_attempt=request.get("quota_delay_attempt", 0),
            quota_delay_seconds=request.get("quota_delay_seconds", DEFAULT_QUOTA_DELAY_SECONDS),
            max_quota_delay_attempts=request.get("max_quota_delay_attempts", DEFAULT_MAX_QUOTA_DELAY_ATTEMPTS),
            **request.get("kwargs", {}),
        )
    cancel(normalized_key)
    increment_counter("scheduler.reschedule")
    return schedule(
        delay,
        record["callback"],
        key=normalized_key,
        *record["args"],
        owner=record.get("owner_obj") or record.get("owner") or record.get("interest_obj"),
        system=record.get("system", record.get("source", "")),
        timing_mode=record.get("timing_mode", SCHEDULED_EXPIRY),
        keep_active_obj=record.get("interest_obj"),
        key_conflict=record.get("key_conflict", DEFAULT_KEY_CONFLICT_POLICY),
        inactive_policy=record.get("inactive_policy", DEFAULT_INACTIVE_POLICY),
        inactive_defer_delay=record.get("inactive_defer_delay", DEFAULT_INACTIVE_DEFER_DELAY),
        max_inactive_defers=record.get("max_inactive_defers", DEFAULT_MAX_INACTIVE_DEFERS),
        inactive_defer_count=record.get("inactive_defer_count", 0),
        **record["kwargs"],
    )


def get_scheduler_snapshot():
    with _LOCK:
        by_owner = {}
        by_system = {}
        active_jobs = [
            {
                "job_id": job_id,
                "key": record.get("key"),
                "owner": record.get("owner"),
                "owner_label": record.get("owner_label"),
                "system": record.get("system", record.get("source")),
                "source": record.get("source"),
                "timing_mode": record.get("timing_mode"),
                "delay_s": float(record.get("delay_s", 0.0) or 0.0),
                "created_at": float(record.get("created_at", 0.0) or 0.0),
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
        delayed_jobs = [
            {
                "job_id": job_id,
                "key": record.get("key"),
                "owner": record.get("owner"),
                "owner_label": record.get("owner_label"),
                "system": record.get("system", record.get("source")),
                "source": record.get("source"),
                "timing_mode": record.get("timing_mode"),
                "delay_s": float(record.get("delay_s", 0.0) or 0.0),
                "created_at": float(record.get("created_at", 0.0) or 0.0),
                "due_at": float(record.get("due_at", 0.0) or 0.0),
                "reason": record.get("reason"),
                "quota_scope": record.get("quota_scope"),
                "quota_behavior": record.get("quota_behavior"),
                "quota_limit": record.get("quota_limit"),
                "quota_current_count": record.get("quota_current_count"),
                "quota_delay_attempt": int((record.get("request", {}) or {}).get("quota_delay_attempt", 0) or 0),
            }
            for job_id, record in _DELAYED_RETRY_JOBS.items()
        ]
        for job in active_jobs:
            owner = str(job.get("owner", "") or "").strip()
            system = str(job.get("system", "") or "").strip()
            if owner:
                by_owner[owner] = int(by_owner.get(owner, 0) or 0) + 1
            if system:
                by_system[system] = int(by_system.get(system, 0) or 0) + 1
    return {
        "active_jobs": active_jobs,
        "delayed_jobs": delayed_jobs,
        "active_job_count": len(active_jobs),
        "delayed_job_count": len(delayed_jobs),
        "total_jobs": len(active_jobs),
        "by_owner": dict(sorted(by_owner.items())),
        "by_system": dict(sorted(by_system.items())),
        "quota_policy": {
            "owner": {"limit": int(MAX_JOBS_PER_OWNER or 0), "behavior": _normalize_quota_behavior(OWNER_QUOTA_BEHAVIOR)},
            "system": {"limit": int(MAX_JOBS_PER_SYSTEM or 0), "behavior": _normalize_quota_behavior(SYSTEM_QUOTA_BEHAVIOR)},
            "global": {"limit": int(MAX_TOTAL_JOBS or 0), "behavior": _normalize_quota_behavior(GLOBAL_QUOTA_BEHAVIOR)},
        },
    }


def flush_due(now=None):
    target_time = float(now if now is not None else time.time())
    increment_counter("scheduler.flush")
    executed = 0
    while True:
        with _LOCK:
            due_delayed_job_ids = [
                job_id
                for job_id, record in _DELAYED_RETRY_JOBS.items()
                if isinstance(record.get("task"), _DeferredTask)
                and float(record.get("due_at", 0.0) or 0.0) <= target_time
                and not getattr(record.get("task"), "cancelled", False)
            ]
            due_job_ids = [
                job_id
                for job_id, record in _ACTIVE_JOBS.items()
                if isinstance(record.get("task"), _DeferredTask)
                and float(record.get("due_at", 0.0) or 0.0) <= target_time
                and not getattr(record.get("task"), "cancelled", False)
            ]
        if not due_delayed_job_ids and not due_job_ids:
            break
        progressed = False
        for job_id in due_delayed_job_ids:
            if _retry_delayed_schedule(job_id):
                progressed = True
        for job_id in due_job_ids:
            if _execute_job(job_id):
                executed += 1
                progressed = True
        if not progressed:
            break
    if executed:
        increment_counter("scheduler.flush.executed", executed)
    return executed
