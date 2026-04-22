import tempfile
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

import yaml

from server.systems import item_loader, vendor_profiles, weapon_generator


def _write_layer_files(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "cultures.yaml").write_text(
        "jade_isles:\n  primary_styles:\n    - graceful\n  secondary_styles:\n    - lacquered\n  materials:\n    - bronze\n    - yew\n  embellishments:\n    - engraved\nfrontier_marches:\n  primary_styles:\n    - practical\n  secondary_styles:\n    - balanced\n  materials:\n    - steel\n    - ash\n  embellishments:\n    - wrapped\n",
        encoding="utf-8",
    )
    (root / "construction_methods.yaml").write_text(
        "forged:\n  traits:\n    - solid\n    - reliable\n",
        encoding="utf-8",
    )
    (root / "function_styles.yaml").write_text(
        "executioner:\n  traits:\n    - heavy\n    - brutal\nhunter:\n  traits:\n    - efficient\n    - practical\n",
        encoding="utf-8",
    )
    (root / "age_profiles.yaml").write_text(
        "new:\n  traits:\n    - clean\n    - polished\n",
        encoding="utf-8",
    )
    (root / "embellishments.yaml").write_text(
        "none: {}\nengraved:\n  traits:\n    - etched\nwrapped:\n  traits:\n    - reinforced grip\n",
        encoding="utf-8",
    )
    (root / "trait_families.yaml").write_text(
        "weight:\n  - light\n  - heavy\n  - dense\nstyle:\n  - elegant\n  - brutal\n  - crude\n  - refined\n  - graceful\n  - practical\nhandling:\n  - precise\n  - unwieldy\n  - balanced\n  - reliable\ncondition:\n  - worn\n  - pristine\n  - ancient\n",
        encoding="utf-8",
    )
    (root / "trait_conflicts.yaml").write_text(
        "hard_conflicts:\n  - [graceful, brutal]\n  - [refined, crude]\n  - [precise, unwieldy]\nsoft_conflicts:\n  - [light, heavy]\n  - [delicate, dense]\n",
        encoding="utf-8",
    )
    (root / "trait_phrases.yaml").write_text(
        "precise: favored for controlled strikes\nbrutal: designed for crushing force\nbalanced: well-suited to varied combat\nunwieldy: difficult to control in tight quarters\ngraceful: favored for flowing cuts\npractical: made for hard travel and repeated use\nreliable: trusted to hold together under strain\nheavy: weighted toward forceful blows\nsolid: built to absorb punishment\nefficient: shaped for quick, economical motion\nclean: newly finished and free of wear\npolished: polished to a bright sheen\netched: marked with deliberate engraved detail\nlacquered: finished with a lacquered sheen\nbroad: given a broad striking profile\nbrittle: best used with deliberate care\n",
        encoding="utf-8",
    )
    (root / "description_voices.yaml").write_text(
        "functional:\n  openers:\n    - This weapon is built around\n    - This piece is constructed from\nobservational:\n  openers:\n    - Its form suggests\n    - The weapon appears to be\nhistorical:\n  openers:\n    - Forged in\n    - Crafted in\nmythic:\n  openers:\n    - Legends claim\n    - It is said that\n",
        encoding="utf-8",
    )
    (root / "material_categories.yaml").write_text(
        "blade:\n  - metal\n  - stone\n  - alloy\ngrip:\n  - wood\n  - organic\nshaft:\n  - wood\n  - organic\n",
        encoding="utf-8",
    )
    (root / "materials_metals.yaml").write_text(
        "steel:\n  category: metal\n  tier: common\n  tags: [balanced]\nbronze:\n  category: metal\n  tier: common\n  tags: [reliable]\nstarsteel:\n  category: metal\n  tier: exotic\n  tags: [keen, cosmic]\nstormsteel:\n  category: metal\n  tier: uncommon\n  tags: [charged]\n",
        encoding="utf-8",
    )
    (root / "materials_woods.yaml").write_text(
        "ash:\n  category: wood\n  tier: common\n  tags: [flexible]\nyew:\n  category: wood\n  tier: uncommon\n  tags: [elastic, ideal_for_bows]\nironwood:\n  category: wood\n  tier: uncommon\n  tags: [dense, heavy]\n",
        encoding="utf-8",
    )
    (root / "materials_organic.yaml").write_text(
        "leather_wrap:\n  category: organic\n  tier: common\n  tags: [grippy]\nbone:\n  category: organic\n  tier: common\n  tags: [light]\n",
        encoding="utf-8",
    )
    (root / "materials_stone.yaml").write_text(
        "obsidian:\n  category: stone\n  tier: uncommon\n  tags: [sharp]\n",
        encoding="utf-8",
    )
    (root / "materials_alloys.yaml").write_text(
        "shadowsteel:\n  category: alloy\n  tier: rare\n  tags: [dark, fine]\narcane_composite:\n  category: alloy\n  tier: exotic\n  tags: [magical]\n",
        encoding="utf-8",
    )


class WeaponGeneratorTests(unittest.TestCase):
    def test_load_cultures_reads_structured_layer_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                cultures = weapon_generator.load_cultures()

        self.assertIn("jade_isles", cultures)
        self.assertEqual(cultures["jade_isles"]["primary_styles"], ["graceful"])
        self.assertEqual(cultures["jade_isles"]["secondary_styles"], ["lacquered"])

    def test_low_tier_disables_secondary_culture_and_embellishment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("sword", tier="low", rng=Random(1))

        self.assertIsNone(generated["style_stack"]["secondary_culture"])
        self.assertEqual(generated["style_stack"]["embellishment"], "none")
        self.assertLessEqual(len(generated["traits"]), 1)

    def test_bow_compatibility_rules_remove_heavy_traits(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("bow", tier="high", rng=Random(2))

        self.assertNotIn("heavy", generated["traits"])
        self.assertNotIn("brutal", generated["traits"])

    def test_generated_item_payload_is_item_loader_and_vendor_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("bow", tier="mid", rng=Random(4))

        normalized = item_loader.normalize_item_payload(generated["item_payload"])
        profile = vendor_profiles.normalize_vendor_profile(
            {
                "id": "generated_bow_vendor",
                "category": "weapon",
                "level_band": {"min": 1, "max": 10},
                "stock_count": 1,
                "allowed_weapon_classes": [normalized["weapon_class"]],
                "preferred_weapon_classes": {normalized["weapon_class"]: 1.0},
                "required_tags": ["generated"],
                "allow_duplicates": True,
            }
        )

        with patch.object(vendor_profiles, "VENDOR_PROFILES", {profile["id"]: profile}):
            stock = vendor_profiles.generate_vendor_stock(profile, item_records={normalized["id"]: normalized}, rng=Random(7))

        self.assertEqual(stock["item_ids"], [normalized["id"]])

    def test_low_tier_uses_common_materials_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("sword", tier="low", rng=Random(5))

        material_tiers = {material["tier"] for material in generated["materials"].values()}
        self.assertEqual(material_tiers, {"common"})

    def test_bow_selection_prefers_flexible_shaft_materials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                selected = []
                for seed in range(10):
                    generated = weapon_generator.generate_weapon_definition("bow", tier="mid", rng=Random(seed))
                    selected.append(generated["materials"]["shaft"]["id"])

        self.assertIn("yew", selected)
        self.assertNotIn("starsteel", selected)

    def test_description_uses_natural_article_and_slot_aware_parts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                mace = weapon_generator.generate_weapon_definition("mace", tier="mid", rng=Random(202))
                bow = weapon_generator.generate_weapon_definition("bow", tier="mid", rng=Random(202))

        self.assertIn("head", mace["description"])
        self.assertRegex(mace["description"], r"built around|paired with")
        self.assertIn("stave", bow["description"])
        self.assertIn("reflects the style of the", bow["description"])

    def test_description_avoids_trait_dump_scaffolding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("sword", tier="high", rng=Random(101))

        self.assertNotIn("It carries", generated["description"])
        self.assertNotIn("In the hand, it feels", generated["description"])
        self.assertNotIn("Its finish is", generated["description"])
        self.assertIn("It is ", generated["description"])

    def test_legendary_secondary_culture_name_is_additive_and_stable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = None
                for seed in range(1, 200):
                    candidate = weapon_generator.generate_weapon_definition("sword", tier="legendary", rng=Random(seed))
                    if candidate["style_stack"]["secondary_culture"]:
                        generated = candidate
                        break

        self.assertIsNotNone(generated)
        self.assertIn(", a ", generated["name"])
        self.assertIn("of the", generated["name"])
        self.assertIn("in the manner of the", generated["name"])

    def test_trait_conflicts_are_resolved(self):
        resolved = weapon_generator._resolve_trait_conflicts(
            ["graceful", "brutal", "precise", "unwieldy", "heavy", "light"],
            tier="mid",
            rng=Random(1),
        )

        self.assertIn("graceful", resolved)
        self.assertNotIn("brutal", resolved)
        self.assertIn("precise", resolved)
        self.assertNotIn("unwieldy", resolved)
        self.assertIn("heavy", resolved)
        self.assertNotIn("light", resolved)

    def test_trait_count_respects_tier(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                low = weapon_generator.generate_weapon_definition("sword", tier="low", rng=Random(5))
                mid = weapon_generator.generate_weapon_definition("sword", tier="mid", rng=Random(5))
                high = weapon_generator.generate_weapon_definition("sword", tier="high", rng=Random(5))

        self.assertLessEqual(len(low["traits"]), 1)
        self.assertLessEqual(len(mid["traits"]), 2)
        self.assertLessEqual(len(high["traits"]), 3)

    def test_description_contains_mapped_trait_phrases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                generated = weapon_generator.generate_weapon_definition("sword", tier="mid", rng=Random(5))

        self.assertRegex(generated["description"], r"favored for|well-suited|designed for|trusted to")

    def test_voice_changes_across_tiers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                low = weapon_generator.generate_weapon_definition("dagger", tier="low", rng=Random(2))
                high = weapon_generator.generate_weapon_definition("dagger", tier="high", rng=Random(2))
                legendary = weapon_generator.generate_weapon_definition("dagger", tier="legendary", rng=Random(2))

        self.assertIn(low["style_stack"]["description_voice"], {"functional", "observational"})
        self.assertIn(high["style_stack"]["description_voice"], {"historical", "observational"})
        self.assertIn(legendary["style_stack"]["description_voice"], {"mythic", "historical", "observational"})

    def test_tiered_name_complexity_increases_by_tier(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_layer_files(root)
            with patch.object(weapon_generator, "WEAPON_LAYER_ROOT", root):
                low = weapon_generator.generate_weapon_definition("dagger", tier="low", rng=Random(5))
                mid = weapon_generator.generate_weapon_definition("dagger", tier="mid", rng=Random(5))
                high = weapon_generator.generate_weapon_definition("dagger", tier="high", rng=Random(5))
                legendary = weapon_generator.generate_weapon_definition("dagger", tier="legendary", rng=Random(5))

        self.assertGreaterEqual(len(low["name"].split()), 3)
        self.assertGreaterEqual(len(mid["name"].split()), 3)
        self.assertIn("of the", high["name"])
        self.assertIn(", a ", legendary["name"])


if __name__ == "__main__":
    unittest.main()