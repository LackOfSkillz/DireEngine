import unittest

from domain.abilities.roars.banshees_wail import BansheesWailRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class BansheesWailTests(unittest.TestCase):
    def test_banshees_wail_sets_immobilize_state(self):
        actor, target, _room = make_actor_and_target()

        result = BansheesWailRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertTrue(RoarService.is_immobilized(target))