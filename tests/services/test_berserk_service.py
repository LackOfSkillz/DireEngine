import unittest
from types import SimpleNamespace

from engine.services.circle_service import collect_circle_advancement_private_messages
from engine.services.berserk_service import BerserkService


class _Room:
    def __init__(self, room_id=1, *, silenced=False, safehaven=False):
        self.id = room_id
        self.db = SimpleNamespace(silenced=silenced, safehaven=safehaven)
        self.contents = []
        self.tags = SimpleNamespace(has=lambda _name: False)


class _Target:
    def __init__(self, room, *, key="goblin", target=None):
        self.id = 9
        self.key = key
        self.location = room
        self.db = SimpleNamespace(is_npc=True, hp=100)
        self._target = target
        room.contents.append(self)

    def is_alive(self):
        return True

    def get_target(self):
        return self._target


class _Actor:
    def __init__(self, *, circle=2, saf=10, room=None, profession="barbarian", stats=None):
        self.key = "Barbarian"
        self.id = 1
        self.location = room or _Room()
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            canonical_saf=saf,
            states={},
            hp=50,
            max_hp=100,
            max_fatigue=100,
            fatigue=10,
            position="prone",
            invisible=False,
            nonexist=False,
            unconscious=False,
            gmmode=False,
            is_npc=False,
            mm=1,
        )
        self._stats = dict(stats or {"strength": 30, "reflex": 20, "discipline": 15, "stamina": 20, "charisma": 10, "agility": 30})
        self._target = None
        self._hidden = False
        self.db.barbarian_abilities = []
        self.messages = []

    def is_profession(self, profession):
        return self.db.profession == str(profession)

    def get_circle(self):
        return self.db.circle

    def get_stat(self, name):
        return int(self._stats.get(str(name or "").strip().lower(), 0) or 0)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def clear_state(self, key):
        states = dict(self.db.states or {})
        states.pop(key, None)
        self.db.states = states

    def get_target(self):
        return self._target

    def set_target(self, target):
        self._target = target

    def get_range(self, target):
        return "melee" if target == self._target else "missile"

    def is_dead(self):
        return False

    def is_stunned(self):
        return bool(getattr(self.db, "stunned", False))

    def is_hidden(self):
        return self._hidden

    def break_stealth(self):
        self._hidden = False

    def set_fatigue(self, value):
        self.db.fatigue = int(value)


class BerserkServiceTests(unittest.TestCase):
    def test_circle_two_auto_learns_berserk(self):
        actor = _Actor(circle=2)

        self.assertTrue(BerserkService.ensure_berserk_learned(actor))
        self.assertIn("berserk", actor.db.barbarian_abilities)

    def test_circle_service_emits_berserk_autolearn_message_once(self):
        actor = _Actor(circle=2)
        actor.db.profession = "barbarian"

        first = collect_circle_advancement_private_messages(actor, 1, 2)
        second = collect_circle_advancement_private_messages(actor, 1, 2)

        self.assertTrue(any("now BERSERK" in line for line in first))
        self.assertEqual(second, [])

    def test_preflight_rejects_off_class(self):
        actor = _Actor(profession="cleric")

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertIn("You do not have the facilities to properly channel your rage.", result.errors)

    def test_preflight_rejects_silenced_room(self):
        actor = _Actor(room=_Room(silenced=True))

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertEqual(result.errors[0], "You can't do that here.")

    def test_preflight_rejects_safehaven_room(self):
        actor = _Actor(room=_Room(safehaven=True))

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertIn("overwhelming desire for tranquility", result.errors[0])

    def test_preflight_rejects_invisible_corruption(self):
        actor = _Actor()
        actor.db.invisible = True

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertIn("magical corruption", result.errors[0])

    def test_preflight_rejects_bloodthirst_and_dance_and_active_berserk(self):
        actor = _Actor()
        actor.set_state("effect_8932001", {"duration": 10})
        self.assertIn("true bloodthirst", BerserkService.can_berserk(actor).errors[0])
        actor.clear_state("effect_8932001")
        actor.set_state("effect_3387100", {"duration": 10})
        self.assertIn("focused on a Dance", BerserkService.can_berserk(actor).errors[0])
        actor.clear_state("effect_3387100")
        actor.set_state("effect_1740001", {"duration": 10})
        self.assertIn("already berserking", BerserkService.can_berserk(actor).errors[0])

    def test_preflight_rejects_droughtmans_maze(self):
        actor = _Actor(room=_Room(room_id=1051001))

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertEqual(result.errors[0], "Something prevents you from doing that.")

    def test_preflight_rejects_missing_melee_critter(self):
        actor = _Actor()

        result = BerserkService.can_berserk(actor)

        self.assertFalse(result.success)
        self.assertIn("Without a foe to savage", result.errors[0])

    def test_strength_tier_boundaries_are_canonical(self):
        actor = _Actor()
        target = _Target(actor.location, target=actor)
        actor.set_target(target)
        BerserkService.ensure_berserk_learned(actor)

        actor.db.canonical_saf = 25
        self.assertEqual(BerserkService.can_berserk(actor).data["strength_percent"], 75)
        actor.db.canonical_saf = 26
        self.assertEqual(BerserkService.can_berserk(actor).data["strength_percent"], 74)
        actor.db.canonical_saf = 50
        self.assertEqual(BerserkService.can_berserk(actor).data["strength_percent"], 50)
        actor.db.canonical_saf = 51
        self.assertEqual(BerserkService.can_berserk(actor).data["strength_percent"], 49)
        actor.db.canonical_saf = 75
        self.assertEqual(BerserkService.can_berserk(actor).data["strength_percent"], 25)
        actor.db.canonical_saf = 76
        self.assertFalse(BerserkService.can_berserk(actor).success)

    def test_success_applies_hp_mm_duration_fatigue_and_reveal(self):
        actor = _Actor(saf=10)
        target = _Target(actor.location, target=actor)
        actor.set_target(target)
        actor._hidden = True
        BerserkService.ensure_berserk_learned(actor)

        result = BerserkService.berserk(actor, randomizer=lambda low, high: { (80,120): 100, (90,110): 100, (70,130): 100 }[(low, high)])

        self.assertTrue(result.success)
        self.assertGreater(result.data["hp_bonus"], 0)
        self.assertGreater(result.data["mm_bonus"], 0)
        self.assertGreaterEqual(result.data["duration"], 20)
        self.assertEqual(actor.db.fatigue, actor.db.max_fatigue)
        self.assertEqual(actor.db.position, "standing")
        self.assertFalse(actor._hidden)
        self.assertIsNotNone(actor.get_state("effect_1740001"))

    def test_stun_break_clears_stun_when_stats_allow(self):
        actor = _Actor(saf=10, stats={"strength": 20, "reflex": 20, "discipline": 20, "stamina": 20, "charisma": 5, "agility": 20})
        target = _Target(actor.location, target=actor)
        actor.set_target(target)
        actor.db.stunned = True
        BerserkService.ensure_berserk_learned(actor)

        result = BerserkService.berserk(actor, randomizer=lambda _low, _high: 100)

        self.assertTrue(result.success)
        self.assertTrue(result.data["broke_stun"])
        self.assertFalse(actor.db.stunned)


if __name__ == "__main__":
    unittest.main()