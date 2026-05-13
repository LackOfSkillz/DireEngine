import unittest

from domain.combat.armor import apply_armor_reduction
from domain.combat.damage import RawDamage


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, start, _end):
        return self._values.pop(0) if self._values else start


class ArmorTests(unittest.TestCase):
    def test_apply_armor_reduction_uses_flat_then_percent_stages(self):
        raw = RawDamage(puncture=20, slice=20, impact=20)
        armor = {
            "punc_res": 525,
            "slic_res": 525,
            "impa_res": 525,
            "damage": 0,
            "strength": 100,
        }

        reduced = apply_armor_reduction(raw, armor, armor_skill=60, maneuver_mod=10, multi_armor_penalty=0, rng=FixedRandom(4, 5, 4, 5, 4, 5, 0))

        self.assertLess(reduced.total, raw.total)
        self.assertEqual(reduced.flat_reduction[0], 5)
        self.assertGreaterEqual(reduced.percent_reduction[0], 20)


if __name__ == "__main__":
    unittest.main()