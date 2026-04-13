import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character


class DummyHolder:
    pass


class DummyRoom:
    def __init__(self, mana=None):
        self.db = DummyHolder()
        self.db.mana = dict(mana or {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0})


class EmpathBackfillDummy:
    gate_mana_effect = Character.gate_mana_effect
    _fail_mana_gate = Character._fail_mana_gate

    def __init__(self, attunement=100.0, healing_modifier=1.0):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.location = DummyRoom()
        self.db.attunement = attunement
        self.db.max_attunement = 100.0
        self.db.in_combat = False
        self.messages = []
        self._wounds = {"vitality": 20, "bleeding": 10}
        self.healing_modifier = healing_modifier

    def ensure_core_defaults(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def is_empath(self):
        return True

    def get_empath_wounds(self):
        return dict(self._wounds)

    def get_empath_wound(self, wound_type):
        return int(self._wounds.get(wound_type, 0) or 0)

    def set_empath_wound(self, wound_type, value):
        updated = max(0, int(value or 0))
        self._wounds[str(wound_type)] = updated
        return updated

    def get_empath_healing_modifier(self):
        return float(self.healing_modifier)

    def award_empathy_experience(self, *args, **kwargs):
        _args = args
        _kwargs = kwargs
        return 0

    def is_empath_tutorial_active(self):
        return False

    def set_empath_training_stage(self, value):
        _value = value
        return None


class ClericBackfillDummy:
    gate_mana_effect = Character.gate_mana_effect
    _fail_mana_gate = Character._fail_mana_gate
    get_devotion_effect_multiplier = Character.get_devotion_effect_multiplier
    get_commune_profile = Character.get_commune_profile

    def __init__(self, attunement=100.0, devotion=50, devotion_max=100):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.location = DummyRoom()
        self.db.attunement = attunement
        self.db.max_attunement = 100.0
        self.messages = []
        self.devotion = devotion
        self.devotion_max = devotion_max
        self.last_barrier = None

    def ensure_core_defaults(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def is_profession(self, profession):
        return str(profession or "").strip().lower() == "cleric"

    def is_dead(self):
        return False

    def get_devotion(self):
        return int(self.devotion)

    def get_devotion_max(self):
        return int(self.devotion_max)

    def get_devotion_state_message(self):
        return "Your connection feels steady."

    def get_profession_rank(self):
        return 12

    def apply_warding_barrier(self, target, name, strength, duration):
        self.last_barrier = {
            "target": target,
            "name": name,
            "strength": strength,
            "duration": duration,
        }

    def adjust_devotion(self, amount, sync=False):
        _sync = sync
        self.devotion = max(0, min(self.devotion_max, self.devotion + int(amount)))
        return self.devotion

    def sync_client_state(self):
        return None

    def use_skill(self, *args, **kwargs):
        _args = args
        _kwargs = kwargs
        return None

    def get_theurgy_training_difficulty(self, value):
        return int(value)


class ManaProfessionBackfillTests(unittest.TestCase):
    def test_empath_mend_fails_with_zero_attunement(self):
        empath = EmpathBackfillDummy(attunement=0.0, healing_modifier=1.0)

        ok, message = Character.mend_empath_self(empath)

        self.assertFalse(ok)
        self.assertIn("Not enough attunement.", message)

    def test_empath_mend_is_reduced_under_shock_modifier(self):
        low_shock = EmpathBackfillDummy(attunement=100.0, healing_modifier=1.0)
        high_shock = EmpathBackfillDummy(attunement=100.0, healing_modifier=0.5)

        ok_low, _ = Character.mend_empath_self(low_shock)
        ok_high, _ = Character.mend_empath_self(high_shock)

        self.assertTrue(ok_low)
        self.assertTrue(ok_high)
        self.assertLess(low_shock.get_empath_wound("vitality"), high_shock.get_empath_wound("vitality"))
        self.assertLess(low_shock.get_empath_wound("bleeding"), high_shock.get_empath_wound("bleeding"))

    def test_cleric_commune_ward_fails_with_zero_attunement_even_with_high_devotion(self):
        cleric = ClericBackfillDummy(attunement=0.0, devotion=100, devotion_max=100)

        ok, message = Character.commune_with_divine(cleric, "ward")

        self.assertFalse(ok)
        self.assertIn("Not enough attunement.", message)
        self.assertIsNone(cleric.last_barrier)

    def test_cleric_devotion_increases_ward_strength_after_mana_gate(self):
        low_devotion = ClericBackfillDummy(attunement=100.0, devotion=20, devotion_max=100)
        high_devotion = ClericBackfillDummy(attunement=100.0, devotion=100, devotion_max=100)

        ok_low, _ = Character.commune_with_divine(low_devotion, "ward")
        ok_high, _ = Character.commune_with_divine(high_devotion, "ward")

        self.assertTrue(ok_low)
        self.assertTrue(ok_high)
        self.assertIsNotNone(low_devotion.last_barrier)
        self.assertIsNotNone(high_devotion.last_barrier)
        self.assertLess(low_devotion.last_barrier["strength"], high_devotion.last_barrier["strength"])


if __name__ == "__main__":
    unittest.main()
