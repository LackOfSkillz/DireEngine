import unittest

from domain.abilities.roars.anger_the_earth import AngerTheEarthRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class AngerTheEarthTests(unittest.TestCase):
    def test_anger_the_earth_reduces_balance_and_recovery(self):
        actor, target, _room = make_actor_and_target()

        result = AngerTheEarthRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertLess(target.balance, 100)
        self.assertGreater(RoarService.get_balance_recovery_penalty(target), 0)