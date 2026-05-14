import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.systems.exp_pulse import SKILL_GROUP_OFFSETS
from world.systems.skills import (
    FEEDBACK_COOLDOWN,
    SkillState,
    award_xp,
    calculate_mindstate,
    handle_mindstate_change,
    normalized_mindstate_drain_modifier,
)


class DummyOwner:
    def __init__(self, *, feedback=True):
        self.db = SimpleNamespace(
            exp_feedback=feedback,
            stats={"intelligence": 30, "discipline": 30, "wisdom": 30},
        )
        self.ndb = SimpleNamespace(mind_lock_notifications={})
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


class RuntimeLearningTests(unittest.TestCase):
    def test_calculate_mindstate_uses_linear_35_band_scale(self):
        self.assertEqual(calculate_mindstate(0, 100), 0)
        self.assertEqual(calculate_mindstate(50, 100), 17)
        self.assertEqual(calculate_mindstate(100, 100), 34)

    def test_award_xp_mind_lock_notification_is_rate_limited(self):
        skill = SkillState("light_edge", owner=DummyOwner())
        skill.rank = 100
        skill.skillset = "primary"
        skill.recalc_pool()
        skill.pool = skill.max_pool
        skill.update_mindstate()

        with patch("world.systems.skills.send_untargeted_action") as send_action:
            first = award_xp(skill, 50)
            second = award_xp(skill, 50)

        self.assertEqual(first, 0.0)
        self.assertEqual(second, 0.0)
        send_action.assert_called_once()
        self.assertIn("too saturated", send_action.call_args.kwargs["actor_message"])

    def test_handle_mindstate_change_notifies_on_threshold_crossing(self):
        skill = SkillState("light_edge", owner=DummyOwner())
        skill.last_mindstate_sent = 24
        skill.mindstate = 26

        with patch("world.systems.skills.send_untargeted_action") as send_action:
            notified = handle_mindstate_change(skill, "captivated", now=FEEDBACK_COOLDOWN + 1)

        self.assertTrue(notified)
        send_action.assert_called_once()
        self.assertIn("fascinated", send_action.call_args.kwargs["actor_message"])

    def test_handle_mindstate_change_uses_distinct_mind_lock_message(self):
        skill = SkillState("light_edge", owner=DummyOwner())
        skill.last_mindstate_sent = 33
        skill.mindstate = 34

        with patch("world.systems.skills.send_untargeted_action") as send_action:
            notified = handle_mindstate_change(skill, "mind lock", now=FEEDBACK_COOLDOWN + 1)

        self.assertTrue(notified)
        self.assertIn("Your mind locks", send_action.call_args.kwargs["actor_message"])

    def test_mindstate_weighting_increases_with_higher_band(self):
        self.assertGreater(normalized_mindstate_drain_modifier(34), normalized_mindstate_drain_modifier(0))

    def test_exp_pulse_offsets_cover_all_ten_canonical_groups(self):
        self.assertEqual(sorted(SKILL_GROUP_OFFSETS.keys()), list(range(0, 200, 20)))


if __name__ == "__main__":
    unittest.main()