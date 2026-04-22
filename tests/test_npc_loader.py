import tempfile
import unittest
from pathlib import Path

import yaml

from server.systems import npc_loader


class NpcLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_root = npc_loader.NPC_ROOT
        npc_loader.NPC_ROOT = Path(self.temp_dir.name) / "world_data" / "npcs"
        for directory_name in npc_loader.NPC_TYPE_DIRECTORIES.values():
            (npc_loader.NPC_ROOT / directory_name).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        npc_loader.NPC_ROOT = self.original_root
        self.temp_dir.cleanup()

    def test_save_and_load_npc_payload(self):
        saved = npc_loader.save_npc_payload(
            {
                "id": "goblin-scout",
                "name": "Goblin Scout",
                "type": "hostile",
                "stats": {"level": 3, "health": 15, "attack": 4, "defense": 2},
                "behavior": {"aggressive": False, "roam": True, "assist": False},
                "vendor": {"enabled": True, "inventory": ["potion"]},
                "dialogue": {"greeting": "Snarl.", "idle": ["The goblin watches the treeline."]},
                "description": {"short": "a goblin scout", "long": "A goblin scout peers through the brush."},
                "meta": {"source": "direlore", "imported_at": "2026-04-21"},
            }
        )

        self.assertEqual(saved["type"], "hostile")
        self.assertTrue(saved["behavior"]["aggressive"])
        self.assertFalse(saved["vendor"]["enabled"])
        self.assertEqual(saved["vendor"]["inventory"], [])

        loaded = npc_loader.load_all_npcs()
        self.assertIn("goblin-scout", loaded)
        self.assertEqual(loaded["goblin-scout"]["name"], "Goblin Scout")
        self.assertEqual(loaded["goblin-scout"]["description"]["long"], "A goblin scout peers through the brush.")
        self.assertEqual(loaded["goblin-scout"]["meta"]["source"], "direlore")

    def test_delete_npc_payload_removes_file(self):
        npc_path = npc_loader.NPC_ROOT / "neutral" / "dockhand.yaml"
        with npc_path.open("w", encoding="utf-8") as file_handle:
            yaml.safe_dump(
                {
                    "id": "dockhand",
                    "name": "Dockhand",
                    "type": "neutral",
                    "stats": {"level": 1, "health": 8, "attack": 1, "defense": 1},
                    "behavior": {"aggressive": False, "roam": True, "assist": True},
                    "vendor": {"enabled": False, "inventory": []},
                    "dialogue": {"greeting": "Morning.", "idle": ["The dockhand checks the lines."]},
                },
                file_handle,
                sort_keys=False,
            )

        deleted_id = npc_loader.delete_npc_payload("dockhand")
        self.assertEqual(deleted_id, "dockhand")
        self.assertFalse(npc_path.exists())


if __name__ == "__main__":
    unittest.main()