import unittest

from domain.abilities.roars.slash_the_shadows import SlashTheShadowsRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_target


class SlashTheShadowsTests(unittest.TestCase):
    def test_slash_the_shadows_breaks_stealth_and_penalizes_hiding(self):
        actor, target, _room = make_actor_and_target()
        target.hidden = True
        target.db.invisible = True
        target.set_state("invisible", {"expires_at": RoarService.now() + 10})

        result = SlashTheShadowsRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertFalse(target.hidden)
        self.assertFalse(target.db.invisible)
        self.assertLess(RoarService.get_skill_modifier(target, "stealth"), 0)