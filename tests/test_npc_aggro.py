import types
import unittest

from commands.cmd_debug import CmdDebug
from engine.services.state_service import StateService
from typeclasses.npcs import NPC


class FakeRoom:
    def __init__(self):
        self.messages = []

    def msg_contents(self, message):
        self.messages.append(message)


class FakeActor:
    def __init__(self, key, room, *, has_account=True, alive=True, actor_id=0):
        self.key = key
        self.location = room
        self.has_account = has_account
        self._alive = alive
        self.id = actor_id
        self.messages = []

    def is_alive(self):
        return self._alive

    def msg(self, message):
        self.messages.append(message)

    def get_profession_reaction_message(self, context="presence", observer=None):
        return None


class FakeCaller:
    def __init__(self, room):
        self.location = room
        self.messages = []

    def msg(self, message):
        self.messages.append(message)

    def resolve_numbered_candidate(self, target_name, candidates, default_first=True):
        normalized = str(target_name or "").strip().lower()
        for candidate in candidates:
            if str(getattr(candidate, "key", "") or "").lower() == normalized:
                return candidate, [], normalized, None
        return None, [], normalized, None

    def msg_numbered_matches(self, base_query, matches):
        self.messages.append(f"matches:{base_query}:{len(matches)}")


class FakeNPC:
    ASSIST_SAME_ROOM_ONLY = True

    def __init__(self, room, *, key="training goblin", assist=False, npc_id=100):
        self.key = key
        self.id = npc_id
        self.location = room
        self.ndb = types.SimpleNamespace(threat_table={})
        self.db = types.SimpleNamespace(
            aggressive=True,
            assist=assist,
            assist_source=None,
            target=None,
            in_combat=False,
            hp=10,
            is_npc=True,
            last_seen_target=None,
        )
        self.state = {}
        self.attacker_events = []

    def is_dead(self):
        return False

    def is_alive(self):
        return True

    def get_target(self):
        target = getattr(self.db, "target", None)
        if target is None:
            return None
        if getattr(target, "location", None) != self.location:
            return None
        return target

    def set_target(self, target):
        self.db.target = target
        self.db.in_combat = target is not None
        self.db.last_seen_target = getattr(target, "id", None) if target is not None else None
        if target is None:
            self.clear_state("last_seen_target")
        elif getattr(target, "id", None):
            self.set_state("last_seen_target", target.id)

    def clear_target(self):
        self.set_target(None)

    def set_hp(self, value):
        self.db.hp = value

    def set_state(self, key, value):
        self.state[key] = value

    def get_state(self, key):
        return self.state.get(key)

    def clear_state(self, key):
        self.state.pop(key, None)

    def _get_threat_table(self):
        return NPC._get_threat_table(self)

    def _resolve_threat_target(self, target_id):
        return NPC._resolve_threat_target(self, target_id)

    def get_threat(self, target):
        return NPC.get_threat(self, target)

    def add_threat(self, target, amount):
        return NPC.add_threat(self, target, amount)

    def clear_threat(self):
        return NPC.clear_threat(self)

    def remove_target(self, target):
        return NPC.remove_target(self, target)

    def prune_threat_table(self):
        return NPC.prune_threat_table(self)

    def get_highest_threat(self):
        return NPC.get_highest_threat(self)

    def get_range(self, target):
        if target is None:
            return "not-engaged"
        return "melee" if getattr(target, "location", None) == self.location else "far"

    def is_combat_loop_active(self):
        return NPC.is_combat_loop_active(self)

    def should_auto_engage_actor(self, actor):
        return NPC.should_auto_engage_actor(self, actor)

    def maybe_auto_engage_actor(self, actor):
        return NPC.maybe_auto_engage_actor(self, actor)

    def can_assist(self):
        return NPC.can_assist(self)

    def emit_assist_event(self, target):
        return NPC.emit_assist_event(self, target)

    def receive_assist_event(self, source, target):
        return NPC.receive_assist_event(self, source, target)

    def at_attacked(self, attacker):
        self.attacker_events.append(attacker)
        NPC.at_attacked(self, attacker)


class NPCAggroTests(unittest.TestCase):
    def test_react_to_presence_engages_aggressive_player(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor = FakeActor("player123", room, actor_id=42)
        room.contents = [npc, actor]

        result = NPC.react_to(npc, actor, context="presence")

        self.assertIsNone(result)
        self.assertIs(npc.db.target, actor)
        self.assertTrue(npc.db.in_combat)
        self.assertEqual(npc.get_state("last_seen_target"), 42)
        self.assertEqual(room.messages, ["training goblin snarls and attacks player123!"])

    def test_react_to_presence_does_not_repeat_message_when_target_already_set(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor = FakeActor("player123", room, actor_id=42)
        room.contents = [npc, actor]

        NPC.react_to(npc, actor, context="presence")
        NPC.react_to(npc, actor, context="presence")

        self.assertEqual(room.messages, ["training goblin snarls and attacks player123!"])

    def test_apply_damage_notifies_target_about_attacker(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        attacker = FakeActor("player123", room, actor_id=7)
        room.contents = [npc, attacker]

        result = StateService.apply_damage(npc, 3, attacker=attacker)

        self.assertEqual(result.data["amount"], 3)
        self.assertEqual(npc.db.hp, 7)
        self.assertEqual(npc.attacker_events, [attacker])
        self.assertIs(npc.db.target, attacker)
        self.assertEqual(room.messages, ["training goblin turns on player123!"])

    def test_disengage_clears_target_and_emits_message(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor = FakeActor("player123", room, actor_id=9)
        npc.set_target(actor)
        npc.set_state("combat_timer", 5)

        NPC.disengage(npc)

        self.assertIsNone(npc.db.target)
        self.assertFalse(npc.db.in_combat)
        self.assertIsNone(npc.get_state("combat_timer"))
        self.assertEqual(room.messages, ["training goblin loses interest."])

    def test_debug_npc_reports_target_distance_and_last_seen_name(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor = FakeActor("player123", room, actor_id=42)
        room.contents = [npc, actor]
        npc.set_target(actor)
        caller = FakeCaller(room)

        command = CmdDebug()
        command.caller = caller
        command.args = "npc training goblin"

        command.func()

        self.assertEqual(len(caller.messages), 1)
        self.assertIn("--- NPC DEBUG: training goblin ---", caller.messages[0])
        self.assertIn("Typeclass: FakeNPC", caller.messages[0])
        self.assertIn("Target: player123", caller.messages[0])
        self.assertIn("Same room: True", caller.messages[0])
        self.assertIn("Distance: melee", caller.messages[0])
        self.assertIn("In combat: True", caller.messages[0])
        self.assertIn("Aggressive: True", caller.messages[0])
        self.assertIn("Assist enabled: False", caller.messages[0])
        self.assertIn("Assisting: None", caller.messages[0])
        self.assertIn("Top Threat: None", caller.messages[0])
        self.assertIn("Last seen: player123", caller.messages[0])
        self.assertIn("Threat Table: empty", caller.messages[0])

    def test_at_attacked_emits_same_room_assist_event_for_assist_npcs(self):
        room = FakeRoom()
        source_guard = FakeNPC(room, key="guard one", assist=True, npc_id=1)
        assisting_guard = FakeNPC(room, key="guard two", assist=True, npc_id=2)
        merchant = FakeNPC(room, key="merchant", assist=False, npc_id=3)
        attacker = FakeActor("player123", room, actor_id=42)
        room.contents = [source_guard, assisting_guard, merchant, attacker]

        NPC.at_attacked(source_guard, attacker)

        self.assertIs(source_guard.db.target, attacker)
        self.assertIs(assisting_guard.db.target, attacker)
        self.assertIsNone(merchant.db.target)
        self.assertEqual(assisting_guard.db.assist_source, 1)
        self.assertEqual(assisting_guard.get_threat(attacker), 5)
        self.assertEqual(room.messages, ["guard one turns on player123!", "guard two rushes to assist!"])

    def test_receive_assist_event_does_not_retarget_already_engaged_npc(self):
        room = FakeRoom()
        source_guard = FakeNPC(room, key="guard one", assist=True, npc_id=1)
        assisting_guard = FakeNPC(room, key="guard two", assist=True, npc_id=2)
        attacker = FakeActor("player123", room, actor_id=42)
        existing_target = FakeActor("player999", room, actor_id=84)
        room.contents = [source_guard, assisting_guard, attacker, existing_target]
        assisting_guard.set_target(existing_target)

        result = NPC.receive_assist_event(assisting_guard, source_guard, attacker)

        self.assertFalse(result)
        self.assertIs(assisting_guard.db.target, existing_target)
        self.assertEqual(room.messages, [])

    def test_apply_damage_adds_threat_for_attacker(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        attacker = FakeActor("player123", room, actor_id=7)
        room.contents = [npc, attacker]

        StateService.apply_damage(npc, 3, attacker=attacker)

        self.assertEqual(npc.get_threat(attacker), 10)

    def test_get_highest_threat_prefers_larger_threat_value(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor1 = FakeActor("player1", room, actor_id=1)
        actor2 = FakeActor("player2", room, actor_id=2)
        room.contents = [npc, actor1, actor2]
        npc.add_threat(actor1, 10)
        npc.add_threat(actor2, 30)

        best = npc.get_highest_threat()

        self.assertIs(best, actor2)

    def test_prune_threat_table_removes_targets_not_in_room(self):
        room = FakeRoom()
        other_room = FakeRoom()
        npc = FakeNPC(room)
        actor1 = FakeActor("player1", room, actor_id=1)
        actor2 = FakeActor("player2", other_room, actor_id=2)
        room.contents = [npc, actor1]
        npc.add_threat(actor1, 10)
        npc.add_threat(actor2, 30)

        pruned = npc.prune_threat_table()

        self.assertEqual(pruned, {"1": 10})

    def test_debug_npc_reports_top_threat_and_table_entries(self):
        room = FakeRoom()
        npc = FakeNPC(room)
        actor1 = FakeActor("player1", room, actor_id=1)
        actor2 = FakeActor("player2", room, actor_id=2)
        room.contents = [npc, actor1, actor2]
        npc.add_threat(actor1, 10)
        npc.add_threat(actor2, 30)
        caller = FakeCaller(room)

        command = CmdDebug()
        command.caller = caller
        command.args = "npc training goblin"

        command.func()

        self.assertIn("Top Threat: player2", caller.messages[0])
        self.assertIn("Threat Table:", caller.messages[0])
        self.assertIn("player2: 30", caller.messages[0])
        self.assertIn("player1: 10", caller.messages[0])


if __name__ == "__main__":
    unittest.main()