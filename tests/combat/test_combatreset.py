import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.command import DEAD_STATE_ALLOWED_COMMANDS
from commands.cmd_combatreset import CmdCombatReset
from typeclasses.characters import Character, DEAD_STATE_ALLOWED_COMMANDS as CHARACTER_DEAD_STATE_ALLOWED_COMMANDS


class DummyCaller:
    def __init__(self, target=None, room=None):
        self._target = target
        self.messages = []
        self.last_search = None
        self.location = room

    def msg(self, text):
        self.messages.append(text)

    def search(self, query, global_search=False):
        self.last_search = {"query": query, "global_search": global_search}
        return self._target


class DummyTarget:
    def __init__(self, key="AedanSmoke", room=None):
        self.key = key
        self.messages = []
        self.reset_calls = 0
        self.location = room

    def combat_reset_state(self):
        self.reset_calls += 1

    def msg(self, text):
        self.messages.append(text)


class CombatResetCommandTests(unittest.TestCase):
    def test_combatreset_is_allowed_while_dead(self):
        self.assertIn("combatreset", DEAD_STATE_ALLOWED_COMMANDS)
        self.assertIn("cmbreset", DEAD_STATE_ALLOWED_COMMANDS)
        self.assertIn("combatreset", CHARACTER_DEAD_STATE_ALLOWED_COMMANDS)
        self.assertIn("cmbreset", CHARACTER_DEAD_STATE_ALLOWED_COMMANDS)

    def test_sync_state_to_client_wraps_full_structured_sync(self):
        character = SimpleNamespace(sync_client_state=MagicMock())

        Character.sync_state_to_client(character)

        character.sync_client_state.assert_called_once_with(
            include_map=True,
            include_subsystem=True,
            include_character=True,
            session=None,
        )

    def test_combat_reset_state_calls_sync_state_to_client(self):
        ndb = SimpleNamespace()
        character = SimpleNamespace(
            db=SimpleNamespace(
                max_hp=100,
                max_balance=100,
                wounds={"vitality": 25},
                death_type="vitality",
                death_timestamp=123.0,
                death_location=456,
                last_death_time=789.0,
                recovery_state="revived_weak",
                depart_confirm_mode="standard",
                depart_confirm_expires_at=999.0,
                last_critical_warning_at=5.0,
                stabilized_until=6.0,
                resurrection_vitality_cap_ratio=0.5,
                res_stabilization={"ticks_remaining": 2},
                just_revived=True,
                revive_protection_ticks=3,
                soul_state={"strength": 50},
            ),
            ndb=ndb,
            ensure_core_defaults=MagicMock(),
            renew_state=MagicMock(),
            clear_state=MagicMock(),
            clear_death_corpse_link=MagicMock(),
            set_target=MagicMock(),
            sync_resources_from_empath_wounds=MagicMock(),
            set_hp=MagicMock(),
            set_balance=MagicMock(),
            set_fatigue=MagicMock(),
            set_roundtime=MagicMock(),
            sync_state_to_client=MagicMock(),
        )

        Character.combat_reset_state(character)

        self.assertEqual(
            character.db.wounds,
            {"fatigue": 0, "vitality": 0, "bleeding": 0, "poison": 0, "disease": 0},
        )
        self.assertIsNone(character.db.death_type)
        self.assertEqual(character.db.death_timestamp, 0.0)
        self.assertEqual(character.db.last_death_time, 0.0)
        self.assertEqual(character.db.recovery_state, "none")
        self.assertIsNone(character.db.depart_confirm_mode)
        self.assertEqual(character.db.depart_confirm_expires_at, 0.0)
        self.assertEqual(character.db.stabilized_until, 0.0)
        self.assertEqual(character.db.resurrection_vitality_cap_ratio, 1.0)
        self.assertIsNone(character.db.res_stabilization)
        self.assertFalse(character.db.just_revived)
        self.assertEqual(character.db.revive_protection_ticks, 0)
        self.assertIsNone(character.db.soul_state)
        self.assertIsNone(getattr(character.ndb, "combat_target", None))
        self.assertIsNone(getattr(character.ndb, "queued_action", None))
        self.assertIsNone(getattr(character.ndb, "pending_revive_action", None))
        self.assertIsNone(getattr(character.ndb, "pending_cleric_ritual_action", None))
        character.set_target.assert_called_once_with(None)
        character.set_hp.assert_called_once_with(100)
        character.set_balance.assert_called_once_with(100)
        character.set_fatigue.assert_called_once_with(0)
        character.set_roundtime.assert_called_once_with(0)
        character.sync_state_to_client.assert_called_once_with()

    def test_combatreset_requires_target_name(self):
        caller = DummyCaller()
        command = CmdCombatReset()
        command.caller = caller
        command.args = ""

        command.func()

        self.assertEqual(caller.messages, ["Combat reset whom?"])

    def test_combatreset_uses_global_search_and_resets_target(self):
        room = SimpleNamespace(messages=[], msg_contents=lambda message, exclude=None: room.messages.append({"message": message, "exclude": exclude}))
        target = DummyTarget(room=room)
        caller = DummyCaller(target=target, room=room)
        command = CmdCombatReset()
        command.caller = caller
        command.args = "AedanSmoke"

        command.func()

        self.assertEqual(caller.last_search, {"query": "AedanSmoke", "global_search": True})
        self.assertEqual(target.reset_calls, 1)
        self.assertEqual(caller.messages, ["You reset AedanSmoke's combat state."])
        self.assertEqual(target.messages, ["A restoring force clears your combat state and lingering wounds."])
        self.assertEqual(room.messages, [{"message": "AedanSmoke suddenly looks refreshed and at ease.", "exclude": [caller, target]}])

    def test_combatreset_rejects_nonresettable_target(self):
        caller = DummyCaller(target=SimpleNamespace(key="rock"))
        command = CmdCombatReset()
        command.caller = caller
        command.args = "rock"

        command.func()

        self.assertEqual(caller.messages, ["You cannot combat reset rock."])


if __name__ == "__main__":
    unittest.main()
