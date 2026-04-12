import unittest

from domain.wounds.models import copy_default_injuries
from engine.services.injury_service import InjuryService
from engine.services.state_service import StateService


class DummyTarget:
	def __init__(self):
		self.pk = None
		self.messages = []
		self.db = type(
			"DB",
			(),
			{
				"hp": 100,
				"max_hp": 100,
				"injuries": copy_default_injuries(),
				"is_dead": False,
				"disguised": False,
				"post_ambush_grace": False,
				"post_ambush_grace_until": 0.0,
				"is_npc": False,
				"bleed_state": "none",
				"in_combat": False,
				"stabilized_until": 0.0,
				"stability_strength": 0.0,
			},
		)()

	def ensure_core_defaults(self):
		return None

	def msg(self, text):
		self.messages.append(str(text))

	def set_hp(self, value):
		self.db.hp = int(value)

	def is_surprised(self):
		return False

	def format_body_part_name(self, part, title=False):
		text = str(part).replace("_", " ")
		return text.title() if title else text

	def get_possessive_name(self, looker=None):
		return "target's"


class InjuryServiceTests(unittest.TestCase):
	def test_apply_hit_wound_updates_location_state(self):
		target = DummyTarget()
		result = InjuryService.apply_hit_wound(target, "left_arm", 9, damage_type="slice", critical=False)
		self.assertTrue(result.success)
		self.assertTrue(result.data["applied"])
		self.assertGreater(target.db.injuries["left_arm"]["external"], 0)
		self.assertEqual(target.messages, [])
		self.assertEqual(target.messages, [])

	def test_stabilize_wound_sets_tend_state(self):
		target = DummyTarget()
		InjuryService.apply_hit_wound(target, "head", 10, damage_type="slice", critical=False)
		result = InjuryService.stabilize_wound(target, "head", skill_result=20, heal_amount=3)
		self.assertTrue(result.success)
		self.assertTrue(target.db.injuries["head"]["tended"])
		self.assertGreater(target.db.injuries["head"]["tend"]["strength"], 0)
		self.assertEqual(target.messages, [])

	def test_process_bleed_tick_returns_events_without_service_messages(self):
		target = DummyTarget()
		target.pk = 1
		target.db.injuries["head"]["bleed"] = 4
		result = InjuryService.process_bleed_tick(target)
		self.assertTrue(result.success)
		self.assertGreaterEqual(result.data["hp_loss"], 0)
		self.assertIsInstance(result.data.get("injury_events", []), list)
		self.assertEqual(target.messages, [])
		self.assertEqual(target.messages, [])

	def test_process_bleed_tick_returns_events_without_service_messages(self):
		target = DummyTarget()
		target.pk = 1
		target.db.injuries["head"]["bleed"] = 4
		result = InjuryService.process_bleed_tick(target)
		self.assertTrue(result.success)
		self.assertGreaterEqual(result.data["hp_loss"], 0)
		self.assertIsInstance(result.data.get("injury_events", []), list)
		self.assertEqual(target.messages, [])

	def test_state_service_damage_applies_hp_and_wound(self):
		target = DummyTarget()
		result = StateService.apply_damage(target, 12, location="right_leg", damage_type="impact", critical=True)
		self.assertTrue(result.success)
		self.assertEqual(target.db.hp, 88)
		self.assertGreaterEqual(target.db.injuries["right_leg"]["bruise"], 12)


if __name__ == "__main__":
	unittest.main()