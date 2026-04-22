import unittest
from unittest.mock import patch

from server.systems import direlore_item_import


class DireloreItemImportTests(unittest.TestCase):
    def test_interpret_item_maps_schema_bounded_fields(self):
        payload = direlore_item_import.interpret_item(
            {
                "id": 1,
                "name": "Weapon:Steel Broadsword",
                "item_type": "weapon",
                "weight": 45,
                "appraised_cost": "1,250 Kronars",
            }
        )
        self.assertEqual(payload["id"], "steel_broadsword")
        self.assertEqual(payload["category"], "weapon")
        self.assertEqual(payload["equipment"]["slot"], "weapon")
        self.assertEqual(payload["value"], 1250)
        self.assertFalse(payload["stackable"])
        self.assertEqual(payload["max_stack"], 1)
        self.assertEqual(payload["meta"]["source"], "direlore")

    def test_normalize_category_collapses_variants(self):
        self.assertEqual(direlore_item_import.normalize_category("armour"), "armor")
        self.assertEqual(direlore_item_import.normalize_category("general"), "misc")

    def test_ensure_unique_id_adds_suffix_for_collisions(self):
        self.assertEqual(
            direlore_item_import.ensure_unique_id("black_leather_mask", {"black_leather_mask", "black_leather_mask_1"}),
            "black_leather_mask_2",
        )

    def test_build_item_description_handles_plural_gear(self):
        description = direlore_item_import.build_item_description("Brown wool pants")
        self.assertEqual(description["short"], "some brown wool pants")
        self.assertEqual(description["long"], "Some brown wool pants lie here.")

    def test_import_summary_reports_missing_fields(self):
        rows = [
            {"id": 1, "name": "Armor:Half Plate", "item_type": "plate armor", "weight": None, "appraised_cost": ""},
            {"id": 2, "name": "Weapon:Half Plate", "item_type": "weapon", "weight": 45, "appraised_cost": "1,250 Kronars"},
        ]
        with patch("server.systems.direlore_item_import.fetch_items", return_value=rows):
            summary = direlore_item_import.import_direlore_items(limit=2, dry_run=True)
        self.assertEqual(summary["imported"], 2)
        self.assertEqual(summary["missing"]["appraised_cost"], 1)
        self.assertEqual(summary["missing"]["weight"], 1)
        self.assertEqual(summary["id_collisions_resolved"], 1)