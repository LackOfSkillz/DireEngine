import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_stat_info import CmdStatInfo


class _StatCaller:
    def __init__(self, race="human", tdp=600, stats=None):
        self.db = SimpleNamespace(
            race=race,
            tdp=tdp,
            stats=dict(stats or {}),
        )
        self.messages = []

    def ensure_core_defaults(self):
        return None

    def get_stat(self, name):
        return int((self.db.stats or {}).get(name, 0) or 0)

    def msg(self, text):
        self.messages.append(str(text))


class StatInfoCommandTests(unittest.TestCase):
    def _run(self, cmdstring, race="human", tdp=600, stats=None):
        caller = _StatCaller(race=race, tdp=tdp, stats=stats or {cmdstring: 21})
        command = SimpleNamespace(caller=caller, cmdstring=cmdstring, key="strength")
        CmdStatInfo.func(command)
        return caller.messages[-1]

    def test_strength_displays_current_value(self):
        output = self._run("strength", stats={"strength": 21})
        self.assertIn("Current value: 21", output)

    def test_strength_displays_human_modifier_and_cost(self):
        output = self._run("strength", race="human", stats={"strength": 21})
        self.assertIn("Racial modifier: +0", output)
        self.assertIn("Cost to raise to 22: 63 TDPs", output)

    def test_strength_displays_volgrin_modifier_and_cost(self):
        output = self._run("strength", race="volgrin", stats={"strength": 21})
        self.assertIn("Racial modifier: -3", output)
        self.assertIn("Cost to raise to 22: 33 TDPs", output)

    def test_intelligence_command_works_via_alias(self):
        output = self._run("intelligence", race="aethari", stats={"intelligence": 30})
        self.assertIn("Intelligence", output)
        self.assertIn("Current value: 30", output)

    def test_charisma_command_shows_tdp_total(self):
        output = self._run("charisma", tdp=712, stats={"charisma": 18})
        self.assertIn("Time Development Points available: 712", output)

    def test_discipline_command_includes_description(self):
        output = self._run("discipline", stats={"discipline": 14})
        self.assertIn("experience pool size and concentration", output)
