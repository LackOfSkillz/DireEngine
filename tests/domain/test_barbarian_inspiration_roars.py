import unittest

from domain.abilities.roars.bloodthirst import BloodthirstRoar
from domain.abilities.roars.bravery import BraveryRoar
from domain.abilities.roars.honor import HonorRoar
from domain.abilities.roars.nobility import NobilityRoar
from domain.abilities.roars.pride import PrideRoar
from domain.abilities.roars.steadfastness import SteadfastnessRoar
from domain.abilities.roars.superiority import SuperiorityRoar
from domain.abilities.roars.vengeance import VengeanceRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import make_actor_and_ally


class BarbarianInspirationRoarTests(unittest.TestCase):
    def test_honor_applies_charisma_bonus(self):
        actor, ally, _npc, _room = make_actor_and_ally()

        result = HonorRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 4)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_stat_modifier(ally, "charisma"), 0)

    def test_vengeance_clears_stun_and_grants_resistance(self):
        actor, ally, _npc, _room = make_actor_and_ally()
        ally.db.stunned = True
        ally.db.stunned_until = 50.0

        result = VengeanceRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 5)

        self.assertTrue(result.success)
        self.assertFalse(ally.db.stunned)
        self.assertGreater(RoarService.get_stun_resistance_bonus(ally), 0)

    def test_steadfastness_adds_hp_and_reduces_fatigue(self):
        actor, ally, _npc, _room = make_actor_and_ally()
        ally.db.hp = 60
        ally.db.fatigue = 25

        result = SteadfastnessRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 6)

        self.assertTrue(result.success)
        self.assertGreater(ally.db.hp, 60)
        self.assertLess(ally.db.fatigue, 25)
        self.assertGreater(RoarService.get_temp_hp_bonus(ally), 0)

    def test_pride_boosts_balance_and_reduces_roundtime(self):
        actor, ally, _npc, _room = make_actor_and_ally()
        ally.set_balance(50)

        result = PrideRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 6)

        self.assertTrue(result.success)
        self.assertGreater(ally.balance, 50)
        self.assertLess(RoarService.get_attack_roundtime_penalty(ally), 0.0)
        self.assertLess(RoarService.get_stat_modifier(ally, "wisdom"), 0)

    def test_nobility_applies_multiple_opponent_skill_bonus(self):
        actor, ally, _npc, _room = make_actor_and_ally()

        result = NobilityRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 8)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_skill_modifier(ally, "multiple_engaged_opponent"), 0)

    def test_bravery_applies_fear_resistance(self):
        actor, ally, _npc, _room = make_actor_and_ally()

        result = BraveryRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 7)

        self.assertTrue(result.success)
        self.assertGreater(RoarService.get_fear_resistance(ally), 0)

    def test_bloodthirst_applies_berserk_saf_reduction_and_offense_bonus(self):
        actor, ally, _npc, _room = make_actor_and_ally()
        ally.set_state("barbarian_berserk", {"name": "frenzy", "expires_at": RoarService.now() + 30})
        starting_inner_fire = ally.get_inner_fire()

        result = BloodthirstRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 9)

        self.assertTrue(result.success)
        self.assertLess(ally.get_inner_fire(), starting_inner_fire)
        self.assertGreater(RoarService.get_stat_modifier(ally, "strength"), 0)
        self.assertLess(RoarService.get_offense_penalty(ally, "melee_accuracy"), 0)

    def test_bloodthirst_expiry_adds_fatigue_cost(self):
        actor, ally, _npc, _room = make_actor_and_ally()
        ally.db.fatigue = 10
        BloodthirstRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 9)
        payload = ally.get_state(RoarService.BLOODTHIRST_STATE_KEY)
        payload["expires_at"] = 0.0
        ally.set_state(RoarService.BLOODTHIRST_STATE_KEY, payload)

        RoarService.get_offense_penalty(ally, "melee_accuracy")

        self.assertGreater(ally.db.fatigue, 10)
        self.assertIsNone(ally.get_state(RoarService.BLOODTHIRST_STATE_KEY))

    def test_superiority_applies_defense_bonuses(self):
        actor, ally, _npc, _room = make_actor_and_ally()

        result = SuperiorityRoar.begin_roar(actor, [ally], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 8)

        self.assertTrue(result.success)
        self.assertLess(RoarService.get_defense_penalty(ally, "evasion"), 0)
        self.assertLess(RoarService.get_defense_penalty(ally, "parry"), 0)
        self.assertLess(RoarService.get_defense_penalty(ally, "shield"), 0)