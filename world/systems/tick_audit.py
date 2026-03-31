"""Soft timing anti-pattern audit helpers."""

from __future__ import annotations

from pathlib import Path
import re


_DEF_TICK_RE = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*tick[A-Za-z0-9_]*)\s*\(")
_WHILE_TRUE_RE = re.compile(r"^\s*while\s+True\s*:")
_TIME_CALL_RE = re.compile(r"time\.(time|sleep|perf_counter)\s*\(")


def scan_for_tick_violations(root_path=None):
    root = Path(root_path or Path(__file__).resolve().parents[2])
    warnings = []
    for path in root.rglob("*.py"):
        lowered = str(path).replace("\\", "/")
        if any(part in lowered for part in ["/.venv/", "/__pycache__/", "/build/"]):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for index, line in enumerate(lines, start=1):
            tick_match = _DEF_TICK_RE.search(line)
            if tick_match:
                warnings.append({
                    "path": str(path),
                    "line": index,
                    "kind": "tick_function",
                    "message": f"suspicious tick-like function: {tick_match.group(1)}",
                })
            if _WHILE_TRUE_RE.search(line):
                warnings.append({
                    "path": str(path),
                    "line": index,
                    "kind": "while_true",
                    "message": "while True loop found in gameplay code",
                })
            if _TIME_CALL_RE.search(line):
                window = "\n".join(lines[max(0, index - 3): min(len(lines), index + 2)])
                if "while" in window:
                    warnings.append({
                        "path": str(path),
                        "line": index,
                        "kind": "time_loop",
                        "message": "time-based loop pattern detected",
                    })
    return warnings
