import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.systems.loot import loot_loader


class LootLoaderTests(unittest.TestCase):
    def test_validate_loot_table_rejects_unknown_item(self):
        with self.assertRaisesRegex(ValueError, "unknown item"):
            loot_loader.validate_loot_table(
                {"id": "bad", "drops": [{"item": "missing_item", "chance": 0.5}]},
                item_records={},
            )

    def test_load_all_loot_tables_reads_yaml_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "schema_loot.yaml").write_text("id: string\n", encoding="utf-8")
            (root / "test_loot.yaml").write_text(
                "id: test_loot\n\ndrops:\n  - item: chain_greaves\n    chance: 1.0\n    min: 1\n    max: 2\n",
                encoding="utf-8",
            )
            with patch.object(loot_loader, "LOOT_ROOT", root):
                loaded = loot_loader.load_all_loot_tables(item_records={"chain_greaves": {"id": "chain_greaves"}})

        self.assertIn("test_loot", loaded)
        self.assertEqual(loaded["test_loot"]["drops"][0]["max"], 2)