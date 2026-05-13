import unittest

from domain.combat.cleanup import apply_cleanup


class DummyDb:
    pass


class DummyActor:
    def __init__(self, mm=10, position="standing", stunned=False):
        self.db = DummyDb()
        self.db.mm = mm
        self.db.position = position
        self.db.stunned = stunned


class CleanupTests(unittest.TestCase):
    def test_apply_cleanup_clamps_prone_stunned_mm_to_one(self):
        attacker = DummyActor(mm=12, position="prone", stunned=True)
        defender = DummyActor(mm=20, position="standing", stunned=False)

        result = apply_cleanup(attacker, defender, leftover_of=10, base_roundtime=3.0)

        self.assertEqual(result.attacker_mm, 1)
        self.assertEqual(result.roundtime, 3.0)

    def test_apply_cleanup_uses_miss_sentinel_and_five_fatigue(self):
        attacker = DummyActor()
        defender = DummyActor()

        result = apply_cleanup(attacker, defender, leftover_of=0, base_roundtime=3.0)

        self.assertEqual(result.sentinel, -5)
        self.assertEqual(result.fatigue_change, 5)


if __name__ == "__main__":
    unittest.main()