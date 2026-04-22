import tempfile
import unittest
from pathlib import Path

import yaml

from server.systems import zone_room_npc_assignments


class BuilderZoneRoomNpcTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_zone_root = zone_room_npc_assignments.ZONE_ROOT
        self.test_zones_dir = Path(self.temp_dir.name) / "worlddata" / "zones"
        self.test_zones_dir.mkdir(parents=True, exist_ok=True)
        zone_room_npc_assignments.ZONE_ROOT = self.test_zones_dir

    def tearDown(self):
        zone_room_npc_assignments.ZONE_ROOT = self.original_zone_root
        self.temp_dir.cleanup()

    def test_update_builder_room_npcs_persists_room_assignment_ids(self):
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
                            "npcs": ["town_guard"],
                            "map": {"x": 1, "y": 2, "layer": 0},
                            "exits": {},
                        },
                        {
                            "id": "ferry_hold",
                            "name": "Ferry Hold",
                            "desc": "The river stinks of silt.",
                            "map": {"x": 3, "y": 4, "layer": 0},
                            "exits": {},
                        },
                    ],
                    "placements": {"npcs": [], "items": []},
                },
                file_handle,
                sort_keys=False,
            )

        updated_zone, updated_room = zone_room_npc_assignments.update_room_npcs(
            "market_square",
            ["town_guard", "goblin_grunt", "town_guard", ""],
            zone_id="kingshade",
        )

        self.assertEqual(updated_room["npcs"], ["town_guard", "goblin_grunt"])
        self.assertEqual(updated_zone["zone_id"], "kingshade")

        with zone_path.open(encoding="utf-8") as file_handle:
            saved = yaml.safe_load(file_handle) or {}

        saved_rooms = {room["id"]: room for room in saved.get("rooms") or []}
        self.assertEqual(saved_rooms["market_square"]["npcs"], ["town_guard", "goblin_grunt"])
        self.assertEqual(saved_rooms["ferry_hold"].get("npcs") or [], [])


if __name__ == "__main__":
    unittest.main()