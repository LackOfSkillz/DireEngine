from __future__ import annotations

from server.systems import zone_runtime_spawn

from .loot_resolver import roll_loot


def on_npc_defeated(npc, room=None) -> list[dict]:
    loot_table = str(getattr(getattr(npc, "db", None), "loot_table", "") or "").strip()
    if not loot_table:
        return []

    room = room or getattr(npc, "location", None)
    if room is None:
        return []

    drops = roll_loot(loot_table)
    for drop in drops:
        item_id = str(drop.get("item_id") or "").strip()
        count = max(1, int(drop.get("count", 1) or 1))
        if not item_id:
            continue
        zone_runtime_spawn.spawn_runtime_item_drop(room, {"id": item_id, "count": count}, spawn_source="loot_drop")
        print(f"{getattr(npc, 'key', getattr(npc, 'id', 'npc'))} dropped {item_id} x{count}")
    return drops