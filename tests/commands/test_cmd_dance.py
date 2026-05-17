import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_dance import CmdDance
from engine.services.result import ActionResult


class _Caller:
    def __init__(self):
        self.messages = []

    def msg(self, text):
        self.messages.append(str(text))


class CmdDanceTests(unittest.TestCase):
    def test_bare_dance_relays_known_list(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="")

        with patch("commands.cmd_dance.DanceService.begin_dance", return_value=ActionResult.ok(messages=["Known dances: Swan"])):
            CmdDance.func(command)

        self.assertEqual(caller.messages[-1], "Known dances: Swan")

    def test_dance_off_relays_end_message(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="off")

        with patch("commands.cmd_dance.DanceService.end_dance", return_value=ActionResult.ok(messages=["You feel your inner fire cool, as the adrenaline pumping effect of your battle dance ends."])):
            CmdDance.func(command)

        self.assertIn("battle dance ends", caller.messages[-1])


if __name__ == "__main__":
    unittest.main()