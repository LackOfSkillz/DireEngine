from __future__ import annotations

import math


def normalize_item_weight(raw_weight) -> float:
    if raw_weight is None:
        return 1.0
    return max(0.1, round(float(raw_weight) / 10.0, 2))


def derive_item_stats(category: str, *, raw_weight=None) -> dict:
    weight = normalize_item_weight(raw_weight)
    if category == "weapon":
        return {"attack": max(1, int(math.ceil(weight * 2.0))), "defense": 0}
    if category == "armor":
        return {"attack": 0, "defense": max(1, int(math.ceil(weight * 1.5)))}
    return {"attack": 0, "defense": 0}