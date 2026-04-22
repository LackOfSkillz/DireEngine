from __future__ import annotations

from evennia.prototypes.spawner import search_prototype, spawn
from evennia.utils.create import create_object

from server.systems import item_loader, npc_loader, zone_room_item_assignments, zone_room_npc_assignments


npc_registry: dict[str, dict] = {}
item_registry: dict[str, dict] = {}
GENERIC_OBJECT_TYPECLASS = "typeclasses.objects.Object"


def reload_definitions() -> dict[str, int]:
    npc_registry.clear()
    item_registry.clear()
    npc_registry.update(npc_loader.load_all_npcs())
    item_registry.update(item_loader.load_all_items())
    return {
        "npcs": len(npc_registry),
        "items": len(item_registry),
    }


def _ensure_definitions_loaded() -> None:
    if not npc_registry and not item_registry:
        reload_definitions()


def _spawn_key(*parts: str) -> str:
    return "::".join(str(part or "").strip() for part in parts if str(part or "").strip())


def _flatten_room_item_entries(entries: list[dict], room_id: str, parent_spawn_key: str | None = None) -> list[dict]:
    flattened: list[dict] = []
    normalized_entries = zone_room_item_assignments.normalize_room_item_entries(entries)
    for index, entry in enumerate(normalized_entries):
        item_id = str(entry.get("id") or "").strip()
        if item_id not in item_registry:
            raise ValueError(f"Room '{room_id}' references unknown item '{item_id}'.")
        spawn_key = _spawn_key(room_id, parent_spawn_key or "room", str(index), item_id)
        flattened.append(
            {
                "id": item_id,
                "room": room_id,
                "count": max(1, int(entry.get("count", 1) or 1)),
                "parent_spawn_key": parent_spawn_key,
                "spawn_key": spawn_key,
                "definition": dict(item_registry[item_id]),
                "spawn_source": "room_assignment",
            }
        )
        flattened.extend(_flatten_room_item_entries(entry.get("items") or [], room_id, parent_spawn_key=spawn_key))
    return flattened


def build_room_assignment_placements(rooms: list[dict]) -> dict[str, list[dict]]:
    _ensure_definitions_loaded()

    npc_placements: list[dict] = []
    item_placements: list[dict] = []
    for room_data in list(rooms or []):
        room_id = str((room_data or {}).get("id") or "").strip()
        if not room_id:
            continue

        for index, npc_id in enumerate(zone_room_npc_assignments.normalize_builder_reference_ids(room_data.get("npcs") or [])):
            if npc_id not in npc_registry:
                raise ValueError(f"Room '{room_id}' references unknown npc '{npc_id}'.")
            npc_placements.append(
                {
                    "id": npc_id,
                    "room": room_id,
                    "spawn_key": _spawn_key(room_id, "npc", str(index), npc_id),
                    "definition": dict(npc_registry[npc_id]),
                    "spawn_source": "room_assignment",
                }
            )

        item_placements.extend(_flatten_room_item_entries(room_data.get("items") or [], room_id))

    return {
        "npcs": npc_placements,
        "items": item_placements,
    }


def apply_runtime_npc_definition(npc, definition: dict) -> None:
    if not definition:
        return
    description = dict(definition.get("description") or {})
    short_desc = str(description.get("short") or "").strip()
    long_desc = str(description.get("long") or "").strip()
    if short_desc:
        npc.db.short_desc = short_desc
    if long_desc:
        npc.db.desc = long_desc
    stats = dict(definition.get("stats") or {})
    npc.db.level = int(stats.get("level", 1) or 1)
    npc.db.health = int(stats.get("health", 1) or 1)
    npc.db.attack = int(stats.get("attack", 0) or 0)
    npc.db.defense = int(stats.get("defense", 0) or 0)
    behavior = dict(definition.get("behavior") or {})
    npc.db.aggressive = bool(behavior.get("aggressive", False))
    npc.db.assist = bool(behavior.get("assist", False))
    vendor = dict(definition.get("vendor") or {})
    npc.db.is_vendor = bool(vendor.get("enabled", False))
    npc.db.is_shopkeeper = bool(vendor.get("enabled", False))
    npc.db.inventory = [str(entry or "").strip() for entry in list(vendor.get("inventory") or []) if str(entry or "").strip()]
    npc.db.vendor_profile_id = str(definition.get("vendor_profile_id") or "").strip() or None
    if npc.db.vendor_profile_id and hasattr(npc, "generate_stock"):
        npc.generate_stock(force=True)
    loot_table = str(definition.get("loot_table") or "").strip()
    npc.db.loot_table = loot_table or None


def _safe_prototype_exists(prototype_key: str | None) -> bool:
    key = str(prototype_key or "").strip()
    if not key:
        return False
    try:
        return bool(search_prototype(key=key))
    except Exception:
        return False


def _create_spawned_object(placement: dict):
    prototype = str(placement.get("resolved_prototype") or placement.get("prototype") or "").strip() or None
    if prototype and _safe_prototype_exists(prototype):
        spawned = spawn(prototype)
        if spawned:
            return spawned[0]
    typeclass = str(placement.get("resolved_typeclass") or placement.get("typeclass") or GENERIC_OBJECT_TYPECLASS).strip() or GENERIC_OBJECT_TYPECLASS
    key = placement.get("id") or "unnamed"
    return create_object(typeclass, key=str(key))


def _track_room_runtime(room, kind: str, obj) -> None:
    if kind == "npc":
        room.ndb.runtime_npcs = list(getattr(room.ndb, "runtime_npcs", []) or []) + [obj]
        return
    room.ndb.runtime_items = list(getattr(room.ndb, "runtime_items", []) or []) + [obj]


def _apply_runtime_item_definition(item, definition: dict, item_id: str, count: int, spawn_source: str) -> None:
    base_name = str(definition.get("name") or getattr(item, "key", "") or item_id)
    item.key = f"{base_name} (x{count})" if count > 1 else base_name
    item.aliases.add(base_name)
    item.aliases.add(str(item_id))
    item.db.world_id = item_id
    item.db.prototype = definition.get("prototype")
    item.db.runtime_definition_id = item_id
    item.db.runtime_definition_kind = "item"
    item.db.runtime_spawn_source = spawn_source or "zone_placement"
    item.db.stack_count = count
    item.db.is_npc = False


def spawn_runtime_item_drop(room, entry: dict, *, spawn_source: str = "loot_drop"):
    _ensure_definitions_loaded()

    room_id = str(getattr(getattr(room, "db", None), "world_id", "") or getattr(room, "key", "") or "room")
    zone_id = str(getattr(getattr(room, "db", None), "zone_id", "") or "").strip()
    item_id = str((entry or {}).get("id") or "").strip()
    if not item_id:
        raise ValueError("Runtime item entry is missing id.")
    if item_id not in item_registry:
        raise ValueError(f"Unknown item '{item_id}'.")

    definition = dict(item_registry[item_id])
    count = max(1, int((entry or {}).get("count", 1) or 1))
    if bool(definition.get("stackable", False)):
        for existing in list(getattr(room.ndb, "runtime_items", []) or []):
            if getattr(getattr(existing, "db", None), "runtime_definition_kind", "") != "item":
                continue
            if str(getattr(getattr(existing, "db", None), "runtime_definition_id", "") or "").strip() != item_id:
                continue
            if getattr(existing, "location", None) != room:
                continue
            next_count = max(1, int(getattr(getattr(existing, "db", None), "stack_count", 1) or 1) + count)
            _apply_runtime_item_definition(existing, definition, item_id, next_count, spawn_source)
            print(f"Spawned item {item_id} x{next_count} in {room_id}")
            return existing

    placement = {
        "id": item_id,
        "count": count,
        "definition": definition,
        "room": room_id,
        "prototype": definition.get("prototype"),
        "typeclass": definition.get("typeclass") or GENERIC_OBJECT_TYPECLASS,
        "spawn_source": spawn_source,
    }
    item = _create_spawned_object(placement)
    item.location = room
    item.home = room
    _apply_runtime_item_definition(item, definition, item_id, count, spawn_source)
    if zone_id and getattr(item, "tags", None):
        item.tags.add("world_sync")
        item.tags.add(f"zone:{zone_id}")
    _track_room_runtime(room, "item", item)
    print(f"Spawned item {item_id} x{count} in {room_id}")
    return item