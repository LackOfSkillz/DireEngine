import unittest

from domain.abilities.roars.screech_of_madness import ScreechOfMadnessRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class ScreechOfMadnessTests(unittest.TestCase):
    def test_screech_of_madness_sets_fear_amplification_state(self):
        actor, target, _room = make_actor_and_target()

        result = ScreechOfMadnessRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_fear_amplification(target), 0)