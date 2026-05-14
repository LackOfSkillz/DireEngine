import os
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from server.conf import at_server_startstop


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, teaching=False, learning_mindstate=0):
        self.db = DummyHolder()
        self.db.is_npc = False
        self.db.skills = {"empathy": {"mindstate": learning_mindstate}}
        self.db.states = {"learning_from": "mentor"} if teaching else {}
        self.learning_calls = 0
        self.teaching_calls = 0

    def process_learning_pulse(self):
        self.learning_calls += 1

    def process_teaching_pulse(self):
        self.teaching_calls += 1


class TeachingTickTests(unittest.TestCase):
    def test_teaching_tick_only_processes_teaching_branch(self):
        teacher = DummyCharacter(teaching=True, learning_mindstate=34)
        learner = DummyCharacter(teaching=False, learning_mindstate=34)

        with patch.object(at_server_startstop.settings, "ENABLE_GLOBAL_STATUS_TICK", True), patch(
            "server.conf.at_server_startstop._iter_tick_characters",
            return_value=[teacher, learner],
        ), patch("server.conf.at_server_startstop._log_slow_tick"):
            at_server_startstop.process_teaching_tick()

        self.assertEqual(teacher.learning_calls, 0)
        self.assertEqual(teacher.teaching_calls, 1)
        self.assertEqual(learner.learning_calls, 0)
        self.assertEqual(learner.teaching_calls, 0)

    def test_legacy_learning_tick_wrapper_delegates_to_teaching_tick(self):
        with patch("server.conf.at_server_startstop.process_teaching_tick") as delegated:
            at_server_startstop.process_learning_tick()
        delegated.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()