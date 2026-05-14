import unittest

from engine.services.messaging import send_action_messages, send_untargeted_action


class DummyRoom:
    def __init__(self):
        self.calls = []

    def msg_contents(self, message, exclude=None):
        self.calls.append({"message": message, "exclude": exclude})


class DummyActor:
    def __init__(self, room=None):
        self.location = room
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


class SendActionMessagesTests(unittest.TestCase):
    def test_actor_target_and_room_each_receive_their_own_message(self):
        room = DummyRoom()
        actor = DummyActor(room=room)
        target = DummyActor(room=room)

        send_action_messages(
            actor=actor,
            target=target,
            actor_message="actor",
            target_message="target",
            room_message="room",
        )

        self.assertEqual(actor.messages, ["actor"])
        self.assertEqual(target.messages, ["target"])
        self.assertEqual(room.calls, [{"message": "room", "exclude": [actor, target]}])

    def test_target_falls_back_to_room_message_when_target_message_missing(self):
        room = DummyRoom()
        actor = DummyActor(room=room)
        target = DummyActor(room=room)

        send_action_messages(actor=actor, target=target, room_message="room")

        self.assertEqual(target.messages, ["room"])
        self.assertEqual(room.calls, [{"message": "room", "exclude": [actor, target]}])

    def test_untargeted_action_sends_actor_and_room_only(self):
        room = DummyRoom()
        actor = DummyActor(room=room)

        send_untargeted_action(actor=actor, actor_message="actor", room_message="room")

        self.assertEqual(actor.messages, ["actor"])
        self.assertEqual(room.calls, [{"message": "room", "exclude": [actor]}])

    def test_room_message_can_include_actor_when_requested(self):
        room = DummyRoom()
        actor = DummyActor(room=room)
        target = DummyActor(room=room)

        send_action_messages(
            actor=actor,
            target=target,
            room_message="room",
            room_exclude_actor=False,
        )

        self.assertEqual(room.calls, [{"message": "room", "exclude": [target]}])

    def test_room_message_can_include_target_when_requested(self):
        room = DummyRoom()
        actor = DummyActor(room=room)
        target = DummyActor(room=room)

        send_action_messages(
            actor=actor,
            target=target,
            room_message="room",
            room_exclude_target=False,
        )

        self.assertEqual(room.calls, [{"message": "room", "exclude": [actor]}])

    def test_no_room_message_skips_broadcast(self):
        room = DummyRoom()
        actor = DummyActor(room=room)
        target = DummyActor(room=room)

        send_action_messages(actor=actor, target=target, actor_message="actor", target_message="target")

        self.assertEqual(actor.messages, ["actor"])
        self.assertEqual(target.messages, ["target"])
        self.assertEqual(room.calls, [])

    def test_explicit_room_parameter_overrides_actor_location(self):
        actor_room = DummyRoom()
        other_room = DummyRoom()
        actor = DummyActor(room=actor_room)

        send_action_messages(actor=actor, room=other_room, room_message="room")

        self.assertEqual(actor_room.calls, [])
        self.assertEqual(other_room.calls, [{"message": "room", "exclude": [actor]}])


if __name__ == "__main__":
    unittest.main()