import unittest

from domain.abilities.roars.mage_lament import MagesLamentRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class MagesLamentTests(unittest.TestCase):
    def test_mages_lament_applies_magic_attack_penalty(self):
        actor, target, _room = make_actor_and_target()

        result = MagesLamentRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_magic_penalty(target, "magic_attack"), 0)