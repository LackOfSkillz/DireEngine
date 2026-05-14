import unittest

from engine.services.slot_service import SlotService
from engine.services.spellbook_service import SpellbookService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="cleric", circle=1):
        self.db = DummyHolder()
        self.db.profession = profession
        self.db.circle = circle
        self.db.magic_slot_pool = None

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle


class SpellbookServiceTests(unittest.TestCase):
    def test_learn_spell_fails_when_slots_insufficient(self):
        character = DummyCharacter(profession="cleric", circle=1)

        result = SpellbookService.learn_spell(character, "gauge_flow", "book")

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "insufficient_slots")
        self.assertEqual(SlotService.get_used_slots(character), 0)

    def test_learn_spell_consumes_slots_for_canonical_spell(self):
        character = DummyCharacter(profession="cleric", circle=10)

        result = SpellbookService.learn_spell(character, "manifest_force", "scroll")

        self.assertTrue(result.success)
        self.assertEqual(result.data["slots_consumed"], 1)
        self.assertEqual(SlotService.get_used_slots(character), 1)
        self.assertEqual(character.db.spellbook["known_spells"]["manifest_force"]["slot_cost"], 1)

    def test_zero_slot_spell_does_not_allocate(self):
        character = DummyCharacter(profession="cleric", circle=1)

        result = SpellbookService.learn_spell(character, "cleric_minor_heal", "npc")

        self.assertTrue(result.success)
        self.assertEqual(result.data["slots_consumed"], 0)
        self.assertEqual(SlotService.get_used_slots(character), 0)

    def test_multiple_learns_accumulate_slot_usage(self):
        character = DummyCharacter(profession="cleric", circle=10)

        first = SpellbookService.learn_spell(character, "burden", "book")
        second = SpellbookService.learn_spell(character, "gauge_flow", "book")

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(SlotService.get_used_slots(character), 3)
        self.assertEqual(SlotService.get_available_slots(character), 7)

    def test_duplicate_learning_does_not_double_allocate(self):
        character = DummyCharacter(profession="cleric", circle=10)
        SpellbookService.learn_spell(character, "burden", "book")

        result = SpellbookService.learn_spell(character, "burden", "book")

        self.assertFalse(result.success)
        self.assertEqual(SlotService.get_used_slots(character), 1)


if __name__ == "__main__":
    unittest.main()