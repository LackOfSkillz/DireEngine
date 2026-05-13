import unittest

from domain.combat.hit_area import BodyPart, area_exists, attempt_targeted_hit, body_part_to_key, determine_hit_area


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, _start, _end):
        if not self._values:
            raise AssertionError("No more randint values available")
        return self._values.pop(0)


def injuries(**overrides):
    base = {
        "head": {"external": 0, "internal": 0, "bruise": 0},
        "chest": {"external": 0, "internal": 0, "bruise": 0},
        "abdomen": {"external": 0, "internal": 0, "bruise": 0},
        "back": {"external": 0, "internal": 0, "bruise": 0},
        "left_arm": {"external": 0, "internal": 0, "bruise": 0},
        "right_arm": {"external": 0, "internal": 0, "bruise": 0},
        "left_hand": {"external": 0, "internal": 0, "bruise": 0},
        "right_hand": {"external": 0, "internal": 0, "bruise": 0},
        "left_leg": {"external": 0, "internal": 0, "bruise": 0},
        "right_leg": {"external": 0, "internal": 0, "bruise": 0},
    }
    base.update(overrides)
    return base


class HitAreaTests(unittest.TestCase):
    def test_chest_probability_band_matches_s00047(self):
        """GSL S00047: random roll < 28 and >= 8 yields chest (b9=9)."""
        result = determine_hit_area(
            leftover_of=20,
            original_of=80,
            weapon_balance=50,
            attacker_agility=30,
            defender_reflex=20,
            rng=FixedRandom(27),
        )
        self.assertEqual(result.area, BodyPart.CHEST)
        self.assertEqual(result.area_key, "chest")

    def test_sweep_biases_to_lower_body_range(self):
        """GSL S00047: sweep rolls in the 1-40 range before the hit-area ladder."""
        result = determine_hit_area(
            leftover_of=20,
            original_of=80,
            weapon_balance=50,
            attacker_agility=30,
            defender_reflex=20,
            verb="sweep",
            rng=FixedRandom(35),
        )
        self.assertEqual(result.area, BodyPart.ABDOMEN)

    def test_targeted_chest_uses_105_difficulty_seed(self):
        """GSL S00047: chest targeting starts from b9=105 and succeeds when original OF clears the defense-scaled threshold."""
        self.assertTrue(
            attempt_targeted_hit(
                leftover_of=30,
                original_of=120,
                target_area=BodyPart.CHEST,
                weapon_balance=60,
                attacker_agility=40,
                defender_reflex=20,
            )
        )

    def test_targeted_eye_can_fail_and_retarget(self):
        """GSL S00047: failed aimed attacks fall back into a retarget path instead of forcing the aimed location."""
        result = determine_hit_area(
            leftover_of=5,
            original_of=20,
            weapon_balance=30,
            attacker_agility=10,
            defender_reflex=40,
            aimed_at=BodyPart.LEFT_EYE,
            rng=FixedRandom(27),
        )
        self.assertTrue(result.was_targeted)
        self.assertFalse(result.targeting_succeeded)
        self.assertEqual(result.area, BodyPart.CHEST)

    def test_destroyed_hand_area_falls_back_if_arm_is_destroyed(self):
        """GSL S00047 $AREA_EXISTS: a hand is unhittable when its connected arm is already destroyed at 60+."""
        self.assertFalse(area_exists(BodyPart.RIGHT_HAND, injuries(right_arm={"external": 60, "internal": 0, "bruise": 0})))

    def test_tail_roll_retargets_because_tail_hits_are_disabled(self):
        """GSL S00047 currently disables tail hits even when the defender has a tail."""
        result = determine_hit_area(
            leftover_of=20,
            original_of=80,
            weapon_balance=50,
            attacker_agility=30,
            defender_reflex=20,
            defender_has_tail=True,
            rng=FixedRandom(103, 27),
        )
        self.assertEqual(result.area, BodyPart.CHEST)
        self.assertGreaterEqual(result.retarget_count, 1)

    def test_body_part_key_bridges_eye_to_head_storage(self):
        """DRG-024a bridge: eye hits map to head-backed injury storage until separate eye wound state exists."""
        self.assertEqual(body_part_to_key(BodyPart.LEFT_EYE), "head")


if __name__ == "__main__":
    unittest.main()