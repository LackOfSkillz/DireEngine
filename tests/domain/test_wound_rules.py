import unittest

from domain.wounds import rules
from domain.wounds.models import copy_default_injuries


class DummyTarget:
	def __init__(self, hp=100, max_hp=100):
		self.db = type("DB", (), {"hp": hp, "max_hp": max_hp})()


class WoundRuleTests(unittest.TestCase):
	def test_low_damage_does_not_always_create_wound(self):
		injuries = copy_default_injuries()
		result = rules.apply_hit_to_part(DummyTarget(), injuries, "left_arm", 3, damage_type="impact", critical=False)
		self.assertFalse(result["applied"])
		self.assertEqual(result["body_part"]["external"], 0)

	def test_existing_trauma_allows_followup_wound_application(self):
		injuries = copy_default_injuries()
		injuries["left_arm"]["external"] = 6
		result = rules.apply_hit_to_part(DummyTarget(), injuries, "left_arm", 3, damage_type="slice", critical=False)
		self.assertTrue(result["applied"])
		self.assertGreater(result["body_part"]["external"], 6)

	def test_penalties_reflect_injured_limbs(self):
		injuries = copy_default_injuries()
		injuries["right_hand"]["external"] = 25
		injuries["left_leg"]["external"] = 36
		penalties = rules.derive_penalties(injuries)
		self.assertGreater(penalties["hand_penalty"], 0)
		self.assertGreater(penalties["leg_penalty"], 0)
		self.assertGreater(penalties["movement_cost_mult"], 1.0)

	def test_bleed_tick_respects_tending_strength(self):
		injuries = copy_default_injuries()
		injuries["head"]["bleed"] = 4
		injuries["head"]["tend"] = {"strength": 2, "duration": 5, "last_applied": 0.0, "min_until": 0.0}
		injuries["head"]["tended"] = True
		result = rules.apply_bleed_tick(injuries, now=100.0, in_combat=False, stabilized_until=0.0, stability_strength=0.0)
		self.assertEqual(result["total_bleed"], 2)
		self.assertGreater(result["hp_loss"], 0)


if __name__ == "__main__":
	unittest.main()