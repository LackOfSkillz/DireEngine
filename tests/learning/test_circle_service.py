import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from engine.services.circle_service import (
    calculate_circle_tdp_grant,
    commit_advancement,
    find_guild_leader_for_profession,
    get_placeholder_circle_requirements,
    project_advancement,
)
from typeclasses.npcs import GuildLeaderNPC
from typeclasses.rooms import Room


class _CircleCharacter:
    def __init__(self, room=None, *, profession="empath", circle=2, coins=1000, exp_skill_state=None):
        self.location = room
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            coins=coins,
            exp_skill_state=dict(exp_skill_state or {}),
            spellbook={"known_spells": {}},
            magic_slot_pool=None,
        )
        self.grants = []
        self.syncs = 0

    def grant_tdp(self, amount, reason=""):
        self.grants.append((int(amount or 0), str(reason or "")))
        return int(amount or 0)

    def sync_client_state(self):
        self.syncs += 1

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle

    def get_skill(self, _skill_name):
        return 100


class CircleServiceTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.room = self._create(Room, "Circle Test Room")
        self.leader = self._create(GuildLeaderNPC, "Leader Test", location=self.room, home=self.room)
        self.leader.db.leads_profession = "empath"

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def test_circle_tdp_grant_below_ten(self):
        self.assertEqual(calculate_circle_tdp_grant(5), 50)

    def test_circle_tdp_grant_at_ten(self):
        self.assertEqual(calculate_circle_tdp_grant(10), 110)

    def test_circle_tdp_grant_midrange(self):
        self.assertEqual(calculate_circle_tdp_grant(27), 127)

    def test_circle_tdp_grant_at_cap(self):
        self.assertEqual(calculate_circle_tdp_grant(150), 250)

    def test_circle_tdp_grant_above_cap(self):
        self.assertEqual(calculate_circle_tdp_grant(151), 0)

    def test_placeholder_requirements_scale_with_circle(self):
        requirements = get_placeholder_circle_requirements("empath", 4)
        self.assertEqual(requirements["skill_rank_total_required"], 200)
        self.assertEqual(requirements["money_coins_required"], 400)

    def test_cleric_requirements_use_primary_magic_and_theurgy(self):
        requirements = get_placeholder_circle_requirements("cleric", 4)
        self.assertEqual(requirements["skill_requirements"], {"primary_magic": 75, "theurgy": 75})
        self.assertEqual(requirements["money_coins_required"], 400)

    def test_find_guild_leader_for_profession(self):
        caller = _CircleCharacter(self.room)
        self.assertEqual(find_guild_leader_for_profession(caller, "empath"), self.leader)

    def test_project_advancement_reports_missing_requirements(self):
        caller = _CircleCharacter(self.room, exp_skill_state={"empathy": {"rank": 10}}, coins=50)
        projection = project_advancement(caller)
        self.assertFalse(projection["requirements_met"])
        self.assertTrue(projection["missing"])
        self.assertIn("shakes their head", projection["room_message"])

    def test_project_advancement_includes_tdp_preview(self):
        caller = _CircleCharacter(self.room, circle=9, exp_skill_state={"empathy": {"rank": 500}})
        projection = project_advancement(caller)
        self.assertEqual(projection["tdp_grant_preview"], 110)
        self.assertIn("appraises them in silence", projection["room_message"])

    def test_commit_fails_without_guild_leader(self):
        caller = _CircleCharacter(None)
        result = commit_advancement(caller)
        self.assertFalse(result.ok)
        self.assertIn("guild leader", result.message)
        self.assertIsNone(result.room_message)

    def test_commit_succeeds_when_requirements_met(self):
        caller = _CircleCharacter(
            self.room,
            circle=2,
            coins=1000,
            exp_skill_state={"empathy": {"rank": 200}},
        )
        result = commit_advancement(caller)
        self.assertTrue(result.ok)
        self.assertEqual(caller.db.circle, 3)
        self.assertEqual(caller.db.coins, 700)
        self.assertEqual(caller.grants[-1][0], 50)
        self.assertIn("has advanced in their guild", result.room_message)

    def test_circle_ten_warning_lists_unmemorized_apprentice_spells(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=9,
            coins=2000,
            exp_skill_state={"primary_magic": {"rank": 600}, "theurgy": {"rank": 600}},
        )

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertIn("You have reached the 10th circle.", result.message)
        self.assertIn("Burden", result.message)
        self.assertIn("Manifest Force", result.message)
        self.assertIn("Strange Arrow", result.message)

    def test_circle_ten_warning_suppressed_when_all_apprentice_spells_memorized(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=9,
            coins=2000,
            exp_skill_state={"primary_magic": {"rank": 600}, "theurgy": {"rank": 600}},
        )
        caller.db.spellbook["known_spells"] = {
            "bless": {"learned_via": "book", "circle_learned": 1},
            "burden": {"learned_via": "book", "circle_learned": 9},
            "holy_light": {"learned_via": "book", "circle_learned": 2},
            "manifest_force": {"learned_via": "scroll", "circle_learned": 9},
            "protection_from_evil": {"learned_via": "book", "circle_learned": 3},
            "strange_arrow": {"learned_via": "book", "circle_learned": 9},
        }

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertNotIn("apprentice access", result.message)

    def test_circle_eleven_expiration_lists_lost_spells(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=10,
            coins=3000,
            exp_skill_state={"primary_magic": {"rank": 700}, "theurgy": {"rank": 700}},
        )

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertIn("Your apprentice access has expired", result.message)
        self.assertIn("Bless", result.message)
        self.assertIn("Burden", result.message)
        self.assertIn("Holy Light", result.message)
        self.assertIn("Manifest Force", result.message)
        self.assertIn("Protection from Evil", result.message)
        self.assertIn("Strange Arrow", result.message)

    def test_circle_eleven_expiration_suppressed_when_all_apprentice_spells_memorized(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=10,
            coins=3000,
            exp_skill_state={"primary_magic": {"rank": 700}, "theurgy": {"rank": 700}},
        )
        caller.db.spellbook["known_spells"] = {
            "bless": {"learned_via": "book", "circle_learned": 1},
            "burden": {"learned_via": "book", "circle_learned": 9},
            "holy_light": {"learned_via": "book", "circle_learned": 2},
            "manifest_force": {"learned_via": "scroll", "circle_learned": 9},
            "protection_from_evil": {"learned_via": "book", "circle_learned": 3},
            "strange_arrow": {"learned_via": "book", "circle_learned": 9},
        }

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertNotIn("Your apprentice access has expired", result.message)

    def test_commit_recomputes_slot_pool_max(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=49,
            coins=6000,
            exp_skill_state={"primary_magic": {"rank": 2600}, "theurgy": {"rank": 2600}},
        )

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertEqual(caller.db.circle, 50)
        self.assertEqual(caller.db.magic_slot_pool["max"], 50)

    def test_cleric_projection_reports_skill_specific_missing_lines(self):
        self.leader.db.leads_profession = "cleric"
        caller = _CircleCharacter(
            self.room,
            profession="cleric",
            circle=4,
            coins=1000,
            exp_skill_state={"primary_magic": {"rank": 80}, "theurgy": {"rank": 50}},
        )

        projection = project_advancement(caller)

        self.assertFalse(projection["requirements_met"])
        self.assertIn("Primary Magic: 80/100", projection["missing"])
        self.assertIn("Theurgy: 50/100", projection["missing"])

    def test_commit_failure_for_missing_requirements_has_no_room_message(self):
        caller = _CircleCharacter(self.room, exp_skill_state={"empathy": {"rank": 10}}, coins=50)

        result = commit_advancement(caller)

        self.assertFalse(result.ok)
        self.assertIsNone(result.room_message)
