import unittest

from engine.presenters.injury_presenter import InjuryPresenter
from engine.services.result import ActionResult


class DummyTarget:
	def __init__(self):
		self.messages = []

	def msg(self, text):
		self.messages.append(str(text))


class InjuryPresenterTests(unittest.TestCase):
	def test_present_result_renders_payload_events(self):
		target = DummyTarget()
		result = ActionResult.ok(
			data={
				"injury_events": [
					{"event": "apply_wound", "kind": "badly_damaged", "part_display": "left arm"},
					{"event": "bleed_state", "new_state": "moderate"},
				],
			}
		)
		InjuryPresenter.present_result(target, result)
		self.assertEqual(
			target.messages,
			[
				"Your left arm is badly damaged!",
				"Your wounds are bleeding steadily.",
			],
		)


if __name__ == "__main__":
	unittest.main()import unittest

from engine.presenters.injury_presenter import InjuryPresenter
from engine.services.result import ActionResult


class DummyTarget:
	def __init__(self):
		self.messages = []

	def msg(self, text):
		self.messages.append(str(text))


class InjuryPresenterTests(unittest.TestCase):
	def test_present_result_renders_payload_events(self):
		target = DummyTarget()
		result = ActionResult.ok(
			data={
				"injury_events": [
					{"event": "apply_wound", "kind": "badly_damaged", "part_display": "left arm"},
					{"event": "bleed_state", "new_state": "moderate"},
				],
			}
		)
		InjuryPresenter.present_result(target, result)
		self.assertEqual(
			target.messages,
			[
				"Your left arm is badly damaged!",
				"Your wounds are bleeding steadily.",
			],
		)


if __name__ == "__main__":
	unittest.main()