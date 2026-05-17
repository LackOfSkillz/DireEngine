import unittest

from domain.abilities.roars.caution_of_the_spider import CautionOfTheSpiderRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class CautionOfTheSpiderTests(unittest.TestCase):
    def test_caution_of_the_spider_disengages_target(self):
        actor, target, _room = make_actor_and_target()

        result = CautionOfTheSpiderRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertTrue(target.disengaged)
        self.assertEqual(target.get_state("barbarian_roar_caution_of_the_spider")["retreat_steps"], 2)