import unittest

from domain.combat.rng import CombatRng


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, _start, _end):
        if not self._values:
            raise AssertionError("No more RNG values available")
        return self._values.pop(0)


class CombatRngTests(unittest.TestCase):
    def test_roll_without_open_uses_single_4d50_batch(self):
        """GSL S00265: if the first die is below 50, the combat RNG stops after one 4d50 batch."""
        rng = CombatRng(FixedRandom(10, 20, 30, 40))

        self.assertEqual(rng.roll(), 100)

    def test_roll_with_open_adds_second_4d50_batch(self):
        """GSL S00265: a first die of 50 opens and appends another 4d50 batch."""
        rng = CombatRng(FixedRandom(50, 10, 10, 10, 5, 5, 5, 5))

        self.assertEqual(rng.roll(), 100)


if __name__ == "__main__":
    unittest.main()