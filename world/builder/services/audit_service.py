from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import tempfile
from time import time


logger = logging.getLogger(__name__)
AUDIT_AVAILABLE = True
AUDIT_ENABLED = True
AUDIT_SOFT_LIMIT_MB = 5
AUDIT_SOFT_LIMIT_BYTES = AUDIT_SOFT_LIMIT_MB * 1_000_000


def get_audit_log_path() -> Path:
    return Path(__file__).resolve().parent.parent / "audit" / "audit_log_v1.json"


def _load_audit_entries() -> list[dict]:
    audit_path = get_audit_log_path()
    if not audit_path.exists():
        return []
    with audit_path.open("r", encoding="utf-8") as audit_file:
        data = json.load(audit_file)
    if not isinstance(data, list):
        raise ValueError("Audit log must be a list.")
    return data


def _sort_entries(entries: list[dict]) -> list[dict]:
    return sorted(
        list(entries or []),
        key=lambda entry: float(entry.get("timestamp", 0.0) or 0.0),
        reverse=True,
    )


def _apply_limit(entries: list[dict], limit: int | None) -> list[dict]:
    if limit is None:
        return list(entries)
    normalized_limit = int(limit)
    if normalized_limit < 0:
        raise ValueError("limit must be >= 0")
    return list(entries)[:normalized_limit]


def _write_audit_entries(entries: list[dict]) -> None:
    audit_path = get_audit_log_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(audit_path.parent), suffix=".tmp") as temp_file:
            json.dump(entries, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, audit_path)
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def _warn_if_audit_log_large(audit_path: Path) -> None:
    if not audit_path.exists():
        return

    current_size = audit_path.stat().st_size
    if current_size > AUDIT_SOFT_LIMIT_BYTES:
        logger.warning(
            "Builder audit log is growing large: %s bytes exceeds soft limit of %s MB. Rotation is not implemented yet.",
            current_size,
            AUDIT_SOFT_LIMIT_MB,
        )


def log_audit_event(action: str, object_id: int, details: dict):
    if not AUDIT_AVAILABLE or not AUDIT_ENABLED:
        return None

    normalized_action = str(action or "").strip()
    if not normalized_action:
        raise ValueError("action is required.")
    if not isinstance(details, dict):
        raise ValueError("details must be a dict.")

    audit_path = get_audit_log_path()
    _warn_if_audit_log_large(audit_path)

    entry = {
        "timestamp": time(),
        "action": normalized_action,
        "object_id": int(object_id or 0),
        "details": dict(details),
    }
    entries = _load_audit_entries()
    entries.append(entry)
    _write_audit_entries(entries)
    return dict(entry)


def load_audit_log(limit: int | None = None) -> list[dict]:
    # Audit queries are always returned newest-first.
    return _apply_limit(_sort_entries(_load_audit_entries()), limit)


def get_audit_for_object(object_id, limit: int | None = None) -> list[dict]:
    normalized_object_id = int(object_id)
    entries = [entry for entry in load_audit_log() if int(entry.get("object_id", 0) or 0) == normalized_object_id]
    return _apply_limit(entries, limit)


def get_audit_by_action(action: str, limit: int | None = None) -> list[dict]:
    normalized_action = str(action or "").strip()
    if not normalized_action:
        raise ValueError("action is required.")
    entries = [entry for entry in load_audit_log() if str(entry.get("action", "") or "") == normalized_action]
    return _apply_limit(entries, limit)


def get_audit_in_range(start_ts, end_ts, limit: int | None = None) -> list[dict]:
    normalized_start = float(start_ts)
    normalized_end = float(end_ts)
    if normalized_start > normalized_end:
        raise ValueError("start_ts must be <= end_ts")
    entries = [
        entry
        for entry in load_audit_log()
        if normalized_start <= float(entry.get("timestamp", 0.0) or 0.0) <= normalized_end
    ]
    return _apply_limit(entries, limit)