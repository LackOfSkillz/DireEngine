import unittest

from engine.services.slot_service import SlotService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="commoner", circle=1):
        self.db = DummyHolder()
        self.db.profession = profession
        self.db.circle = circle
        self.db.magic_slot_pool = None

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle


class SlotServiceTests(unittest.TestCase):
    def test_non_magic_profession_has_no_pool(self):
        character = DummyCharacter(profession="barbarian", circle=10)

        self.assertIsNone(SlotService.get_pool(character))
        self.assertEqual(SlotService.get_available_slots(character), 0)

    def test_primary_curve_matches_canonical_checkpoints(self):
        character = DummyCharacter(profession="cleric", circle=1)
        self.assertEqual(SlotService.get_pool(character)["max"], 1)
        character.db.circle = 10
        self.assertEqual(SlotService.get_pool(character)["max"], 10)
        character.db.circle = 50
        self.assertEqual(SlotService.get_pool(character)["max"], 50)
        character.db.circle = 100
        self.assertEqual(SlotService.get_pool(character)["max"], 75)

    def test_secondary_curve_matches_canonical_checkpoints(self):
        character = DummyCharacter(profession="empath", circle=1)
        self.assertEqual(SlotService.get_pool(character)["max"], 1)
        character.db.circle = 10
        self.assertEqual(SlotService.get_pool(character)["max"], 10)
        character.db.circle = 50
        self.assertEqual(SlotService.get_pool(character)["max"], 35)
        character.db.circle = 100
        self.assertEqual(SlotService.get_pool(character)["max"], 60)

    def test_tertiary_curve_matches_canonical_checkpoints(self):
        character = DummyCharacter(profession="paladin", circle=1)
        self.assertEqual(SlotService.get_pool(character)["max"], 1)
        character.db.circle = 10
        self.assertEqual(SlotService.get_pool(character)["max"], 6)
        character.db.circle = 50
        self.assertEqual(SlotService.get_pool(character)["max"], 26)
        character.db.circle = 100
        self.assertEqual(SlotService.get_pool(character)["max"], 51)

    def test_trader_is_treated_as_magic_user(self):
        character = DummyCharacter(profession="trader", circle=10)

        self.assertEqual(SlotService.get_pool(character)["max"], 6)

    def test_allocation_and_deallocation_round_trip(self):
        character = DummyCharacter(profession="cleric", circle=10)

        self.assertTrue(SlotService.allocate(character, "spells", "burden", 1))
        self.assertEqual(SlotService.get_used_slots(character), 1)
        self.assertEqual(SlotService.get_available_slots(character), 9)
        self.assertEqual(SlotService.deallocate(character, "spells", "burden"), 1)
        self.assertEqual(SlotService.get_used_slots(character), 0)

    def test_allocation_fails_when_slots_insufficient(self):
        character = DummyCharacter(profession="paladin", circle=10)

        self.assertFalse(SlotService.allocate(character, "spells", "impossible", 7))
        self.assertEqual(SlotService.get_used_slots(character), 0)

    def test_multi_category_allocations_share_pool(self):
        character = DummyCharacter(profession="cleric", circle=10)

        self.assertTrue(SlotService.allocate(character, "spells", "burden", 1))
        self.assertTrue(SlotService.allocate(character, "feats", "magic_theorist", 1))
        pool = SlotService.get_pool(character)

        self.assertEqual(pool["allocations"]["spells"]["burden"], 1)
        self.assertEqual(pool["allocations"]["feats"]["magic_theorist"], 1)
        self.assertEqual(SlotService.get_used_slots(character), 2)

    def test_recompute_max_preserves_allocations(self):
        character = DummyCharacter(profession="cleric", circle=10)
        SlotService.allocate(character, "spells", "burden", 1)

        character.db.circle = 50
        pool = SlotService.recompute_max(character)

        self.assertEqual(pool["max"], 50)
        self.assertEqual(pool["allocations"]["spells"]["burden"], 1)

    def test_primary_curve_outpaces_tertiary_at_same_circle(self):
        cleric = DummyCharacter(profession="cleric", circle=50)
        paladin = DummyCharacter(profession="paladin", circle=50)

        self.assertGreater(SlotService.get_pool(cleric)["max"], SlotService.get_pool(paladin)["max"])


if __name__ == "__main__":
    unittest.main()