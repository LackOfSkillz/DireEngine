import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_disengage import CmdDisengage
from commands.cmd_target import CmdTarget


class DummyRoom:
    def __init__(self):
        self.messages = []
        self.contents = []

    def msg_contents(self, message, exclude=None):
        self.messages.append({"message": message, "exclude": exclude})


class DummyTarget:
    def __init__(self, key="goblin", room=None):
        self.key = key
        self.messages = []
        self.location = room
        self.db = SimpleNamespace(target=None)

    def msg(self, text):
        self.messages.append(text)

    def set_target(self, target):
        self.db.target = target


class DummyCaller:
    def __init__(self, room=None, target=None):
        self.key = "Jekar"
        self.location = room or DummyRoom()
        self.db = SimpleNamespace(in_combat=True, target=target, target_body_part=None)
        self.messages = []
        self._matches = []
        self.break_calls = []
        self.roundtime = None

    def msg(self, text):
        self.messages.append(text)

    def is_stunned(self):
        return False

    def consume_stun(self):
        return None

    def is_in_roundtime(self):
        return False

    def msg_roundtime_block(self):
        self.messages.append("RT")

    def set_target(self, target):
        self.db.target = target

    def set_roundtime(self, value):
        self.roundtime = value

    def break_combat_rhythm(self, show_message=False):
        self.break_calls.append(show_message)

    def search(self, _query):
        return None


class MessagingCommandTests(unittest.TestCase):
    def test_target_person_notifies_actor_target_and_room(self):
        room = DummyRoom()
        target = DummyTarget(room=room)
        caller = DummyCaller(room=room)
        room.contents = [caller, target]
        command = CmdTarget()
        command.caller = caller
        command.args = "goblin"
        command.resolve_target = lambda *_args, **_kwargs: (target, [], "goblin", None, "characters")
        command.msg_target_matches = lambda *_args, **_kwargs: None

        command.func()

        self.assertEqual(caller.messages, ["You focus on goblin."])
        self.assertEqual(target.messages, ["Jekar focuses on you."])
        self.assertEqual(room.messages, [{"message": "Jekar fixes attention on goblin.", "exclude": [caller, target]}])

    def test_target_body_part_notifies_actor_and_room(self):
        room = DummyRoom()
        caller = DummyCaller(room=room)
        command = CmdTarget()
        command.caller = caller
        command.args = "head"

        command.func()

        self.assertEqual(caller.db.target_body_part, "head")
        self.assertEqual(caller.messages, ["You focus your attacks on the head."])
        self.assertEqual(room.messages, [{"message": "Jekar shifts into a more precise stance.", "exclude": [caller]}])

    def test_disengage_notifies_actor_target_and_room(self):
        room = DummyRoom()
        target = DummyTarget(room=room)
        caller = DummyCaller(room=room, target=target)
        target.db.target = caller
        command = CmdDisengage()
        command.caller = caller
        command.args = ""

        command.func()

        self.assertEqual(caller.messages, ["You step back and disengage."])
        self.assertEqual(target.messages, ["Jekar disengages from you."])
        self.assertEqual(room.messages, [{"message": "Jekar disengages from goblin.", "exclude": [caller, target]}])

    def test_disengage_without_target_uses_untargeted_room_line(self):
        room = DummyRoom()
        caller = DummyCaller(room=room, target=None)
        command = CmdDisengage()
        command.caller = caller
        command.args = ""

        caller.db.target = None
        caller.db.in_combat = True

        command.func()

        self.assertEqual(caller.messages, ["You step back and disengage."])
        self.assertEqual(room.messages, [{"message": "Jekar steps back from the fight.", "exclude": [caller]}])


if __name__ == "__main__":
    unittest.main()