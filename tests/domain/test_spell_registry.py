import unittest

from domain.spells.spell_definitions import SPELL_REGISTRY, Spell, get_spell


class SpellRegistryTests(unittest.TestCase):
    def test_registry_contains_seed_spells(self):
        self.assertIn("empath_heal", SPELL_REGISTRY)
        self.assertIn("cleric_minor_heal", SPELL_REGISTRY)
        self.assertIn("daze", SPELL_REGISTRY)
        self.assertIn("slow", SPELL_REGISTRY)

    def test_registry_contains_migrated_legacy_room_and_utility_spells(self):
        for spell_id in ["hinder", "shielding", "glimmer", "radiant_burst", "shared_guard", "cleanse"]:
            with self.subTest(spell_id=spell_id):
                self.assertIn(spell_id, SPELL_REGISTRY)

    def test_get_spell_returns_dataclass(self):
        spell = get_spell("empath_heal")

        self.assertIsInstance(spell, Spell)
        self.assertEqual(spell.name, "Heal")
        self.assertEqual(spell.allowed_professions, ["empath"])

    def test_analogous_patterns_seed_metadata_matches_canon(self):
        burden = get_spell("burden")
        gauge_flow = get_spell("gauge_flow")
        strange_arrow = get_spell("strange_arrow")
        manifest_force = get_spell("manifest_force")

        self.assertEqual(burden.slot_cost, 1)
        self.assertEqual(burden.apprentice_until_circle, 10)
        self.assertNotIn("apprentice", burden.acquisition_methods)
        self.assertEqual(gauge_flow.slot_cost, 2)
        self.assertIsNone(gauge_flow.apprentice_until_circle)
        self.assertNotIn("apprentice", gauge_flow.acquisition_methods)
        self.assertEqual(strange_arrow.slot_cost, 1)
        self.assertEqual(strange_arrow.apprentice_until_circle, 10)
        self.assertNotIn("apprentice", strange_arrow.acquisition_methods)
        self.assertEqual(manifest_force.slot_cost, 1)
        self.assertEqual(manifest_force.apprentice_until_circle, 10)
        self.assertEqual(manifest_force.acquisition_methods, ["scroll"])
        self.assertIn("trader", burden.allowed_professions)

    def test_all_structured_spells_define_required_fields(self):
        for spell_id, spell in SPELL_REGISTRY.items():
            with self.subTest(spell_id=spell_id):
                self.assertTrue(str(spell.spell_type or "").strip())
                self.assertTrue(str(spell.mana_type or "").strip())
                self.assertTrue(list(spell.allowed_professions or []))
                self.assertGreater(int(spell.safe_mana or 0), 0)
                self.assertGreater(int(spell.base_difficulty or 0), 0)


if __name__ == "__main__":
    unittest.main()