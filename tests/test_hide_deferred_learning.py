import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_hide import CmdHide


class _DummyObserver:
    def __init__(self, key="observer", perception_total=15):
        self.key = key
        self.messages = []
        self._perception_total = perception_total
        self._sync_exp_skill_state = True

    def msg(self, text):
        self.messages.append(str(text))

    def get_perception_total(self):
        return self._perception_total


class _DummyCaller:
    def __init__(self, *, location=None):
        self.key = "hider"
        self.location = location
        self.db = SimpleNamespace(stealthed=False)
        self.messages = []
        self.roundtimes = []
        self.recorded = []

    def is_hidden(self):
        return False

    def is_in_roundtime(self):
        return False

    def apply_thief_roundtime(self, value):
        self.roundtimes.append(value)

    def msg(self, text):
        self.messages.append(str(text))

    def record_stealth_contest(self, *args, **kwargs):
        self.recorded.append((args, kwargs))


class _DummyHideCommand:
    def __init__(self, caller):
        self.caller = caller


class HideDeferredLearningTests(unittest.TestCase):
    def test_hide_failure_records_deferred_failure(self):
        caller = _DummyCaller(location=SimpleNamespace(contents=[]))

        with patch("commands.cmd_hide.enter_stealth", return_value=False):
            CmdHide.func(_DummyHideCommand(caller))

        self.assertEqual(len(caller.recorded), 1)
        _args, kwargs = caller.recorded[0]
        self.assertEqual(kwargs["result"]["outcome"], "fail")
        self.assertFalse(kwargs["require_hidden"])

    def test_hide_success_without_room_records_practice_attempt(self):
        caller = _DummyCaller(location=None)

        with patch("commands.cmd_hide.enter_stealth", return_value=55):
            CmdHide.func(_DummyHideCommand(caller))

        self.assertEqual(len(caller.recorded), 1)
        _args, kwargs = caller.recorded[0]
        self.assertIsNone(kwargs["result"])
        self.assertTrue(kwargs["require_hidden"])

    def test_hide_success_with_observer_records_contest_outcome(self):
        observer = _DummyObserver(perception_total=18)
        room = SimpleNamespace(contents=[])
        caller = _DummyCaller(location=room)
        room.contents = [caller, observer]

        with patch("commands.cmd_hide.enter_stealth", return_value=60), patch("commands.cmd_hide.detect", return_value=True):
            CmdHide.func(_DummyHideCommand(caller))

        self.assertEqual(len(caller.recorded), 1)
        args, kwargs = caller.recorded[0]
        self.assertEqual(args[1], 18)
        self.assertEqual(kwargs["result"]["outcome"], "fail")
        self.assertEqual(observer.messages, ["You notice hider trying to hide."])


if __name__ == "__main__":
    unittest.main()