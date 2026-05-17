import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_roar import CmdRoar
from engine.services.result import ActionResult


class _Caller:
    def __init__(self):
        self.messages = []

    def msg(self, text):
        self.messages.append(str(text))


class CmdRoarTests(unittest.TestCase):
    def test_bare_roar_relays_exhaustion_message(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="")

        with patch("commands.cmd_roar.RoarService.invoke", return_value=ActionResult.ok(messages=["You feel ready to defeat an army!"])):
            CmdRoar.func(command)

        self.assertEqual(caller.messages[-1], "You feel ready to defeat an army!")

    def test_named_roar_relays_error_message(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="everild")

        with patch("commands.cmd_roar.RoarService.invoke", return_value=ActionResult.fail(errors=["You have not received the proper instruction in that technique."])):
            CmdRoar.func(command)

        self.assertIn("proper instruction", caller.messages[-1])


if __name__ == "__main__":
    unittest.main()