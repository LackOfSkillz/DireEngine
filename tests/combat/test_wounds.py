import unittest

from domain.combat.damage import RawDamage
from domain.combat.hit_area import BodyPart
from domain.combat.wounds import apply_wounds


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, start, _end):
        return self._values.pop(0) if self._values else start


class WoundTests(unittest.TestCase):
    def test_apply_wounds_caps_hand_damage_and_generates_levels(self):
        result = apply_wounds(RawDamage(puncture=40, slice=20, impact=0), body_part=BodyPart.RIGHT_HAND, max_hp=100, current_hp=100, rng=FixedRandom(120, 90))

        self.assertGreater(result.wound_level, 0)
        self.assertLessEqual(result.hp_damage, 36)

    def test_apply_wounds_cascades_destroyed_arm_to_hand(self):
        result = apply_wounds(RawDamage(puncture=200, slice=200, impact=0), body_part=BodyPart.RIGHT_ARM, max_hp=100, current_hp=100, rng=FixedRandom(120, 90))

        self.assertIn("right_arm", result.destroyed_parts)
        self.assertIn("right_hand", result.destroyed_parts)


if __name__ == "__main__":
    unittest.main()