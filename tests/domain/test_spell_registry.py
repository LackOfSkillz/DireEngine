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