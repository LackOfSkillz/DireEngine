import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from server.systems import zone_runtime_spawn
from world.worlddata.services import import_zone_service


class ImportZoneServiceTests(unittest.TestCase):
    def setUp(self):
        zone_runtime_spawn.npc_registry.clear()
        zone_runtime_spawn.item_registry.clear()

    def tearDown(self):
        zone_runtime_spawn.npc_registry.clear()
        zone_runtime_spawn.item_registry.clear()

    def test_resolve_spawn_blueprint_defaults_npcs_to_npc_typeclass(self):
        prototype, typeclass = import_zone_service._resolve_spawn_blueprint({"id": "training_goblin"}, "npc", [])

        self.assertIsNone(prototype)
        self.assertEqual(typeclass, "typeclasses.npcs.NPC")

    def test_resolve_spawn_blueprint_keeps_generic_items_generic(self):
        prototype, typeclass = import_zone_service._resolve_spawn_blueprint({"id": "chain_greaves"}, "item", [])

        self.assertIsNone(prototype)
        self.assertEqual(typeclass, "typeclasses.objects.Object")

    def test_build_import_plan_promotes_room_npcs_into_runtime_placements(self):
        zone_runtime_spawn.npc_registry.update({
            "armorer_01": {"id": "armorer_01", "name": "Armorer"},
        })

        plan = import_zone_service._build_import_plan(
            "builder2",
            {
                "schema_version": "v1",
                "zone_id": "builder2",
                "name": "Builder Two",
                "rooms": [
                    {
                        "id": "market_square",
                        "name": "Market Square",
                        "desc": "A broad plaza.",
                        "npcs": ["armorer_01"],
                        "items": [],
                        "map": {"x": 1, "y": 2, "layer": 0},
                        "exits": {},
                    }
                ],
                "placements": {"npcs": [], "items": []},
            },
        )

        self.assertEqual(plan["summary"]["npcs"], 1)
        self.assertEqual(plan["placements"]["npcs"][0]["id"], "armorer_01")
        self.assertEqual(plan["placements"]["npcs"][0]["room"], "market_square")

    def test_build_import_plan_migrates_missing_room_tags_to_empty_object(self):
        plan = import_zone_service._build_import_plan(
            "builder2",
            {
                "schema_version": "v1",
                "zone_id": "builder2",
                "name": "Builder Two",
                "rooms": [
                    {
                        "id": "market_square",
                        "name": "Market Square",
                        "desc": "A broad plaza.",
                        "map": {"x": 1, "y": 2, "layer": 0},
                        "exits": {},
                    }
                ],
                "placements": {"npcs": [], "items": []},
            },
        )

        self.assertEqual(
            plan["rooms"][0]["tags"],
            {
                "structure": None,
                "specific_function": None,
                "named_feature": None,
                "condition": None,
                "custom": [],
            },
        )

    def test_build_import_plan_preserves_and_normalizes_room_tags(self):
        plan = import_zone_service._build_import_plan(
            "builder2",
            {
                "schema_version": "v1",
                "zone_id": "builder2",
                "name": "Builder Two",
                "rooms": [
                    {
                        "id": "market_square",
                        "name": "Market Square",
                        "desc": "A broad plaza.",
                        "tags": {
                            "structure": "square",
                            "specific_function": "market-stall",
                            "named_feature": "fountain",
                            "condition": "worn",
                            "custom": ["awning", "crowded", "awning"],
                        },
                        "map": {"x": 1, "y": 2, "layer": 0},
                        "exits": {},
                    }
                ],
                "placements": {"npcs": [], "items": []},
            },
        )

        self.assertEqual(
            plan["rooms"][0]["tags"],
            {
                "structure": "square",
                "specific_function": "market-stall",
                "named_feature": "fountain",
                "condition": "worn",
                "custom": ["awning", "crowded"],
            },
        )