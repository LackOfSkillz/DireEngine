from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import tempfile
from time import time
from uuid import uuid4


logger = logging.getLogger(__name__)
DIFF_HISTORY_AVAILABLE = True
DIFF_HISTORY_SOFT_LIMIT_MB = 5
DIFF_HISTORY_SOFT_LIMIT_BYTES = DIFF_HISTORY_SOFT_LIMIT_MB * 1_000_000


def get_diff_history_path() -> Path:
    return Path(__file__).resolve().parent.parent / "history" / "diff_history_v1.json"


def _load_history_entries() -> list[dict]:
    history_path = get_diff_history_path()
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8") as history_file:
        data = json.load(history_file)
    if not isinstance(data, list):
        raise ValueError("Diff history must be a list.")
    return data


def _write_history_entries(entries: list[dict]) -> None:
    history_path = get_diff_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(history_path.parent), suffix=".tmp") as temp_file:
            json.dump(entries, temp_file, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, history_path)
    except Exception:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def _warn_if_history_large(history_path: Path) -> None:
    if not history_path.exists():
        return

    current_size = history_path.stat().st_size
    if current_size > DIFF_HISTORY_SOFT_LIMIT_BYTES:
        logger.warning(
            "Builder diff history is growing large: %s bytes exceeds soft limit of %s MB. Rotation is not implemented yet.",
            current_size,
            DIFF_HISTORY_SOFT_LIMIT_MB,
        )


def append_history_entry(entry: dict) -> None:
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict.")

    normalized_entry = dict(entry)
    entry_type = str(normalized_entry.get("type") or "apply").strip().lower() or "apply"
    if entry_type not in {"apply", "undo", "redo"}:
        raise ValueError("history entry type must be one of: apply, undo, redo.")
    normalized_entry["type"] = entry_type
    normalized_entry.setdefault("entry_id", str(uuid4()))
    normalized_entry.setdefault("timestamp", time())
    history_path = get_diff_history_path()
    _warn_if_history_large(history_path)
    entries = _load_history_entries()
    entries.append(normalized_entry)
    _write_history_entries(entries)


def load_history() -> list[dict]:
    return list(_load_history_entries())