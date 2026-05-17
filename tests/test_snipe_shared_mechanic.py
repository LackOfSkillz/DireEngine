import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character


class _Target:
    def __init__(self, target_id=7, key="target"):
        self.id = target_id
        self.key = key


class _SnipeActor:
    def __init__(self, *, profession="ranger", guild1=0, thieftrix=0, thieftrix2=0, hidden=True, stealthed=False, invisible=False, ammo_loaded=True):
        self.profession = profession
        self.db = SimpleNamespace(
            profession=profession,
            guild1=guild1,
            thieftrix=thieftrix,
            thieftrix2=thieftrix2,
            stealthed=stealthed,
            invisible=invisible,
        )
        self._hidden = hidden
        self._state = {}
        self.target = None
        self._weapon = SimpleNamespace(db=SimpleNamespace(ammo_loaded=ammo_loaded))
        self.location = SimpleNamespace(contents=[])
        self.search_result = _Target()

    def is_profession(self, name):
        return self.profession == name

    def is_hidden(self):
        return self._hidden

    def get_state(self, key):
        return self._state.get(key)

    def set_state(self, key, value):
        self._state[key] = value

    def clear_state(self, key):
        self._state.pop(key, None)

    def get_equipped_ranged_weapon(self):
        return self._weapon

    def search(self, _query, candidates=None):
        return self.search_result

    def set_target(self, target):
        self.target = target

    def get_ranger_aim_stacks(self, target):
        return 2

    def get_ranger_bond_accuracy_bonus(self):
        return 4

    def get_ranger_aim_focus_accuracy_bonus(self):
        return 3

    def get_ranger_aim_focus_damage_multiplier(self):
        return 1.2

    def _get_snipe_training_status(self):
        return Character._get_snipe_training_status(self)

    def _is_canonically_positioned_to_snipe(self):
        return Character._is_canonically_positioned_to_snipe(self)

    def prepare_snipe(self, target_name):
        return Character.prepare_snipe(self, target_name)


class SharedSnipeMechanicTests(unittest.TestCase):
    def test_ranger_training_uses_guild1_bits(self):
        actor = _SnipeActor(profession="ranger", guild1=1)

        ok, message = Character._get_snipe_training_status(actor)

        self.assertTrue(ok)
        self.assertEqual(message, "")

    def test_ranger_banned_snipe_uses_guild1_bit_one(self):
        actor = _SnipeActor(profession="ranger", guild1=3)

        ok, message = Character._get_snipe_training_status(actor)

        self.assertFalse(ok)
        self.assertEqual(message, "You seem to have forgotten the intricacies of sniping.")

    def test_thief_training_uses_thieftrix_bits(self):
        actor = _SnipeActor(profession="thief", thieftrix=(1 << 31))

        ok, message = Character._get_snipe_training_status(actor)

        self.assertTrue(ok)
        self.assertEqual(message, "")

    def test_off_class_rejected_by_canonical_profession_gate(self):
        actor = _SnipeActor(profession="cleric")

        ok, message = Character._get_snipe_training_status(actor)

        self.assertFalse(ok)
        self.assertEqual(message, "You have not been trained in the ways of sniping.")

    def test_prepare_snipe_requires_hidden_or_explicit_stealth_flags(self):
        actor = _SnipeActor(profession="ranger", guild1=1, hidden=False, stealthed=False, invisible=False)

        ok, message, should_attack = Character.prepare_snipe(actor, "target")

        self.assertFalse(ok)
        self.assertFalse(should_attack)
        self.assertEqual(message, "How can you snipe if you are not hidden?")

    def test_prepare_snipe_sets_profession_neutral_state_name(self):
        actor = _SnipeActor(profession="ranger", guild1=1)

        ok, message, should_attack = Character.prepare_snipe(actor, "target")

        self.assertTrue(ok)
        self.assertTrue(should_attack)
        self.assertEqual(message, "You release a carefully placed shot from concealment.")
        self.assertIn("prepared_snipe", actor._state)
        self.assertNotIn("ranger_snipe", actor._state)
        self.assertEqual(actor._state["prepared_snipe"]["target_id"], actor.search_result.id)

    def test_prepare_snipe_keeps_ranger_overlay_but_shared_profession_neutral_key(self):
        actor = _SnipeActor(profession="ranger", guild1=1)

        Character.prepare_snipe(actor, "target")

        prepared = actor._state["prepared_snipe"]
        self.assertEqual(prepared["overlay"], "ranger_directengine_canon")
        self.assertEqual(prepared["accuracy_bonus"], 48)
        self.assertAlmostEqual(prepared["damage_multiplier"], 1.86)

    def test_prepare_snipe_allows_thief_without_ranger_overlay(self):
        actor = _SnipeActor(profession="thief", thieftrix=(1 << 31))

        ok, _message, should_attack = Character.prepare_snipe(actor, "target")

        self.assertTrue(ok)
        self.assertTrue(should_attack)
        prepared = actor._state["prepared_snipe"]
        self.assertEqual(prepared["overlay"], "shared_gsl_2004")
        self.assertEqual(prepared["accuracy_bonus"], 25)
        self.assertAlmostEqual(prepared["damage_multiplier"], 1.35)


if __name__ == "__main__":
    unittest.main()