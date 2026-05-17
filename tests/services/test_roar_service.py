import unittest
from types import SimpleNamespace

from engine.services.roar_service import RoarService


class _Tags:
    def has(self, _name):
        return False


class _Room:
    def __init__(self, room_id=1, *, silenced=False, safehaven=False):
        self.id = room_id
        self.db = SimpleNamespace(silenced=silenced, safehaven=safehaven)
        self.tags = _Tags()
        self.contents = []


class _Target:
    def __init__(self, room, *, key="goblin"):
        self.id = 2
        self.key = key
        self.location = room
        self.db = SimpleNamespace(is_npc=True, stats={"discipline": 5, "reflex": 5, "agility": 5, "strength": 5, "stamina": 5}, mm=1, states={}, position="standing")
        self.roundtime = 0
        room.contents.append(self)

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def clear_state(self, key):
        states = dict(self.db.states or {})
        states.pop(key, None)
        self.db.states = states

    def set_roundtime(self, value):
        self.roundtime = float(value)

    def set_position_state(self, state):
        self.db.position_state = state


class _Actor:
    def __init__(self, *, profession="barbarian", circle=5, room=None, position="standing", invisible=False, nonexist=False):
        self.id = 1
        self.key = "Barbarian"
        self.location = room or _Room()
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            position=position,
            invisible=invisible,
            nonexist=nonexist,
            spellbook1=0,
            stats={"discipline": 30, "charisma": 20, "strength": 20, "reflex": 20, "agility": 20},
            states={},
        )
        self._target = None

    def is_profession(self, profession):
        return self.db.profession == str(profession)

    def get_circle(self):
        return self.db.circle

    def get_spellbook1(self):
        return self.db.spellbook1

    def set_spellbook1(self, value, emit_messages=True):
        self.db.spellbook1 = int(value)
        return self.db.spellbook1

    def get_stat(self, name):
        return int(self.db.stats.get(str(name or "").strip().lower(), 0) or 0)

    def get_state(self, key):
        return dict(self.db.states or {}).get(key)

    def set_state(self, key, value):
        states = dict(self.db.states or {})
        states[key] = value
        self.db.states = states

    def clear_state(self, key):
        states = dict(self.db.states or {})
        states.pop(key, None)
        self.db.states = states

    def get_target(self):
        return self._target

    def set_target(self, target):
        self._target = target


class RoarServiceTests(unittest.TestCase):
    def test_slot_formula_matches_canonical_checkpoints(self):
        self.assertEqual(RoarService.get_total_slots_for_circle(4), 0)
        self.assertEqual(RoarService.get_total_slots_for_circle(5), 1)
        self.assertEqual(RoarService.get_total_slots_for_circle(15), 2)
        self.assertEqual(RoarService.get_total_slots_for_circle(50), 5)

    def test_circle_five_auto_learns_kuniyo_when_no_roars_known(self):
        actor = _Actor(circle=5)

        learned = RoarService.ensure_kuniyo_auto_learned(actor)

        self.assertTrue(learned)
        self.assertTrue(RoarService.has_known_roar_bit(actor, 0))

    def test_auto_learn_does_not_override_existing_roars(self):
        actor = _Actor(circle=15)
        actor.db.spellbook1 = 2

        learned = RoarService.ensure_kuniyo_auto_learned(actor)

        self.assertFalse(learned)
        self.assertFalse(RoarService.has_known_roar_bit(actor, 0))

    def test_slot_enforcement_blocks_second_roar_at_one_slot(self):
        actor = _Actor(circle=5)
        RoarService.ensure_kuniyo_auto_learned(actor)

        result = RoarService.set_known_roar(actor, 1)

        self.assertFalse(result.success)
        self.assertIn("no free roar slots", result.errors[0])

    def test_off_class_rejected(self):
        actor = _Actor(profession="cleric")

        result = RoarService.can_roar(actor, "kuniyo")

        self.assertFalse(result.success)

    def test_silenced_and_safehaven_gates_are_canonical(self):
        self.assertIn("silence", RoarService.can_roar(_Actor(room=_Room(silenced=True)), "kuniyo").errors[0])
        self.assertIn("peace", RoarService.can_roar(_Actor(room=_Room(safehaven=True)), "kuniyo").errors[0])

    def test_position_gate_attempts_to_stand_with_frustration(self):
        actor = _Actor(position="prone")

        result = RoarService.can_roar(actor, "kuniyo")

        self.assertFalse(result.success)
        self.assertEqual(actor.db.position, "standing")
        self.assertIn("roar of frustration", result.messages[0])

    def test_invisible_gate_is_canonical(self):
        actor = _Actor(invisible=True)

        result = RoarService.can_roar(actor, "kuniyo")

        self.assertFalse(result.success)
        self.assertIn("metaphysical conundrum", result.errors[0])

    def test_droughtmans_maze_gate_is_canonical(self):
        actor = _Actor(room=_Room(room_id=1052001))

        result = RoarService.can_roar(actor, "kuniyo")

        self.assertFalse(result.success)
        self.assertEqual(result.errors[0], "Something prevents you from doing that.")

    def test_unknown_roar_name_still_returns_preview_message(self):
        actor = _Actor(circle=5)
        RoarService.ensure_kuniyo_auto_learned(actor)

        result = RoarService.can_roar(actor, "unknown-roar")

        self.assertFalse(result.success)
        self.assertIn("Have patience", result.errors[0])

    def test_known_gate_uses_proper_instruction_message(self):
        actor = _Actor(circle=15)

        result = RoarService.can_roar(actor, "everild")

        self.assertFalse(result.success)
        self.assertIn("proper instruction", result.errors[0])

    def test_deaths_shriek_requires_deaths_embrace_prerequisite(self):
        actor = _Actor(circle=75)

        result = RoarService.set_known_roar(actor, 6)

        self.assertFalse(result.success)
        self.assertIn("proper instruction", result.errors[0])

    def test_bare_roar_reports_voice_tier(self):
        actor = _Actor(circle=5)

        result = RoarService.invoke(actor)

        self.assertTrue(result.success)
        self.assertIn("defeat an army", result.messages[0])

    def test_kuniyo_success_sets_stun_susceptibility_effect(self):
        actor = _Actor(circle=5)
        target = _Target(actor.location)
        actor.set_target(target)
        RoarService.ensure_kuniyo_auto_learned(actor)

        result = RoarService.invoke(actor, "kuniyo", randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertIsNotNone(target.get_state("effect_2077001"))
        self.assertIsNotNone(target.get_state("barbarian_roar_kuniyo"))

    def test_everild_success_sets_defense_penalty_effects(self):
        actor = _Actor(circle=15)
        target = _Target(actor.location)
        actor.set_target(target)
        RoarService.ensure_kuniyo_auto_learned(actor)
        RoarService.set_known_roar(actor, 1)

        result = RoarService.invoke(actor, "everild", randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertIsNotNone(target.get_state("barbarian_roar_everild"))
        self.assertIsNotNone(target.get_state("effect_11808001"))

    def test_deaths_shriek_success_forces_target_to_kneel(self):
        actor = _Actor(circle=75)
        target = _Target(actor.location)
        actor.set_target(target)
        RoarService.ensure_kuniyo_auto_learned(actor)
        RoarService.set_known_roar(actor, 4)
        RoarService.set_known_roar(actor, 6)

        result = RoarService.invoke(actor, "death's shriek", randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertEqual(target.db.position, "kneeling")
        self.assertGreaterEqual(target.roundtime, 3)

    def test_magics_bane_success_sets_skill_penalties(self):
        actor = _Actor(circle=75)
        target = _Target(actor.location)
        actor.set_target(target)
        RoarService.ensure_kuniyo_auto_learned(actor)
        RoarService.set_known_roar(actor, 7)

        result = RoarService.invoke(actor, "magic's bane", randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        payload = target.get_state("barbarian_roar_magics_bane")
        self.assertIsNotNone(payload)
        self.assertLess(payload["skill_modifiers"]["primary_magic"], 0)

    def test_voice_gate_blocks_roar_when_total_exceeds_twenty(self):
        actor = _Actor(circle=5)
        target = _Target(actor.location)
        actor.set_target(target)
        RoarService.ensure_kuniyo_auto_learned(actor)
        for index in range(21):
            actor.set_state(
                "barbarian_vocal_damage",
                {"3089001": {"0": [RoarService.now() + 100] * 21}},
            )

        result = RoarService.invoke(actor, "kuniyo")

        self.assertFalse(result.success)
        self.assertIn("cannot muster enough energy", result.errors[0])

    def test_expired_target_effects_clean_on_read(self):
        actor = _Actor(circle=15)
        actor.set_state("barbarian_roar_everild", {"expires_at": RoarService.now() - 1, "penalties": {"shield": 7}})

        penalty = RoarService.get_defense_penalty(actor, "shield")

        self.assertEqual(penalty, 0)
        self.assertIsNone(actor.get_state("barbarian_roar_everild"))


if __name__ == "__main__":
    unittest.main()