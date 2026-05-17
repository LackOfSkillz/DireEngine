import unittest

from domain.abilities.roars.weighted_justice import WeightedJusticeRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import DummyWeapon, make_actor_and_target


class WeightedJusticeTests(unittest.TestCase):
    def test_weighted_justice_forces_weapon_drop(self):
        actor, target, room = make_actor_and_target()
        target.weapon = DummyWeapon("axe")

        result = WeightedJusticeRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertIsNone(target.weapon)
        self.assertEqual(target.get_state("barbarian_roar_weighted_justice")["dropped_weapon"], "axe")
        self.assertEqual(target.get_state("effect_11822001")["dropped_weapon"], "axe")