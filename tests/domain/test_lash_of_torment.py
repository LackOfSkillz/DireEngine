import unittest

from domain.abilities.roars.lash_of_torment import LashOfTormentRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class LashOfTormentTests(unittest.TestCase):
    def test_lash_of_torment_stuns_target(self):
        actor, target, _room = make_actor_and_target()

        result = LashOfTormentRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertTrue(target.db.stunned)
        self.assertIsNotNone(target.get_state("barbarian_roar_lash_of_torment"))