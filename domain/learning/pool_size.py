from __future__ import annotations


VALID_SKILLSETS = ("primary", "secondary", "tertiary")

_BASE_POOL_FORMULAS = {
    "primary": (15000.0, 1000.0),
    "secondary": (12750.0, 850.0),
    "tertiary": (10500.0, 700.0),
}
_POOL_DENOMINATOR_OFFSET = 900.0


def normalize_skillset(skillset: str) -> str:
    normalized = str(skillset or "primary").strip().lower()
    if normalized not in VALID_SKILLSETS:
        return "primary"
    return normalized


def _piecewise_stat_bonus(stat_value: int | float, low_slope: float, mid_slope: float, high_slope: float, mid_base: float, high_base: float) -> float:
    value = float(stat_value or 0.0)
    if value < 30.0:
        return ((value - 10.0) * low_slope) / 10.0
    if value <= 60.0:
        return (((value - 30.0) * mid_slope) + mid_base) / 10.0
    return (((value - 60.0) * high_slope) + high_base) / 10.0


def base_pool_size(rank: int | float, skillset: str) -> float:
    normalized_rank = max(0.0, float(rank or 0.0))
    numerator, floor = _BASE_POOL_FORMULAS[normalize_skillset(skillset)]
    return (numerator * normalized_rank / (normalized_rank + _POOL_DENOMINATOR_OFFSET)) + floor


def intelligence_pool_bonus(intelligence: int | float) -> float:
    return _piecewise_stat_bonus(intelligence, 60.0, 30.0, 15.0, 1200.0, 2100.0)


def discipline_pool_bonus(discipline: int | float) -> float:
    return _piecewise_stat_bonus(discipline, 20.0, 10.0, 5.0, 400.0, 700.0)


def total_pool_size(rank: int | float, skillset: str, intelligence: int | float, discipline: int | float) -> float:
    base = base_pool_size(rank, skillset)
    pool_modifier = (1000.0 + intelligence_pool_bonus(intelligence) + discipline_pool_bonus(discipline)) / 1000.0
    return base * pool_modifier


def wisdom_pulse_multiplier(wisdom: int | float) -> float:
    return (1000.0 + intelligence_pool_bonus(wisdom)) / 1000.0