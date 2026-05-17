import unittest
from types import SimpleNamespace

from engine.services.roar_service import RoarService


class _Room:
    def __init__(self):
        self.contents = []


class _Actor:
    def __init__(self, key, room, *, group_id=None, has_account=True, dead=False):
        self.id = id(self)
        self.key = key
        self.location = room
        self.account = object() if has_account else None
        self.db = SimpleNamespace(group_id=group_id, states={})
        self.ndb = SimpleNamespace()
        self._dead = dead
        room.contents.append(self)

    def is_dead(self):
        return self._dead

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states


class _Npc:
    def __init__(self, key, room, *, allied=False):
        self.id = id(self)
        self.key = key
        self.location = room
        self.account = None
        self.db = SimpleNamespace(states={}, is_npc=True)
        room.contents.append(self)
        if allied:
            self.set_state("effect_360001", {"expires_at": RoarService.now() + 30})

    def is_dead(self):
        return False

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states


class _InspirationDefinition:
    category = "inspiration"


class _IntimidationDefinition:
    category = "intimidation"


class RoarInspirationSubstrateTests(unittest.TestCase):
    def test_get_ally_targets_prefers_group_marker_and_keeps_flagged_npc(self):
        room = _Room()
        caller = _Actor("Caller", room, group_id="alpha")
        grouped = _Actor("Grouped", room, group_id="alpha")
        _other_group = _Actor("Other", room, group_id="beta")
        _dead_grouped = _Actor("Dead", room, group_id="alpha", dead=True)
        npc = _Npc("Companion", room, allied=True)

        recipients = RoarService._get_ally_targets(caller)

        self.assertEqual([obj.key for obj in recipients], ["Caller", "Grouped", "Companion"])

    def test_resolve_recipients_routes_by_roar_category(self):
        room = _Room()
        caller = _Actor("Caller", room)
        ally = _Actor("Ally", room)
        enemy = _Npc("Enemy", room, allied=False)
        caller.get_target = lambda: enemy

        inspiration_recipients = RoarService._resolve_recipients(caller, _InspirationDefinition())
        intimidation_recipients = RoarService._resolve_recipients(caller, _IntimidationDefinition())

        self.assertEqual([obj.key for obj in inspiration_recipients], ["Caller", "Ally"])
        self.assertEqual([obj.key for obj in intimidation_recipients], ["Enemy"])


if __name__ == "__main__":
    unittest.main()