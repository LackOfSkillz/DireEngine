import os
import types
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from server.systems import zone_runtime_spawn


class ZoneRuntimeSpawnTests(unittest.TestCase):
    def setUp(self):
        zone_runtime_spawn.npc_registry.clear()
        zone_runtime_spawn.item_registry.clear()

    def tearDown(self):
        zone_runtime_spawn.npc_registry.clear()
        zone_runtime_spawn.item_registry.clear()

    def test_apply_runtime_npc_definition_copies_behavior_flags(self):
        npc = types.SimpleNamespace(db=types.SimpleNamespace())

        zone_runtime_spawn.apply_runtime_npc_definition(
            npc,
            {
                "stats": {"level": 2, "health": 12, "attack": 3, "defense": 1},
                "behavior": {"aggressive": True, "assist": True},
                "loot_table": "test_loot",
            },
        )

        self.assertTrue(npc.db.aggressive)
        self.assertTrue(npc.db.assist)
        self.assertEqual(npc.db.loot_table, "test_loot")

    def test_build_room_assignment_placements_expands_nested_room_content(self):
        rooms = [
            {
                "id": "market_square",
                "npcs": ["merchant"],
                "items": [
                    {"id": "health_potion", "count": 3},
                    {"id": "chest", "count": 1, "items": [{"id": "coin_pouch", "count": 2}]},
                ],
            },
            {
                "id": "alley",
                "npcs": ["merchant"],
                "items": [{"id": "health_potion", "count": 1}],
            },
        ]

        with patch("server.systems.zone_runtime_spawn.npc_loader.load_all_npcs", return_value={"merchant": {"id": "merchant", "name": "Merchant"}}), patch(
            "server.systems.zone_runtime_spawn.item_loader.load_all_items",
            return_value={
                "health_potion": {"id": "health_potion", "name": "Health Potion", "stackable": True},
                "chest": {"id": "chest", "name": "Chest", "category": "container"},
                "coin_pouch": {"id": "coin_pouch", "name": "Coin Pouch"},
            },
        ):
            placements = zone_runtime_spawn.build_room_assignment_placements(rooms)

        self.assertEqual(len(placements["npcs"]), 2)
        self.assertEqual([placement["id"] for placement in placements["items"]], ["health_potion", "chest", "coin_pouch", "health_potion"])
        self.assertEqual(placements["items"][0]["count"], 3)
        self.assertIsNone(placements["items"][0]["parent_spawn_key"])
        self.assertEqual(placements["items"][2]["parent_spawn_key"], placements["items"][1]["spawn_key"])
        self.assertNotEqual(placements["items"][0]["spawn_key"], placements["items"][3]["spawn_key"])

    def test_build_room_assignment_placements_rejects_unknown_definition_ids(self):
        rooms = [{"id": "market_square", "npcs": ["missing_npc"], "items": [{"id": "missing_item", "count": 1}]}]

        with patch("server.systems.zone_runtime_spawn.npc_loader.load_all_npcs", return_value={}), patch(
            "server.systems.zone_runtime_spawn.item_loader.load_all_items", return_value={}
        ):
            with self.assertRaisesRegex(ValueError, "unknown npc"):
                zone_runtime_spawn.build_room_assignment_placements(rooms)


if __name__ == "__main__":
    unittest.main()