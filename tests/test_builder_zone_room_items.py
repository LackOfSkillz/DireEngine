import tempfile
import unittest
from pathlib import Path

import yaml

from server.systems import zone_room_item_assignments


class BuilderZoneRoomItemTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_zone_root = zone_room_item_assignments.ZONE_ROOT
        self.test_zones_dir = Path(self.temp_dir.name) / "worlddata" / "zones"
        self.test_zones_dir.mkdir(parents=True, exist_ok=True)
        zone_room_item_assignments.ZONE_ROOT = self.test_zones_dir

    def tearDown(self):
        zone_room_item_assignments.ZONE_ROOT = self.original_zone_root
        self.temp_dir.cleanup()

    def test_assign_item_to_room_persists_count_and_container_shape(self):
        zone_path = self.test_zones_dir / "kingshade.yaml"
        with zone_path.open("w", encoding="utf-8") as file_handle:
            yaml.safe_dump(
                {
                    "schema_version": "v1",
                    "zone_id": "kingshade",
                    "name": "Kingshade",
                    "rooms": [
                        {
                            "id": "market_square",
                            "name": "Market Square",
                            "desc": "A broad plaza.",
                            "items": [
                                {"id": "health_potion", "count": 2},
                                {"id": "chest", "count": 1, "items": [{"id": "coin_pouch", "count": 3}]},
                            ],
                            "map": {"x": 1, "y": 2, "layer": 0},
                            "exits": {},
                        },
                    ],
                    "placements": {"npcs": [], "items": []},
                },
                file_handle,
                sort_keys=False,
            )

        updated_zone, updated_room = zone_room_item_assignments.update_room_items(
            "market_square",
            [
                {"id": "health_potion", "count": 2},
                {"id": "health_potion", "count": 3},
                {"id": "iron_sword", "count": 1},
                {"id": "chest", "count": 1, "items": [{"id": "coin_pouch", "count": 3}]},
            ],
            zone_id="kingshade",
        )

        self.assertEqual(updated_zone["zone_id"], "kingshade")
        self.assertEqual(updated_room["items"], [
            {"id": "health_potion", "count": 5},
            {"id": "iron_sword", "count": 1},
            {"id": "chest", "count": 1, "items": [{"id": "coin_pouch", "count": 3}]},
        ])

        with zone_path.open(encoding="utf-8") as file_handle:
            saved = yaml.safe_load(file_handle) or {}

        saved_room = (saved.get("rooms") or [])[0]
        self.assertEqual(saved_room["items"], [
            {"id": "health_potion", "count": 5},
            {"id": "iron_sword", "count": 1},
            {"id": "chest", "count": 1, "items": [{"id": "coin_pouch", "count": 3}]},
        ])


if __name__ == "__main__":
    unittest.main()