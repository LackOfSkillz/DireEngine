"""Artifact bundle writer for DireTest runs."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_ARTIFACT_FILES = {
    "scenario.json": "json",
    "seed.txt": "text",
    "commands.log": "lines",
    "snapshots.json": "json",
    "metrics.json": "json",
    "traceback.txt": "text",
}


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, payload: str):
    path.write_text(str(payload or ""), encoding="utf-8")


def _write_lines(path: Path, payload):
    lines = payload or []
    if isinstance(lines, str):
        text = lines
    else:
        text = "\n".join(str(line) for line in lines)
    path.write_text(text, encoding="utf-8")


def write_artifacts(run_id, data, base_path=None):
    """Create the full DireTest artifact bundle for a run."""

    root = Path(base_path or Path.cwd() / "artifacts")
    artifact_dir = root / str(run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    scenario_payload = dict(data.get("scenario", {}) or {})
    seed_value = int(data.get("seed", 0) or 0)
    command_log = list(data.get("command_log", []) or [])
    snapshots = list(data.get("snapshots", []) or [])
    metrics = dict(data.get("metrics", {}) or {})
    traceback_text = str(data.get("traceback", "") or "")

    _write_json(artifact_dir / "scenario.json", scenario_payload)
    _write_text(artifact_dir / "seed.txt", f"seed={seed_value}\n")
    _write_lines(artifact_dir / "commands.log", command_log)
    _write_json(artifact_dir / "snapshots.json", snapshots)
    _write_json(artifact_dir / "metrics.json", metrics)
    _write_text(artifact_dir / "traceback.txt", traceback_text)

    for filename in REQUIRED_ARTIFACT_FILES:
        path = artifact_dir / filename
        if not path.exists():
            path.write_text("", encoding="utf-8")

    return artifact_dir