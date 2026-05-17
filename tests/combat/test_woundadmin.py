import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_woundadmin import CmdWoundAdmin


class DummyCaller:
    def __init__(self, target=None, room=None):
        self._target = target
        self.location = room
        self.messages = []
        self.last_search = None

    def msg(self, text):
        self.messages.append(text)

    def search(self, query, global_search=False):
        self.last_search = {"query": query, "global_search": global_search}
        return self._target


class DummyTarget:
    def __init__(self, key="SmokeEmpathLive", room=None):
        self.key = key
        self.location = room
        self.messages = []
        self.sync_calls = 0
        self.bleed_updates = 0
        self.db = SimpleNamespace(
            injuries={
                "chest": {
                    "external": 0,
                    "internal": 0,
                    "bruise": 0,
                    "bleed": 0,
                    "scar": 0,
                    "tended": False,
                    "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0},
                    "max": 100,
                    "vital": True,
                },
                "head": {
                    "external": 3,
                    "internal": 2,
                    "bruise": 0,
                    "bleed": 1,
                    "scar": 0,
                    "tended": False,
                    "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0},
                    "max": 100,
                    "vital": True,
                },
            },
            wounds={"fatigue": 0, "vitality": 0, "bleeding": 0, "poison": 0, "disease": 0},
        )

    def msg(self, text):
        self.messages.append(text)

    def ensure_core_defaults(self):
        return None

    def normalize_body_part_name(self, part):
        return str(part or "").strip().lower().replace("-", "_")

    def format_body_part_name(self, part, title=False):
        text = self.normalize_body_part_name(part).replace("_", " ")
        return text.title() if title else text

    def get_body_part(self, part):
        return self.db.injuries.get(self.normalize_body_part_name(part))

    def set_empath_wound(self, wound_type, value):
        self.db.wounds[wound_type] = int(value)
        return self.db.wounds[wound_type]

    def update_bleed_state(self):
        self.bleed_updates += 1

    def sync_client_state(self):
        self.sync_calls += 1


class WoundAdminCommandTests(unittest.TestCase):
    def test_wound_requires_full_arguments(self):
        caller = DummyCaller()
        command = CmdWoundAdmin()
        command.caller = caller
        command.args = "SmokeEmpathLive chest 10"

        command.func()

        self.assertEqual(caller.messages, ["Usage: @wound <target> <part> <external> <internal> <bleed>"])

    def test_wound_uses_global_search_and_applies_part_and_summary(self):
        room = SimpleNamespace(messages=[], msg_contents=lambda message, exclude=None: room.messages.append({"message": message, "exclude": exclude}))
        target = DummyTarget(room=room)
        caller = DummyCaller(target=target, room=room)
        command = CmdWoundAdmin()
        command.caller = caller
        command.args = "SmokeEmpathLive chest 10 4 2"

        command.func()

        self.assertEqual(caller.last_search, {"query": "SmokeEmpathLive", "global_search": True})
        self.assertEqual(target.db.injuries["chest"]["external"], 10)
        self.assertEqual(target.db.injuries["chest"]["internal"], 4)
        self.assertEqual(target.db.injuries["chest"]["bleed"], 2)
        self.assertFalse(target.db.injuries["chest"]["tended"])
        self.assertEqual(target.db.wounds["vitality"], 19)
        self.assertEqual(target.db.wounds["bleeding"], 3)
        self.assertEqual(target.bleed_updates, 1)
        self.assertEqual(target.sync_calls, 1)
        self.assertEqual(caller.messages, ["You set SmokeEmpathLive's Chest wounds to external 10, internal 4, bleed 2 (summary vitality 19, bleeding 3)."])
        self.assertEqual(target.messages, ["A testing force sets your chest wounds to external 10, internal 4, bleed 2."])
        self.assertEqual(room.messages, [{"message": "SmokeEmpathLive suddenly winces as a test wound profile settles in.", "exclude": [caller, target]}])

    def test_wound_rejects_invalid_body_part(self):
        target = DummyTarget()
        caller = DummyCaller(target=target)
        command = CmdWoundAdmin()
        command.caller = caller
        command.args = "SmokeEmpathLive tail 10 0 0"

        command.func()

        self.assertEqual(caller.messages, ["Tail is not a valid wound location on SmokeEmpathLive."])


if __name__ == "__main__":
    unittest.main()