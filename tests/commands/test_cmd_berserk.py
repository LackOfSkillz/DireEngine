import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_berserk import CmdBerserk


class _Caller:
    def __init__(self, profession="barbarian"):
        self.profession = profession
        self.messages = []

    def is_profession(self, profession):
        return self.profession == str(profession)

    def msg(self, text):
        self.messages.append(str(text))


class CmdBerserkTests(unittest.TestCase):
    def test_off_class_message_is_canonical_gate(self):
        caller = _Caller(profession="cleric")
        command = SimpleNamespace(caller=caller, args="")

        CmdBerserk.func(command)

        self.assertEqual(caller.messages[-1], "You do not have the facilities to properly channel your rage.")

    def test_modifierless_prompt_mentions_single_canonical_berserk(self):
        caller = _Caller()
        command = SimpleNamespace(caller=caller, args="power")

        CmdBerserk.func(command)

        self.assertIn("learned automatically at 2nd level", caller.messages[0])
        self.assertIn("Use BERSERK with no modifier", caller.messages[1])


if __name__ == "__main__":
    unittest.main()