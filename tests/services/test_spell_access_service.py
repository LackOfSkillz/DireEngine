import unittest

from domain.spells.spell_definitions import get_spell
from engine.services.spell_access_service import SpellAccessService
from engine.services.spellbook_service import SpellbookService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="commoner", circle=1, skills=None):
        self.db = DummyHolder()
        self.profession = profession
        self.db.circle = circle
        self.skills = dict(skills or {"primary_magic": 100})

    def get_profession(self):
        return self.profession

    def get_skill(self, skill_name):
        return self.skills.get(skill_name, 0)

    def ensure_core_defaults(self):
        SpellbookService.ensure_spellbook_defaults(self)


class SpellAccessServiceTests(unittest.TestCase):
    def test_wrong_profession_fails(self):
        character = DummyCharacter(profession="cleric")
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You cannot comprehend that spell.", result.errors)

    def test_not_learned_fails(self):
        character = DummyCharacter(profession="empath")
        character.ensure_core_defaults()
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You have not learned that spell.", result.errors)

    def test_low_circle_fails(self):
        character = DummyCharacter(profession="empath", circle=0)
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertFalse(result.success)
        self.assertIn("You are not experienced enough.", result.errors)

    def test_valid_spell_succeeds(self):
        character = DummyCharacter(profession="empath", circle=1, skills={"primary_magic": 20})
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "npc")
        spell = get_spell("empath_heal")

        result = SpellAccessService.can_use_spell(character, spell)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_id"], "empath_heal")

    def test_learn_spell_validates_acquisition_method(self):
        character = DummyCharacter(profession="cleric", circle=1)
        character.ensure_core_defaults()

        invalid = SpellbookService.learn_spell(character, "cleric_minor_heal", "ritual")
        npc = SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")
        duplicate = SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")

        self.assertFalse(invalid.success)
        self.assertIn("You cannot learn that spell that way.", invalid.errors)
        self.assertTrue(npc.success)
        self.assertFalse(duplicate.success)
        self.assertIn("You already know that spell.", duplicate.errors)

    def test_known_spell_tracks_method_and_circle(self):
        character = DummyCharacter(profession="cleric", circle=3)
        character.ensure_core_defaults()

        result = SpellbookService.learn_spell(character, "cleric_minor_heal", "book")

        self.assertTrue(result.success)
        self.assertTrue(SpellbookService.has_spell(character, "cleric_minor_heal"))
        self.assertEqual(character.db.spellbook["known_spells"]["cleric_minor_heal"]["learned_via"], "book")
        self.assertEqual(character.db.spellbook["known_spells"]["cleric_minor_heal"]["circle_learned"], 3)

    def test_list_helpers_filter_unknown_spells(self):
        character = DummyCharacter(profession="empath", circle=1)
        character.ensure_core_defaults()
        SpellbookService.learn_spell(character, "empath_heal", "player")

        known = SpellAccessService.list_known_spells(character)
        available = SpellAccessService.list_available_spells(character)

        self.assertEqual([spell.id for spell in known], ["empath_heal"])
        self.assertEqual([spell.id for spell in available], ["empath_heal"])

    def test_integration_requires_learning_then_allows_use(self):
        empath = DummyCharacter(profession="empath", circle=1, skills={"primary_magic": 20})
        empath.ensure_core_defaults()
        spell = get_spell("empath_heal")

        before = SpellAccessService.can_use_spell(empath, spell)
        learned = SpellbookService.learn_spell(empath, "empath_heal", "npc")
        after = SpellAccessService.can_use_spell(empath, spell)
        wrong_profession = DummyCharacter(profession="cleric", circle=1, skills={"primary_magic": 20})
        wrong_profession.ensure_core_defaults()
        SpellbookService.learn_spell(wrong_profession, "cleric_minor_heal", "npc")
        wrong_after = SpellAccessService.can_use_spell(wrong_profession, spell)

        self.assertFalse(before.success)
        self.assertTrue(learned.success)
        self.assertTrue(after.success)
        self.assertFalse(wrong_after.success)
        self.assertIn("You cannot comprehend that spell.", wrong_after.errors)


if __name__ == "__main__":
    unittest.main()