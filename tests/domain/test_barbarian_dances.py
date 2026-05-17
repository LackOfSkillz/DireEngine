import unittest

from domain.abilities.dances.registry import get_dance_definition_by_bit
from engine.services.dance_service import DanceService
from tests.domain.roar_test_support import DummyCombatant, DummyRoom


class BarbarianDanceDefinitionTests(unittest.TestCase):
    def _begin(self, bit_index):
        room = DummyRoom(20)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.set_spellbook2(1 << bit_index)
        definition = get_dance_definition_by_bit(bit_index)
        result = DanceService.begin_dance(actor, definition.name)
        self.assertTrue(result.success)
        return actor, DanceService.get_active_dance(actor)

    def test_swan_applies_melee_defense_and_balance(self):
        actor, payload = self._begin(1)
        self.assertEqual(payload["defense_bonuses"]["melee"], 10)
        self.assertEqual(DanceService.get_balance_bonus(actor), 8)

    def test_cobra_applies_melee_accuracy_damage_and_engagement(self):
        actor, payload = self._begin(2)
        self.assertEqual(payload["offense_bonuses"]["melee_accuracy"], 8)
        self.assertEqual(payload["offense_bonuses"]["melee_damage"], 10)
        self.assertEqual(DanceService.get_engagement_speed_bonus(actor), 10)

    def test_badger_applies_melee_parry_shield_and_multiopponent(self):
        _actor, payload = self._begin(3)
        self.assertEqual(payload["defense_bonuses"]["parry"], 10)
        self.assertEqual(payload["defense_bonuses"]["shield"], 10)
        self.assertEqual(payload["skill_modifiers"]["multiple_engaged_opponent"], 15)

    def test_eagle_applies_missile_perception_and_engagement(self):
        actor, payload = self._begin(4)
        self.assertEqual(payload["offense_bonuses"]["missile_accuracy"], 10)
        self.assertEqual(payload["skill_modifiers"]["perception"], 12)
        self.assertEqual(DanceService.get_engagement_speed_bonus(actor), 8)

    def test_bear_applies_strength_stamina_and_melee_damage(self):
        _actor, payload = self._begin(5)
        self.assertEqual(payload["stat_modifiers"]["strength"], 6)
        self.assertEqual(payload["stat_modifiers"]["stamina"], 6)
        self.assertEqual(payload["offense_bonuses"]["melee_damage"], 12)

    def test_wolverine_applies_mixed_melee_profile(self):
        actor, payload = self._begin(6)
        self.assertEqual(payload["offense_bonuses"]["melee_accuracy"], 10)
        self.assertEqual(payload["defense_bonuses"]["parry"], 8)
        self.assertEqual(DanceService.get_balance_bonus(actor), 8)

    def test_panther_applies_missile_stealth_and_stats(self):
        _actor, payload = self._begin(7)
        self.assertEqual(payload["defense_bonuses"]["missile"], 12)
        self.assertEqual(payload["skill_modifiers"]["stealth"], 12)
        self.assertEqual(payload["stat_modifiers"]["agility"], 4)

    def test_dragon_applies_broad_profile(self):
        actor, payload = self._begin(8)
        self.assertEqual(payload["offense_bonuses"]["melee_damage"], 12)
        self.assertEqual(payload["offense_bonuses"]["missile_damage"], 12)
        self.assertEqual(payload["defense_bonuses"]["shield"], 10)
        self.assertEqual(DanceService.get_engagement_speed_bonus(actor), 12)


if __name__ == "__main__":
    unittest.main()