import os
import time
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_experience import CmdExperience
from commands.cmd_tdp import CmdTDP
from typeclasses.characters import Character
from world.systems.skills import process_rank, rank_cost


class _DummyOwner:
    def __init__(self):
        self.db = SimpleNamespace(tdp=None, tdp_pool=None)
        self.sync_calls = 0

    def ensure_tdp_defaults(self):
        return Character.ensure_tdp_defaults(self)

    def sync_client_state(self):
        self.sync_calls += 1

    def on_skill_rank_gained(self, skill_id, old_rank, new_rank, ranks_gained):
        return Character.on_skill_rank_gained(self, skill_id, old_rank, new_rank, ranks_gained)


class _DummySkill:
    def __init__(self, *, name="alchemy", rank=0, rank_progress=0.0, mindstate=10, pool=40.0, max_pool=100.0):
        self.name = name
        self.rank = rank
        self.rank_progress = rank_progress
        self.mindstate = mindstate
        self.pool = pool
        self.max_pool = max_pool
        self.last_trained = time.time()
        self.owner = None

    def recalc_pool(self):
        return None

    def update_mindstate(self):
        return None

    def mindstate_name(self):
        return "attentive"


class _DummyHandler:
    def __init__(self, skills):
        self.skills = skills

    def get(self, skill_name):
        return self.skills[skill_name]


class _DummyAccount:
    def __init__(self, permissions=None):
        self._permissions = set(permissions or [])

    def check_permstring(self, permission):
        return permission in self._permissions


class _DummyCaller:
    def __init__(self, *, permissions=None, tdp=600, tdp_pool=0, skills=None):
        self.db = SimpleNamespace(tdp=tdp, tdp_pool=tdp_pool, skills={})
        self.account = _DummyAccount(permissions)
        self.messages = []
        self.exp_skills = _DummyHandler(skills or {})

    def ensure_core_defaults(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def get_skillset(self, skill_name):
        return "primary"

    def _sync_exp_skill_state(self, skill_name, legacy_entry):
        return self.exp_skills.get(skill_name)


class _DummyCommand:
    def __init__(self, caller, args=""):
        self.caller = caller
        self.args = args


class TdpFoundationTests(unittest.TestCase):
    def test_ensure_tdp_defaults_backfills_missing_values(self):
        owner = _DummyOwner()

        Character.ensure_tdp_defaults(owner)

        self.assertEqual(owner.db.tdp, 600)
        self.assertEqual(owner.db.tdp_pool, 0)

    def test_rank_gain_matches_canonical_50_rank_example(self):
        owner = _DummyOwner()

        Character.on_skill_rank_gained(owner, "alchemy", 0, 50, 50)

        self.assertEqual(owner.db.tdp, 606)
        self.assertEqual(owner.db.tdp_pool, 75)

    def test_rank_gain_matches_canonical_100_rank_example(self):
        owner = _DummyOwner()

        Character.on_skill_rank_gained(owner, "alchemy", 0, 100, 100)

        self.assertEqual(owner.db.tdp, 625)
        self.assertEqual(owner.db.tdp_pool, 50)

    def test_process_rank_awards_tdp_through_owner_hook(self):
        owner = _DummyOwner()
        skill = _DummySkill(rank=49, rank_progress=float(rank_cost(49)))
        skill.owner = owner

        new_rank = process_rank(skill)

        self.assertEqual(new_rank, 50)
        self.assertEqual(owner.db.tdp, 600)
        self.assertEqual(owner.db.tdp_pool, 50)

    def test_tdp_command_hides_pool_for_players(self):
        caller = _DummyCaller(tdp=612, tdp_pool=87)

        CmdTDP.func(_DummyCommand(caller))

        self.assertEqual(caller.messages, ["Time Development Points: 612"])

    def test_tdp_command_shows_pool_for_developers(self):
        caller = _DummyCaller(permissions={"Developer"}, tdp=612, tdp_pool=87)

        CmdTDP.func(_DummyCommand(caller))

        self.assertEqual(caller.messages, ["Time Development Points: 612\nTDP Pool Progress: 87/200"])

    def test_experience_command_appends_tdp_total(self):
        caller = _DummyCaller(
            tdp=618,
            skills={
                "alchemy": _DummySkill(rank=12, rank_progress=50.0, mindstate=10, pool=30.0, max_pool=90.0),
            },
        )

        CmdExperience.func(_DummyCommand(caller))

        self.assertEqual(len(caller.messages), 1)
        self.assertIn("Time Development Points: 618", caller.messages[0])
        self.assertIn("Total Ranks Displayed: 12", caller.messages[0])


if __name__ == "__main__":
    unittest.main()