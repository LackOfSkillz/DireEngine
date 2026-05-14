import os
import time
import unittest
from collections.abc import Mapping
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_experience import CmdExperience


class _DummySkill:
    def __init__(self, *, name, rank=0, mindstate=0, pool=0.0, max_pool=100.0, last_trained=None):
        self.name = name
        self.rank = rank
        self.rank_progress = 0.0
        self.pool = pool
        self.max_pool = max_pool
        self.mindstate = mindstate
        self.skillset = "primary"
        self.last_trained = time.time() if last_trained is None else last_trained

    def mindstate_name(self):
        if self.mindstate >= 10:
            return "learning"
        if self.mindstate > 0:
            return "dabbling"
        return "clear"


class _DummyHandler:
    def __init__(self, skills):
        self.skills = dict(skills)

    def get(self, name):
        return self.skills[name]


class _DummyCaller:
    def __init__(self):
        self.db = SimpleNamespace(
            tdp=600,
            profession="empath",
            circle=2,
            coins=500,
            skills={
                "combat": {"rank": 50},
                "light_edge": {"rank": 40},
                "parry_ability": {"rank": 18},
                "appraisal": {"rank": 12},
            },
            exp_skill_state={
                "combat": {"rank": 50},
                "light_edge": {"rank": 40},
                "parry_ability": {"rank": 18},
                "appraisal": {"rank": 12},
            },
        )
        now = time.time()
        self.exp_skills = _DummyHandler(
            {
                "combat": _DummySkill(name="combat", rank=50, mindstate=10, pool=30.0, max_pool=120.0, last_trained=now),
                "light_edge": _DummySkill(name="light_edge", rank=40, mindstate=10, pool=24.0, max_pool=100.0, last_trained=now),
                "parry_ability": _DummySkill(name="parry_ability", rank=18, mindstate=6, pool=15.0, max_pool=90.0, last_trained=now),
                "appraisal": _DummySkill(name="appraisal", rank=12, mindstate=0, pool=0.0, max_pool=80.0, last_trained=now - 9999),
            }
        )
        self.messages = []

    def ensure_core_defaults(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def get_skillset(self, skill_name):
        return "primary"

    def _sync_exp_skill_state(self, skill_name, legacy_entry=None):
        return self.exp_skills.get(skill_name)

    def get_skill_detail_entry(self, skill_name):
        if skill_name not in {"light_edge", "appraisal", "combat", "parry_ability"}:
            return None
        labels = {
            "light_edge": "learning",
            "appraisal": "clear",
            "combat": "learning",
            "parry_ability": "dabbling",
        }
        ranks = {
            "light_edge": 40,
            "appraisal": 12,
            "combat": 50,
            "parry_ability": 18,
        }
        cats = {
            "light_edge": "combat",
            "appraisal": "lore",
            "combat": "combat",
            "parry_ability": "defense",
        }
        return {
            "skill": skill_name,
            "rank": ranks[skill_name],
            "mindstate": 10 if skill_name != "appraisal" else 0,
            "label": labels[skill_name],
            "cap": 34,
            "category": cats[skill_name],
        }


class ExpCommandTests(unittest.TestCase):
    def _run(self, args=""):
        caller = _DummyCaller()
        command = SimpleNamespace(caller=caller, args=args, __doc__=CmdExperience.__doc__)
        command._show_skill_detail = lambda active_caller, query: CmdExperience._show_skill_detail(command, active_caller, query)
        command._show_circle_progress = lambda active_caller: CmdExperience._show_circle_progress(command, active_caller)
        CmdExperience.func(command)
        return caller.messages[-1]

    def test_exp_shows_only_actively_absorbing_skills(self):
        output = self._run("")
        self.assertIn("Light Edged Weapons", output)
        self.assertNotIn("Appraisal", output)
        self.assertIn("Rested EXP Stored:", output)
        self.assertIn("Current State: Awake", output)

    def test_exp_all_shows_all_skills(self):
        output = self._run("all")
        self.assertIn("Light Edged Weapons", output)
        self.assertIn("Appraisal", output)

    def test_exp_le_shows_detail(self):
        output = self._run("le")
        self.assertIn("Light Edged Weapons", output)
        self.assertIn("Current rank: 40", output)

    def test_exp_light_edge_matches_alias(self):
        output = self._run("light edge")
        self.assertIn("Light Edged Weapons", output)
        self.assertIn("Bits to next rank", output)

    def test_exp_parry_shows_dedicated_detail(self):
        output = self._run("parry")
        self.assertIn("Parry Ability", output)
        self.assertIn("Skill group: Defense", output)

    def test_exp_circle_shows_progress(self):
        output = self._run("circle")
        self.assertIn("Current Circle: 2", output)
        self.assertIn("Next Circle: 3", output)

    def test_exp_help_shows_doc(self):
        output = self._run("help")
        self.assertIn("Show skill learning and ranks", output)

    def test_exp_unknown_skill_errors_cleanly(self):
        output = self._run("nonsense")
        self.assertIn("Unknown skill", output)
