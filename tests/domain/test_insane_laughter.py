import unittest

from domain.abilities.roars.insane_laughter import InsaneLaughterRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class InsaneLaughterTests(unittest.TestCase):
    def test_insane_laughter_sets_attack_roundtime_penalty(self):
        actor, target, _room = make_actor_and_target()

        result = InsaneLaughterRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_attack_roundtime_penalty(target), 0)