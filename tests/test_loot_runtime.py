import types
import unittest
from unittest.mock import patch

from server.systems import zone_runtime_spawn
from server.systems.loot import loot_runtime


class FakeAliases:
    def __init__(self):
        self.values = []

    def add(self, value):
        self.values.append(value)


class FakeObject:
    def __init__(self, key=""):
        self.key = key
        self.aliases = FakeAliases()
        self.db = types.SimpleNamespace()
        self.ndb = types.SimpleNamespace()
        self.tags = types.SimpleNamespace(add=lambda *args, **kwargs: None)
        self.location = None
        self.home = None


class LootRuntimeTests(unittest.TestCase):
    def setUp(self):
        zone_runtime_spawn.item_registry.clear()

    def tearDown(self):
        zone_runtime_spawn.item_registry.clear()

    def test_spawn_runtime_item_drop_merges_existing_stack(self):
        existing = FakeObject("Chain Greaves")
        existing.db.runtime_definition_kind = "item"
        existing.db.runtime_definition_id = "chain_greaves"
        existing.db.stack_count = 1
        room = types.SimpleNamespace(
            db=types.SimpleNamespace(zone_id="builder2", world_id="CRO_450_300"),
            ndb=types.SimpleNamespace(runtime_items=[existing]),
        )
        existing.location = room

        zone_runtime_spawn.item_registry.update({"chain_greaves": {"id": "chain_greaves", "name": "Chain Greaves", "stackable": True}})
        merged = zone_runtime_spawn.spawn_runtime_item_drop(room, {"id": "chain_greaves", "count": 2})

        self.assertIs(merged, existing)
        self.assertEqual(existing.db.stack_count, 3)
        self.assertEqual(existing.key, "Chain Greaves (x3)")

    def test_on_npc_defeated_spawns_each_drop(self):
        room = types.SimpleNamespace(db=types.SimpleNamespace(zone_id="builder2", world_id="CRO_450_300"), ndb=types.SimpleNamespace(runtime_items=[]))
        npc = types.SimpleNamespace(key="training goblin", db=types.SimpleNamespace(loot_table="test_loot"), location=room)
        with patch("server.systems.loot.loot_runtime.roll_loot", return_value=[{"item_id": "chain_greaves", "count": 1}]), patch(
            "server.systems.loot.loot_runtime.zone_runtime_spawn.spawn_runtime_item_drop"
        ) as spawn_runtime_item_drop:
            drops = loot_runtime.on_npc_defeated(npc)

        self.assertEqual(drops, [{"item_id": "chain_greaves", "count": 1}])
        spawn_runtime_item_drop.assert_called_once_with(room, {"id": "chain_greaves", "count": 1}, spawn_source="loot_drop")