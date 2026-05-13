import unittest

from domain.combat.damage import compute_damage


class FixedCombatRng:
    def __init__(self, *values):
        self._values = list(values)

    def roll(self):
        return self._values.pop(0) if self._values else 50


class FixedRandom:
    def __init__(self, *values):
        self._values = list(values)

    def randint(self, start, _end):
        return self._values.pop(0) if self._values else start


class DamageTests(unittest.TestCase):
    def test_compute_damage_uses_double_average_rolls_and_leftover_multiplier(self):
        profile = {
            "puncture": 10,
            "slice": 20,
            "impact": 5,
            "power": 50,
            "strength": 100,
            "current_damage": 0,
        }

        result = compute_damage(profile, attacker_strength=30, leftover_of=20, maneuver="swing", rng=FixedRandom(6, 8, 10, 12, 3, 4, 10), combat_rng=FixedCombatRng(20))

        self.assertGreater(result.slice, result.puncture)
        self.assertGreater(result.total, 0)
        self.assertEqual(result.multiplier_seed, 140)

    def test_compute_damage_scales_for_durability_and_ammo(self):
        profile = {
            "puncture": 20,
            "slice": 0,
            "impact": 0,
            "power": 0,
            "strength": 100,
            "current_damage": 50,
        }

        result = compute_damage(profile, attacker_strength=10, leftover_of=0, maneuver="thrust", rng=FixedRandom(5, 5), ammo_profile={"puncture": 50})

        self.assertGreaterEqual(result.puncture, 0)
        self.assertLess(result.puncture, 20)


if __name__ == "__main__":
    unittest.main()