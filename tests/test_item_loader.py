import tempfile
import unittest
from pathlib import Path

import yaml

from server.systems import item_loader


class ItemLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_root = item_loader.ITEM_ROOT
        item_loader.ITEM_ROOT = Path(self.temp_dir.name) / "world_data" / "items"
        for directory_name in item_loader.ITEM_CATEGORY_DIRECTORIES.values():
            (item_loader.ITEM_ROOT / directory_name).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        item_loader.ITEM_ROOT = self.original_root
        self.temp_dir.cleanup()

    def test_save_and_load_item_payload(self):
        saved = item_loader.save_item_payload(
            {
                "id": "iron-sword",
                "name": "Iron Sword",
                "category": "weapon",
                "weapon_class": "medium_edge",
                "tags": ["Martial", "Guard", "guard"],
                "level_band": {"min": 1, "max": 10},
                "value": 15,
                "weight": 4.5,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "head", "attack": 4, "defense": 0},
                "consumable": {"effect": "heal", "duration": 5},
                "container": {"capacity": 10},
                "description": {"short": "an iron sword", "long": "An iron sword lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-21"},
            }
        )

        self.assertEqual(saved["category"], "weapon")
        self.assertEqual(saved["equipment"]["slot"], "weapon")
        self.assertEqual(saved["weapon_class"], "medium_edge")
        self.assertEqual(saved["tags"], ["martial", "guard"])
        self.assertEqual(saved["level_band"], {"min": 1, "max": 10})
        self.assertEqual(saved["consumable"], {"effect": "", "duration": 0})
        self.assertEqual(saved["container"], {"capacity": 0, "weight_reduction": 0.0, "ammo_container": False, "allowed_ammo_types": []})
        self.assertEqual(saved["description"]["long"], "An iron sword lies here.")
        self.assertEqual(saved["meta"]["source"], "direlore")

        loaded = item_loader.load_all_items()
        self.assertIn("iron-sword", loaded)
        self.assertEqual(loaded["iron-sword"]["name"], "Iron Sword")
        self.assertEqual(loaded["iron-sword"]["max_stack"], 1)

    def test_delete_item_payload_removes_file(self):
        item_path = item_loader.ITEM_ROOT / "misc" / "rope.yaml"
        with item_path.open("w", encoding="utf-8") as file_handle:
            yaml.safe_dump(
                {
                    "id": "rope",
                    "name": "Rope",
                    "category": "misc",
                    "value": 3,
                    "weight": 1.2,
                    "stackable": False,
                    "max_stack": 1,
                    "equipment": {"slot": "none", "attack": 0, "defense": 0},
                    "consumable": {"effect": "", "duration": 0},
                    "container": {"capacity": 0},
                    "description": {"short": "a rope", "long": "A rope lies here."},
                    "meta": {"source": "", "imported_at": ""},
                },
                file_handle,
                sort_keys=False,
            )

        deleted_id = item_loader.delete_item_payload("rope")
        self.assertEqual(deleted_id, "rope")
        self.assertFalse(item_path.exists())

    def test_unknown_item_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown item fields"):
            item_loader.save_item_payload(
                {
                    "id": "rope",
                    "name": "Rope",
                    "category": "misc",
                    "value": 3,
                    "weight": 1.2,
                    "stackable": False,
                    "max_stack": 1,
                    "equipment": {"slot": "none", "attack": 0, "defense": 0},
                    "consumable": {"effect": "", "duration": 0},
                    "container": {"capacity": 0},
                    "description": {"short": "a rope", "long": "A rope lies here."},
                    "meta": {"source": "", "imported_at": ""},
                    "unexpected": True,
                }
            )

    def test_weapon_items_require_weapon_class(self):
        with self.assertRaisesRegex(ValueError, "weapon_class is required"):
            item_loader.save_item_payload(
                {
                    "id": "iron-sword",
                    "name": "Iron Sword",
                    "category": "weapon",
                    "value": 15,
                    "weight": 4.5,
                    "stackable": False,
                    "max_stack": 1,
                    "equipment": {"slot": "weapon", "attack": 4, "defense": 0},
                    "consumable": {"effect": "", "duration": 0},
                    "container": {"capacity": 0},
                    "description": {"short": "an iron sword", "long": "An iron sword lies here."},
                    "meta": {"source": "direlore", "imported_at": "2026-04-21"},
                }
            )

    def test_armor_items_require_armor_fields_and_normalize_tags(self):
        saved = item_loader.save_item_payload(
            {
                "id": "trail-boots",
                "name": "Trail Boots",
                "category": "armor",
                "armor_class": "light_armor",
                "armor_slot": "feet",
                "tier": "Average",
                "tags": ["Ranger", "Travel", "travel"],
                "level_band": {"min": 1, "max": 10},
                "value": 12,
                "weight": 2.0,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "none", "attack": 0, "defense": 2},
                "consumable": {"effect": "", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "some trail boots", "long": "Some trail boots lie here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-21"},
            }
        )

        self.assertEqual(saved["armor_class"], "light_armor")
        self.assertEqual(saved["armor_slot"], "feet")
        self.assertEqual(saved["tier"], "average")
        self.assertEqual(saved["equipment"]["slot"], "feet")
        self.assertEqual(saved["equip_slots"], ["feet"])
        self.assertEqual(saved["layer"], "base")
        self.assertEqual(saved["tags"], ["ranger", "travel"])

    def test_wearable_items_preserve_layering_metadata(self):
        saved = item_loader.save_item_payload(
            {
                "id": "reinforced_cloak",
                "name": "Reinforced Cloak",
                "category": "armor",
                "armor_class": "light_armor",
                "armor_slot": "cloak",
                "tier": "average",
                "layer": "outer",
                "blocks_layers": ["base"],
                "value": 18,
                "weight": 2.5,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "cloak", "attack": 0, "defense": 2},
                "consumable": {"effect": "", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "a reinforced cloak", "long": "A reinforced cloak lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-21"},
            }
        )

        self.assertEqual(saved["layer"], "outer")
        self.assertEqual(saved["equip_slots"], ["cloak"])
        self.assertEqual(saved["blocks_layers"], ["base"])

    def test_legacy_fine_tier_alias_normalizes_to_above_average(self):
        saved = item_loader.save_item_payload(
            {
                "id": "bascinet_helm",
                "name": "Bascinet Helm",
                "category": "armor",
                "armor_class": "plate_armor",
                "armor_slot": "head",
                "tier": "fine",
                "value": 38,
                "weight": 5.0,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "head", "attack": 0, "defense": 5},
                "consumable": {"effect": "", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "a bascinet helm", "long": "A bascinet helm lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-22"},
            }
        )

        self.assertEqual(saved["tier"], "above_average")

    def test_heavy_outer_armor_defaults_to_blocking_underlayers(self):
        saved = item_loader.save_item_payload(
            {
                "id": "chain_hauberk",
                "name": "Chain Hauberk",
                "category": "armor",
                "armor_class": "chain_armor",
                "armor_slot": "chest",
                "tier": "average",
                "value": 38,
                "weight": 5.0,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "chest", "attack": 0, "defense": 5},
                "consumable": {"effect": "", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "a chain hauberk", "long": "A chain hauberk lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-22"},
            }
        )

        self.assertEqual(saved["layer"], "outer")
        self.assertEqual(saved["blocks_layers"], ["under", "base"])

    def test_armor_items_fail_fast_without_armor_metadata(self):
        with self.assertRaisesRegex(ValueError, "armor_class is required"):
            item_loader.save_item_payload(
                {
                    "id": "trail-boots",
                    "name": "Trail Boots",
                    "category": "armor",
                    "value": 12,
                    "weight": 2.0,
                    "stackable": False,
                    "max_stack": 1,
                    "equipment": {"slot": "feet", "attack": 0, "defense": 2},
                    "consumable": {"effect": "", "duration": 0},
                    "container": {"capacity": 0},
                    "description": {"short": "some trail boots", "long": "Some trail boots lie here."},
                    "meta": {"source": "direlore", "imported_at": "2026-04-21"},
                }
            )

    def test_ammunition_items_require_ammo_metadata(self):
        saved = item_loader.save_item_payload(
            {
                "id": "practice_shortbow_arrows",
                "name": "Practice shortbow arrows",
                "category": "ammunition",
                "ammo_type": "arrow",
                "ammo_class": "short_bow",
                "stack_size": 10,
                "tier": "average",
                "base_price": 2,
                "tags": ["Ranger", "Ammo"],
                "level_band": {"min": 1, "max": 10},
                "value": 20,
                "weight": 1.0,
                "stackable": True,
                "max_stack": 10,
                "equipment": {"slot": "none", "attack": 0, "defense": 0},
                "consumable": {"effect": "", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "a bundle of practice shortbow arrows", "long": "A bundle of practice shortbow arrows lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-21"},
            }
        )

        self.assertEqual(saved["ammo_type"], "arrow")
        self.assertEqual(saved["ammo_class"], "short_bow")
        self.assertEqual(saved["stack_size"], 10)
        self.assertEqual(saved["base_price"], 2)
        self.assertEqual(saved["tags"], ["ranger", "ammo"])

    def test_ammunition_items_reject_invalid_stack_size(self):
        with self.assertRaisesRegex(ValueError, "stack_size must equal 10"):
            item_loader.save_item_payload(
                {
                    "id": "practice_shortbow_arrows",
                    "name": "Practice shortbow arrows",
                    "category": "ammunition",
                    "ammo_type": "arrow",
                    "ammo_class": "short_bow",
                    "stack_size": 8,
                    "tier": "average",
                    "base_price": 2,
                    "level_band": {"min": 1, "max": 10},
                    "value": 20,
                    "weight": 1.0,
                    "stackable": True,
                    "max_stack": 10,
                    "equipment": {"slot": "none", "attack": 0, "defense": 0},
                    "consumable": {"effect": "", "duration": 0},
                    "container": {"capacity": 0},
                    "description": {"short": "a bundle of practice shortbow arrows", "long": "A bundle of practice shortbow arrows lies here."},
                    "meta": {"source": "direlore", "imported_at": "2026-04-21"},
                }
            )

    def test_general_goods_items_preserve_utility_metadata(self):
        saved = item_loader.save_item_payload(
            {
                "id": "hunting_quiver",
                "name": "Hunting Quiver",
                "category": "container",
                "type": "ammo_container",
                "ammo_type": "arrow",
                "capacity": 20,
                "quickdraw_bonus": 0.05,
                "tier": "above_average",
                "utility_category": "containers",
                "functional_type": "quiver",
                "tool_type": "survival",
                "durability": 24,
                "value": 22,
                "weight": 0.8,
                "stackable": False,
                "max_stack": 1,
                "equipment": {"slot": "back", "attack": 0, "defense": 0},
                "consumable": {"effect": "", "duration": 0},
                "container": {
                    "capacity": 20,
                    "weight_reduction": 0.15,
                    "ammo_container": True,
                    "allowed_ammo_types": ["arrow"],
                },
                "description": {"short": "a hunting quiver", "long": "A sturdy hunting quiver lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-22"},
            }
        )

        self.assertEqual(saved["tier"], "above_average")
        self.assertEqual(saved["type"], "ammo_container")
        self.assertEqual(saved["ammo_type"], "arrow")
        self.assertEqual(saved["capacity"], 20)
        self.assertEqual(saved["quickdraw_bonus"], 0.05)
        self.assertEqual(saved["utility_category"], "containers")
        self.assertEqual(saved["functional_type"], "quiver")
        self.assertEqual(saved["tool_type"], "survival")
        self.assertEqual(saved["durability"], 24)
        self.assertEqual(saved["container"]["capacity"], 20)
        self.assertEqual(saved["container"]["weight_reduction"], 0.15)
        self.assertTrue(saved["container"]["ammo_container"])
        self.assertEqual(saved["container"]["allowed_ammo_types"], ["arrow"])

    def test_bait_items_preserve_family_and_quality(self):
        saved = item_loader.save_item_payload(
            {
                "id": "cut_worm_bait",
                "name": "Cut Worm Bait",
                "category": "consumable",
                "tier": "average",
                "utility_category": "fishing",
                "functional_type": "bait",
                "tool_type": "fishing",
                "bait_family": "worm_cutbait",
                "bait_quality": 12.5,
                "value": 3,
                "weight": 0.1,
                "stackable": True,
                "max_stack": 10,
                "equipment": {"slot": "none", "attack": 0, "defense": 0},
                "consumable": {"effect": "bait", "duration": 0},
                "container": {"capacity": 0},
                "description": {"short": "cut worm bait", "long": "A tin of cut worm bait lies here."},
                "meta": {"source": "direlore", "imported_at": "2026-04-22"},
            }
        )

        self.assertEqual(saved["functional_type"], "bait")
        self.assertEqual(saved["bait_family"], "worm_cutbait")
        self.assertEqual(saved["bait_quality"], 12.5)


if __name__ == "__main__":
    unittest.main()