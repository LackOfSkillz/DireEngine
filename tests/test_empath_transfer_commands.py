import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_link import CmdLink
from commands.cmd_mend import CmdMend
from commands.cmd_take import CmdTake
from commands.cmd_touch import CmdTouch


class _Caller:
    def __init__(self):
        self.messages = []
        self.location = object()

    def msg(self, text):
        self.messages.append(str(text))

    def is_empath(self):
        return True

    def search(self, *_args, **_kwargs):
        return None

    def normalize_empath_take_selector(self, selector):
        value = str(selector or "").strip().lower()
        return value if value in {"arm", "leg", "chest", "head"} else ""


class _Target:
    def __init__(self):
        self.key = "Patient"
        self.location = object()


class _TargetingCommand:
    def __init__(self, caller, args, target):
        self.caller = caller
        self.args = args
        self._target = target

    def resolve_target(self, *_args, **_kwargs):
        return self._target, None, None, None, None

    def msg_target_matches(self, *_args, **_kwargs):
        raise AssertionError("should not be called")


class EmpathTransferCommandTests(unittest.TestCase):
    def test_touch_routes_through_service(self):
        caller = _Caller()
        target = _Target()
        target.location = caller.location
        command = _TargetingCommand(caller, "patient", target)
        result = SimpleNamespace(messages=["ok"], errors=[])

        with patch("commands.cmd_touch.WoundTransferService.touch", return_value=result) as helper:
            CmdTouch.func(command)

        helper.assert_called_once_with(caller, target)
        self.assertEqual(caller.messages[-1], "ok")

    def test_link_routes_through_service(self):
        caller = _Caller()
        target = _Target()
        target.location = caller.location
        command = _TargetingCommand(caller, "persistent patient", target)
        result = SimpleNamespace(messages=["linked"], errors=[])

        with patch("commands.cmd_link.WoundTransferService.link", return_value=result) as helper:
            CmdLink.func(command)

        helper.assert_called_once_with(caller, target, persistent=True)
        self.assertEqual(caller.messages[-1], "linked")

    def test_take_routes_through_service(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="bleeding 25")
        result = SimpleNamespace(messages=["taken"], errors=[])

        with patch("commands.cmd_take.WoundTransferService.transfer", return_value=result) as helper:
            CmdTake.func(command)

        helper.assert_called_once_with(caller, wound_type="bleeding", amount="25")
        self.assertEqual(caller.messages[-1], "taken")

    def test_mend_routes_through_service(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="self")
        result = SimpleNamespace(messages=["mended"], errors=[])

        with patch("commands.cmd_mend.WoundTransferService.mend_self", return_value=result) as helper:
            CmdMend.func(command)

        helper.assert_called_once_with(caller)
        self.assertEqual(caller.messages[-1], "mended")


if __name__ == "__main__":
    unittest.main()