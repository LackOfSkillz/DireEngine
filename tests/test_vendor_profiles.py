import tempfile
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from server.systems import item_loader, kit_templates, vendor_profiles


class VendorProfileTests(unittest.TestCase):
    def test_load_kit_templates_reads_yaml_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "schema_kit_template.yaml").write_text("id: string\n", encoding="utf-8")
            (root / "ranger_leathers.yaml").write_text(
                "id: ranger_leathers\narmor_class: leather_armor\ntheme_tags:\n  - ranger\nrequired_slots:\n  - chest\n  - legs\noptional_slots:\n  - cloak\ntier_bias:\n  average: 0.6\n  above_average: 0.3\n  exquisite: 0.1\n",
                encoding="utf-8",
            )
            with patch.object(kit_templates, "KIT_TEMPLATE_ROOT", root):
                loaded = kit_templates.load_kit_templates()

        self.assertIn("ranger_leathers", loaded)
        self.assertEqual(loaded["ranger_leathers"]["armor_class"], "leather_armor")

    def test_load_vendor_profiles_reads_yaml_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "schema_vendor_profile.yaml").write_text("id: string\n", encoding="utf-8")
            (root / "ranger_weapon_vendor.yaml").write_text(
                "id: ranger_weapon_vendor\ncategory: weapon\nlevel_band:\n  min: 1\n  max: 10\nstock_count: 2\nallowed_weapon_classes:\n  - short_bow\npreferred_weapon_classes:\n  short_bow: 0.5\nexcluded_weapon_classes: []\nrequired_tags:\n  - ranger\nallow_duplicates: false\n",
                encoding="utf-8",
            )
            with patch.object(vendor_profiles, "VENDOR_PROFILE_ROOT", root):
                loaded = vendor_profiles.load_vendor_profiles()

        self.assertIn("ranger_weapon_vendor", loaded)
        self.assertEqual(loaded["ranger_weapon_vendor"]["allowed_weapon_classes"], ["short_bow"])

    def test_generate_vendor_stock_filters_ranger_vendor_classes(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_weapon_vendor",
                "category": "weapon",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 3,
                "allowed_weapon_classes": ["short_bow", "long_bow", "thrown"],
                "preferred_weapon_classes": {"short_bow": 0.5, "long_bow": 0.3, "thrown": 0.2},
                "required_tags": ["ranger"],
                "allow_duplicates": False,
            }
        )
        item_records = {
            "practice_shortbow": {"id": "practice_shortbow", "name": "Practice Shortbow", "category": "weapon", "weapon_class": "short_bow", "tags": ["ranger"], "level_band": {"min": 1, "max": 10}, "value": 18},
            "trail_longbow": {"id": "trail_longbow", "name": "Trail Longbow", "category": "weapon", "weapon_class": "long_bow", "tags": ["ranger"], "level_band": {"min": 1, "max": 10}, "value": 28},
            "balanced_throwing_knife": {"id": "balanced_throwing_knife", "name": "Balanced Throwing Knife", "category": "weapon", "weapon_class": "thrown", "tags": ["ranger"], "level_band": {"min": 1, "max": 10}, "value": 16},
            "watch_crossbow": {"id": "watch_crossbow", "name": "Watch Crossbow", "category": "weapon", "weapon_class": "crossbow", "tags": ["guard"], "level_band": {"min": 1, "max": 10}, "value": 27},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(1))

        self.assertEqual(len(generated["inventory"]), 3)
        self.assertTrue(set(generated["item_ids"]).issubset({"practice_shortbow", "trail_longbow", "balanced_throwing_knife"}))
        self.assertNotIn("watch_crossbow", generated["item_ids"])

    def test_generate_vendor_stock_filters_paladin_vendor_classes(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "paladin_weapon_vendor",
                "category": "weapon",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 3,
                "allowed_weapon_classes": ["heavy_edge", "medium_edge", "heavy_blunt"],
                "preferred_weapon_classes": {"heavy_edge": 0.4, "medium_edge": 0.3, "heavy_blunt": 0.3},
                "required_tags": ["martial"],
                "allow_duplicates": False,
            }
        )
        item_records = {
            "templar_claymore": {"id": "templar_claymore", "name": "Templar Claymore", "category": "weapon", "weapon_class": "heavy_edge", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 34},
            "bastion_war_mace": {"id": "bastion_war_mace", "name": "Bastion War Mace", "category": "weapon", "weapon_class": "heavy_blunt", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 30},
            "knight_broadsword": {"id": "knight_broadsword", "name": "Knight Broadsword", "category": "weapon", "weapon_class": "medium_edge", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 24},
            "practice_shortbow": {"id": "practice_shortbow", "name": "Practice Shortbow", "category": "weapon", "weapon_class": "short_bow", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 18},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(2))

        self.assertTrue(set(generated["item_ids"]).issubset({"templar_claymore", "bastion_war_mace", "knight_broadsword"}))
        self.assertNotIn("practice_shortbow", generated["item_ids"])

    def test_vendor_profile_rejects_slot_targets_above_stock_count(self):
        with self.assertRaisesRegex(ValueError, "slot_targets total"):
            vendor_profiles.normalize_vendor_profile(
                {
                    "id": "ranger_armor_vendor",
                    "category": "armor",
                    "stock_count": 2,
                    "allowed_armor_classes": ["light_armor"],
                    "slot_targets": {"chest": 2, "legs": 1},
                }
            )

    def test_vendor_profile_derives_slot_priority_from_slot_targets(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_armor_vendor",
                "category": "armor",
                "stock_count": 6,
                "allowed_armor_slots": ["chest", "legs", "cloak"],
                "slot_targets": {"chest": 3, "legs": 2, "cloak": 1},
            }
        )

        self.assertEqual(
            profile["slot_priority"],
            {"chest": "high", "legs": "medium", "cloak": "low"},
        )

    def test_generate_vendor_stock_supports_armor_slot_targets_and_fallback(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 4,
                "allowed_armor_classes": ["light_armor", "leather_armor"],
                "preferred_armor_classes": {"leather_armor": 0.6, "light_armor": 0.4},
                "allowed_armor_slots": ["chest", "legs", "hands", "cloak"],
                "preferred_armor_slots": {"chest": 0.5, "legs": 0.3, "hands": 0.2},
                "slot_targets": {"chest": 1, "legs": 1, "cloak": 1},
                "allow_duplicates": False,
            }
        )
        item_records = {
            "leather_vest": {"id": "leather_vest", "name": "Leather Vest", "category": "armor", "armor_class": "leather_armor", "armor_slot": "chest", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 25},
            "hide_pants": {"id": "hide_pants", "name": "Hide Pants", "category": "armor", "armor_class": "leather_armor", "armor_slot": "legs", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 22},
            "field_gloves": {"id": "field_gloves", "name": "Field Gloves", "category": "armor", "armor_class": "light_armor", "armor_slot": "hands", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 14},
            "hooded_wrap": {"id": "hooded_wrap", "name": "Hooded Wrap", "category": "armor", "armor_class": "light_armor", "armor_slot": "head", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 9},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(4))

        armor_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict)]
        tiers_by_item = {(entry["item_id"], entry["tier"]) for entry in armor_entries}

        self.assertEqual(len(armor_entries), 4)
        self.assertIn(("leather_vest", "below_average"), tiers_by_item)
        self.assertIn(("leather_vest", "average"), tiers_by_item)
        self.assertIn(("hide_pants", "below_average"), tiers_by_item)
        self.assertIn(("hide_pants", "average"), tiers_by_item)
        self.assertTrue(set(generated["item_ids"]).issubset({"leather_vest", "hide_pants", "field_gloves", "hooded_wrap"}))

    def test_generate_vendor_stock_balances_baseline_and_slot_coverage(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "paladin_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 14,
                "allowed_armor_classes": ["plate_armor", "chain_armor"],
                "allowed_armor_slots": ["chest", "legs", "hands", "feet", "head", "shield"],
                "preferred_armor_classes": {"plate_armor": 0.55, "chain_armor": 0.45},
                "slot_priority": {
                    "chest": "high",
                    "legs": "high",
                    "hands": "medium",
                    "feet": "medium",
                    "head": "medium",
                    "shield": "medium",
                },
                "allow_duplicates": False,
            }
        )
        item_records = {
            "bascinet": {"id": "bascinet", "name": "Bascinet", "category": "armor", "armor_class": "plate_armor", "armor_slot": "head", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 30},
            "chain_robe": {"id": "chain_robe", "name": "Chain Robe", "category": "armor", "armor_class": "chain_armor", "armor_slot": "chest", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 35},
            "chain_greaves": {"id": "chain_greaves", "name": "Chain Greaves", "category": "armor", "armor_class": "chain_armor", "armor_slot": "legs", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 18},
            "plate_gauntlets": {"id": "plate_gauntlets", "name": "Plate Gauntlets", "category": "armor", "armor_class": "plate_armor", "armor_slot": "hands", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 20},
            "plate_sabatons": {"id": "plate_sabatons", "name": "Plate Sabatons", "category": "armor", "armor_class": "plate_armor", "armor_slot": "feet", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 22},
            "tower_shield": {"id": "tower_shield", "name": "Tower Shield", "category": "armor", "armor_class": "plate_armor", "armor_slot": "shield", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 26},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(7))

        armor_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict)]
        baseline_entries = [entry for entry in armor_entries if entry["tier"] in {"below_average", "average"}]
        slot_tiers = {(entry["armor_slot"], entry["tier"]) for entry in armor_entries}
        high_tier_entries = [entry for entry in armor_entries if entry["tier"] in {"epic", "legendary"}]

        for slot_name in ["chest", "legs", "hands", "feet", "head", "shield"]:
            self.assertIn((slot_name, "below_average"), slot_tiers)
            self.assertIn((slot_name, "average"), slot_tiers)
        self.assertGreaterEqual(len(baseline_entries), int(len(armor_entries) * 0.70))
        self.assertLessEqual(len(high_tier_entries), int(len(armor_entries) * 0.10))

    def test_generate_vendor_stock_creates_coherent_ranger_kit(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 8,
                "allowed_armor_classes": ["leather_armor"],
                "allowed_armor_slots": ["chest", "legs", "hands", "feet", "head", "cloak"],
                "slot_priority": {"chest": "high", "legs": "high", "hands": "medium", "feet": "medium", "head": "low", "cloak": "low"},
                "kit_templates": ["ranger_leathers"],
                "kit_count": 1,
                "allow_duplicates": False,
            }
        )
        item_records = {
            "ranger_vest": {"id": "ranger_vest", "name": "Ranger Vest", "category": "armor", "armor_class": "leather_armor", "armor_slot": "chest", "tags": ["ranger", "scout"], "level_band": {"min": 1, "max": 10}, "value": 25},
            "scout_leggings": {"id": "scout_leggings", "name": "Scout Leggings", "category": "armor", "armor_class": "leather_armor", "armor_slot": "legs", "tags": ["ranger", "scout"], "level_band": {"min": 1, "max": 10}, "value": 22},
            "trail_gloves": {"id": "trail_gloves", "name": "Trail Gloves", "category": "armor", "armor_class": "leather_armor", "armor_slot": "hands", "tags": ["ranger"], "level_band": {"min": 1, "max": 10}, "value": 14},
            "field_boots": {"id": "field_boots", "name": "Field Boots", "category": "armor", "armor_class": "leather_armor", "armor_slot": "feet", "tags": ["scout"], "level_band": {"min": 1, "max": 10}, "value": 18},
            "hooded_cowl": {"id": "hooded_cowl", "name": "Hooded Cowl", "category": "armor", "armor_class": "leather_armor", "armor_slot": "head", "tags": ["ranger"], "level_band": {"min": 1, "max": 10}, "value": 12},
            "weather_cloak": {"id": "weather_cloak", "name": "Weather Cloak", "category": "armor", "armor_class": "leather_armor", "armor_slot": "cloak", "tags": ["scout"], "level_band": {"min": 1, "max": 10}, "value": 11},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}), patch.object(
            kit_templates,
            "KIT_TEMPLATES",
            {
                "ranger_leathers": {
                    "id": "ranger_leathers",
                    "armor_class": "leather_armor",
                    "theme_tags": ["ranger", "scout"],
                    "required_slots": ["chest", "legs", "hands", "feet"],
                    "optional_slots": ["head", "cloak"],
                    "tier_bias": {"average": 1.0},
                }
            },
        ):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(3))

        kit_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict) and entry.get("kit_id") == "ranger_leathers"]
        self.assertTrue(kit_entries)
        self.assertTrue({"chest", "legs", "hands", "feet"}.issubset({entry["armor_slot"] for entry in kit_entries}))
        self.assertTrue(all(entry["armor_class"] == "leather_armor" for entry in kit_entries))

    def test_generate_vendor_stock_keeps_normal_fill_after_kits(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "paladin_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 10,
                "allowed_armor_classes": ["chain_armor", "plate_armor"],
                "allowed_armor_slots": ["head", "chest", "legs", "hands", "feet", "shield", "shoulders"],
                "slot_priority": {"chest": "high", "legs": "high", "head": "medium", "hands": "medium", "feet": "medium", "shield": "medium", "shoulders": "low"},
                "kit_templates": ["paladin_chain"],
                "kit_count": 1,
                "allow_duplicates": False,
            }
        )
        item_records = {
            "chain_helm": {"id": "chain_helm", "name": "Chain Helm", "category": "armor", "armor_class": "chain_armor", "armor_slot": "head", "tags": ["paladin"], "level_band": {"min": 1, "max": 10}, "value": 20},
            "chain_hauberk": {"id": "chain_hauberk", "name": "Chain Hauberk", "category": "armor", "armor_class": "chain_armor", "armor_slot": "chest", "tags": ["paladin", "martial"], "level_band": {"min": 1, "max": 10}, "value": 30},
            "chain_legs": {"id": "chain_legs", "name": "Chain Legs", "category": "armor", "armor_class": "chain_armor", "armor_slot": "legs", "tags": ["paladin"], "level_band": {"min": 1, "max": 10}, "value": 24},
            "chain_gauntlets": {"id": "chain_gauntlets", "name": "Chain Gauntlets", "category": "armor", "armor_class": "chain_armor", "armor_slot": "hands", "tags": ["paladin"], "level_band": {"min": 1, "max": 10}, "value": 18},
            "chain_sabatons": {"id": "chain_sabatons", "name": "Chain Sabatons", "category": "armor", "armor_class": "chain_armor", "armor_slot": "feet", "tags": ["paladin"], "level_band": {"min": 1, "max": 10}, "value": 16},
            "kite_shield": {"id": "kite_shield", "name": "Kite Shield", "category": "armor", "armor_class": "chain_armor", "armor_slot": "shield", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 22},
            "plate_spaulders": {"id": "plate_spaulders", "name": "Plate Spaulders", "category": "armor", "armor_class": "plate_armor", "armor_slot": "shoulders", "tags": ["martial"], "level_band": {"min": 1, "max": 10}, "value": 21},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}), patch.object(
            kit_templates,
            "KIT_TEMPLATES",
            {
                "paladin_chain": {
                    "id": "paladin_chain",
                    "armor_class": "chain_armor",
                    "theme_tags": ["paladin", "martial"],
                    "required_slots": ["head", "chest", "legs", "hands"],
                    "optional_slots": ["feet", "shield"],
                    "tier_bias": {"average": 1.0},
                }
            },
        ):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(4))

        kit_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict) and entry.get("kit_id")]
        non_kit_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict) and not entry.get("kit_id")]
        self.assertTrue(kit_entries)
        self.assertTrue(non_kit_entries)

    def test_generate_vendor_stock_filters_armor_classes_and_slots(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "paladin_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 3,
                "allowed_armor_classes": ["plate_armor", "chain_armor"],
                "excluded_armor_classes": ["light_armor"],
                "allowed_armor_slots": ["head", "chest", "legs", "shield"],
                "preferred_armor_classes": {"plate_armor": 0.6, "chain_armor": 0.4},
                "allow_duplicates": False,
            }
        )
        item_records = {
            "bascinet": {"id": "bascinet", "name": "Bascinet", "category": "armor", "armor_class": "plate_armor", "armor_slot": "head", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 30},
            "chain_robe": {"id": "chain_robe", "name": "Chain Robe", "category": "armor", "armor_class": "chain_armor", "armor_slot": "chest", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 35},
            "chain_greaves": {"id": "chain_greaves", "name": "Chain Greaves", "category": "armor", "armor_class": "chain_armor", "armor_slot": "legs", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 18},
            "cloth_wrap": {"id": "cloth_wrap", "name": "Cloth Wrap", "category": "armor", "armor_class": "light_armor", "armor_slot": "chest", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 8},
            "leather_gloves": {"id": "leather_gloves", "name": "Leather Gloves", "category": "armor", "armor_class": "leather_armor", "armor_slot": "hands", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 10},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(2))

        self.assertTrue(set(generated["item_ids"]).issubset({"bascinet", "chain_robe", "chain_greaves"}))

    def test_calculate_ammo_price_scales_by_tier(self):
        self.assertEqual(vendor_profiles.calculate_ammo_price(2, "below_average"), 14)
        self.assertEqual(vendor_profiles.calculate_ammo_price(2, "average"), 20)
        self.assertEqual(vendor_profiles.calculate_ammo_price(2, "legendary"), 80)

    def test_generate_vendor_stock_adds_baseline_and_random_ammo(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_weapon_vendor",
                "category": "weapon",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 1,
                "allowed_weapon_classes": ["short_bow"],
                "preferred_weapon_classes": {"short_bow": 1.0},
                "ammo_types": ["arrow"],
                "ammo_classes": ["short_bow", "long_bow"],
                "ammo_stock_count": 2,
                "allow_duplicates": True,
            }
        )
        item_records = {
            "practice_shortbow": {"id": "practice_shortbow", "name": "Practice Shortbow", "category": "weapon", "weapon_class": "short_bow", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 18},
            "practice_shortbow_arrows": {"id": "practice_shortbow_arrows", "name": "Practice shortbow arrows", "category": "ammunition", "ammo_type": "arrow", "ammo_class": "short_bow", "stack_size": 10, "tier": "average", "base_price": 2, "tags": [], "level_band": {"min": 1, "max": 10}, "value": 20},
            "hunting_longbow_arrows": {"id": "hunting_longbow_arrows", "name": "Hunting longbow arrows", "category": "ammunition", "ammo_type": "arrow", "ammo_class": "long_bow", "stack_size": 10, "tier": "average", "base_price": 3, "tags": [], "level_band": {"min": 1, "max": 10}, "value": 30},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(2))

        ammo_entries = [entry for entry in generated["inventory"] if isinstance(entry, dict)]
        ammo_labels = [str(entry.get("display_name") or "") for entry in ammo_entries]
        self.assertEqual(len(ammo_entries), 6)
        self.assertTrue(any(label.startswith("Below Average Practice shortbow arrows") for label in ammo_labels))
        self.assertTrue(any(label.startswith("Average Practice shortbow arrows") for label in ammo_labels))
        self.assertTrue(any(label.startswith("Below Average Hunting longbow arrows") for label in ammo_labels))
        self.assertTrue(any(label.startswith("Average Hunting longbow arrows") for label in ammo_labels))
        self.assertTrue(all(int(entry.get("quantity", 0) or 0) == 10 for entry in ammo_entries))

    def test_generate_vendor_stock_uses_explicit_tier_labels_for_armor(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "ranger_armor_vendor",
                "category": "armor",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 2,
                "allowed_armor_classes": ["leather_armor"],
                "allowed_armor_slots": ["chest"],
                "slot_priority": {"chest": "high"},
                "allow_duplicates": True,
            }
        )
        item_records = {
            "leather_vest": {"id": "leather_vest", "name": "Leather Vest", "category": "armor", "armor_class": "leather_armor", "armor_slot": "chest", "tags": [], "level_band": {"min": 1, "max": 10}, "value": 25},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(5))

        labels = [entry["display_name"] for entry in generated["inventory"] if isinstance(entry, dict)]
        self.assertIn("[Low] Leather Vest", labels)
        self.assertIn("[Avg] Leather Vest", labels)

    def test_generate_general_goods_stock_keeps_essentials_and_rotates_optionals(self):
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "general_goods_vendor",
                "category": "general_goods",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 5,
                "essential_item_ids": ["starter_pack", "coil_of_rope", "river_fishing_pole"],
                "optional_item_ids": ["miners_pick", "fish_string", "hunting_quiver"],
                "optional_stock_count": 2,
                "allow_duplicates": False,
            }
        )
        item_records = {
            "starter_pack": {"id": "starter_pack", "name": "Starter Pack", "category": "container", "utility_category": "containers", "level_band": {"min": 1, "max": 10}, "value": 9},
            "coil_of_rope": {"id": "coil_of_rope", "name": "Coil of Rope", "category": "misc", "utility_category": "tools", "functional_type": "rope", "level_band": {"min": 1, "max": 10}, "value": 5},
            "river_fishing_pole": {"id": "river_fishing_pole", "name": "River Fishing Pole", "category": "misc", "utility_category": "fishing", "functional_type": "fishing_pole", "level_band": {"min": 1, "max": 10}, "value": 18},
            "miners_pick": {"id": "miners_pick", "name": "Miner's Pick", "category": "misc", "utility_category": "mining", "functional_type": "mining_tool", "level_band": {"min": 1, "max": 10}, "value": 20},
            "fish_string": {"id": "fish_string", "name": "Fish String", "category": "misc", "utility_category": "fishing", "functional_type": "fish_string", "level_band": {"min": 1, "max": 10}, "value": 4},
            "hunting_quiver": {"id": "hunting_quiver", "name": "Hunting Quiver", "category": "container", "utility_category": "containers", "functional_type": "quiver", "level_band": {"min": 1, "max": 10}, "value": 22},
        }

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            generated = vendor_profiles.generate_vendor_stock(profile, item_records=item_records, rng=Random(5))

        self.assertEqual(len(generated["inventory"]), 5)
        self.assertTrue({"starter_pack", "coil_of_rope", "river_fishing_pole"}.issubset(set(generated["item_ids"])))
        self.assertEqual(len([item_id for item_id in generated["item_ids"] if item_id in {"miners_pick", "fish_string", "hunting_quiver"}]), 2)
        generated_entries = {entry["item_id"]: entry for entry in generated["inventory"]}
        self.assertEqual(generated_entries["starter_pack"]["utility_category"], "containers")
        self.assertEqual(generated_entries["river_fishing_pole"]["functional_type"], "fishing_pole")