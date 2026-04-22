from __future__ import annotations

import random

from .loot_loader import ensure_loot_tables_loaded, loot_registry


def roll_loot(loot_id: str, *, rng: random.Random | None = None) -> list[dict]:
    ensure_loot_tables_loaded()

    normalized_loot_id = str(loot_id or "").strip()
    if not normalized_loot_id:
        return []

    table = loot_registry.get(normalized_loot_id)
    if table is None:
        raise ValueError(f"Unknown loot table '{normalized_loot_id}'.")

    rng = rng or random
    results: list[dict] = []
    for entry in table.get("drops") or []:
        if rng.random() > float(entry.get("chance", 0.0) or 0.0):
            continue
        min_count = max(1, int(entry.get("min", 1) or 1))
        max_count = max(min_count, int(entry.get("max", min_count) or min_count))
        quantity = rng.randint(min_count, max_count)
        results.append({"item_id": str(entry.get("item") or "").strip(), "count": quantity})
    return results