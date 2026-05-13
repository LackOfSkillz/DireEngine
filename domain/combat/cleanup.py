from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CleanupResult:
    roundtime: float
    fatigue_change: int
    attacker_mm: int
    defender_mm: int
    sentinel: int


def _clamp_mm(mm: int, *, position: str | None, stunned: bool) -> int:
    mm = max(1, min(24, int(mm or 1)))
    normalized = str(position or "standing").lower()
    if normalized in {"sitting", "kneeling"}:
        mm = min(mm, 5)
    if normalized == "prone":
        mm = 1 if stunned else min(mm, 3)
    elif stunned:
        mm = min(mm, 3)
    return max(1, mm)


def apply_cleanup(attacker, defender, *, leftover_of: int, base_roundtime: float, fatigue_cost: int = 0) -> CleanupResult:
    sentinel = -5 if int(leftover_of or 0) <= 0 else 0
    fatigue_change = 5 if sentinel else max(1, int(fatigue_cost or round(base_roundtime) or 1))

    attacker_db = getattr(attacker, "db", None)
    defender_db = getattr(defender, "db", None)
    attacker_mm = _clamp_mm(getattr(attacker_db, "mm", 1), position=getattr(attacker_db, "position", "standing"), stunned=bool(getattr(attacker_db, "stunned", False)))
    defender_mm = _clamp_mm(getattr(defender_db, "mm", 1), position=getattr(defender_db, "position", "standing"), stunned=bool(getattr(defender_db, "stunned", False)))

    return CleanupResult(
        roundtime=max(1.0, float(base_roundtime or 1.0)),
        fatigue_change=fatigue_change,
        attacker_mm=attacker_mm,
        defender_mm=defender_mm,
        sentinel=sentinel,
    )