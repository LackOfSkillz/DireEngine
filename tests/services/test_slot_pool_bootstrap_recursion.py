import unittest

from engine.services.slot_service import SlotService


class DummyHolder:
    pass


class BootstrapCharacter:
    def __init__(self, profession="cleric", circle=1, pool=None):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.db.profession = profession
        self.db.circle = circle
        self.db.magic_slot_pool = pool
        self.ndb._core_defaults_ready = False

    def get_profession(self):
        return self.db.profession

    def ensure_magic_slot_pool_defaults(self):
        pool = SlotService.get_pool(self)
        if pool is None:
            self.db.magic_slot_pool = None
            return None
        return pool

    def ensure_core_defaults(self):
        if bool(getattr(self.ndb, "_core_defaults_ready", False)):
            return
        self.ensure_magic_slot_pool_defaults()
        self.ndb._core_defaults_ready = True

    def get_circle(self):
        self.ensure_core_defaults()
        return max(1, int(getattr(self.db, "circle", 1) or 1))


class SlotPoolBootstrapRecursionTests(unittest.TestCase):
    def test_magic_user_with_null_pool_get_circle_completes_without_recursion(self):
        character = BootstrapCharacter(profession="cleric", circle=1, pool=None)

        self.assertEqual(character.get_circle(), 1)

    def test_magic_user_with_null_pool_self_heals_pool_on_first_get_circle(self):
        character = BootstrapCharacter(profession="cleric", circle=10, pool=None)

        character.get_circle()

        self.assertIsInstance(character.db.magic_slot_pool, dict)
        self.assertEqual(character.db.magic_slot_pool["allocations"], {"spells": {}})

    def test_magic_user_with_null_pool_initializes_correct_primary_max(self):
        character = BootstrapCharacter(profession="cleric", circle=50, pool=None)

        character.get_circle()

        self.assertEqual(character.db.magic_slot_pool["max"], 50)

    def test_ranger_with_null_pool_initializes_correct_primary_max(self):
        character = BootstrapCharacter(profession="ranger", circle=50, pool=None)

        character.get_circle()

        self.assertEqual(character.db.magic_slot_pool["max"], 50)

    def test_magic_user_with_null_pool_initializes_correct_secondary_max(self):
        character = BootstrapCharacter(profession="empath", circle=50, pool=None)

        character.get_circle()

        self.assertEqual(character.db.magic_slot_pool["max"], 35)

    def test_magic_user_with_null_pool_initializes_correct_tertiary_max(self):
        character = BootstrapCharacter(profession="paladin", circle=50, pool=None)

        character.get_circle()

        self.assertEqual(character.db.magic_slot_pool["max"], 26)

    def test_non_magic_user_get_circle_does_not_create_pool(self):
        character = BootstrapCharacter(profession="barbarian", circle=10, pool=None)

        self.assertEqual(character.get_circle(), 10)
        self.assertIsNone(character.db.magic_slot_pool)

    def test_existing_pool_is_preserved_when_get_circle_runs(self):
        pool = {"max": 10, "allocations": {"spells": {"burden": 1}, "feats": {}}}
        character = BootstrapCharacter(profession="cleric", circle=10, pool=pool)

        character.get_circle()

        self.assertEqual(character.db.magic_slot_pool["allocations"]["spells"], {"burden": 1})
        self.assertEqual(character.db.magic_slot_pool["allocations"]["feats"], {})

    def test_circle_one_initializes_correctly_without_recursion(self):
        character = BootstrapCharacter(profession="cleric", circle=1, pool=None)

        self.assertEqual(character.get_circle(), 1)
        self.assertEqual(character.db.magic_slot_pool["max"], 1)

    def test_circle_one_hundred_initializes_correctly_without_recursion(self):
        character = BootstrapCharacter(profession="cleric", circle=100, pool=None)

        self.assertEqual(character.get_circle(), 100)
        self.assertEqual(character.db.magic_slot_pool["max"], 75)

    def test_get_pool_self_heals_null_pool_directly(self):
        character = BootstrapCharacter(profession="cleric", circle=10, pool=None)

        pool = SlotService.get_pool(character)

        self.assertIs(pool, character.db.magic_slot_pool)
        self.assertEqual(pool["max"], 10)


if __name__ == "__main__":
    unittest.main()