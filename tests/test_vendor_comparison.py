import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.services.test_structured_spell_pipeline import DummyHolder
from tests.test_vendor_browse import BrowseDummyCharacter


class DummyItem:
    def __init__(self, key, *, armor_slot, armor_class, protection, weight, tier="average", layer="base"):
        self.key = key
        self.db = DummyHolder()
        self.db.armor_slot = armor_slot
        self.db.slot = armor_slot
        self.db.armor_class = armor_class
        self.db.armor_type = armor_class
        self.db.protection = protection
        self.db.weight = weight
        self.db.tier = tier
        self.db.layer = layer


class VendorComparisonTests(unittest.TestCase):
    def test_compare_single_item_against_equipped_slot(self):
        character = BrowseDummyCharacter()
        character.db.equipment = {
            "chest": [DummyItem("worn vest", armor_slot="chest", armor_class="light_armor", protection=2, weight=5.0)],
        }

        comparison = character.compare_items(
            {"display_name": "Average Chain Robe", "armor_slot": "chest", "armor_class": "chain_armor", "tier": "above_average"},
            character.get_top_layer_item("chest"),
            emit_messages=False,
            apply_roundtime=False,
        )

        self.assertEqual(int(comparison["armor"]), 2)
        self.assertEqual(int(comparison["weight"]), 5)
        self.assertEqual(int(comparison["tier"]), 1)

    def test_top_layer_comparison_uses_outermost_item(self):
        character = BrowseDummyCharacter()
        character.db.equipment = {
            "chest": [
                DummyItem("padded shirt", armor_slot="chest", armor_class="light_armor", protection=2, weight=5.0, layer="base"),
                DummyItem("outer plate", armor_slot="chest", armor_class="plate_armor", protection=8, weight=15.0, tier="above_average", layer="outer"),
            ],
        }

        top_item = character.get_top_layer_item("chest")
        self.assertEqual(top_item.key, "outer plate")

        comparison = character.compare_items(
            {"display_name": "Average Chain Robe", "armor_slot": "chest", "armor_class": "chain_armor", "tier": "average"},
            top_item,
            emit_messages=False,
            apply_roundtime=False,
        )
        self.assertEqual(int(comparison["armor"]), -4)

    def test_compare_kit_aggregates_slot_deltas(self):
        character = BrowseDummyCharacter()
        character.db.equipment = {
            "chest": [DummyItem("worn vest", armor_slot="chest", armor_class="light_armor", protection=2, weight=5.0)],
        }

        summary = character.compare_kit(
            [
                {"display_name": "Average Chain Robe", "armor_slot": "chest", "armor_class": "chain_armor", "tier": "average"},
                {"display_name": "Below Average Leather Leggings", "armor_slot": "legs", "armor_class": "light_armor", "tier": "below_average"},
            ]
        )

        self.assertEqual(int(summary["armor"]), 4)
        self.assertEqual(int(summary["weight"]), 10)
        self.assertEqual(int(summary["items"]), 2)

    def test_shop_compare_toggle_controls_ui_output(self):
        character = BrowseDummyCharacter()
        character.db.equipment = {
            "chest": [DummyItem("worn vest", armor_slot="chest", armor_class="light_armor", protection=2, weight=5.0)],
        }

        self.assertTrue(character.list_vendor_inventory("inventory"))
        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertTrue(character.list_vendor_inventory("chest"))
        self.assertIn("Compared to your worn chest armor", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("compare off"))
        self.assertIn("Comparison: off", character.messages[-1])
        self.assertNotIn("Compared to your worn chest armor", character.messages[-1])
