import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.combat.resolution import AttackResolution
from engine.services.combat_service import CombatService
from engine.services.empath_saf_service import EmpathSafService
from engine.services.result import ActionResult


class _DummyCharacter:
    def __init__(self, key="Empath", profession="empath", hp=100, circle=10):
        self.key = key
        self.profession = profession
        self.db = SimpleNamespace(
            hp=hp,
            max_hp=hp,
            stunned=False,
            stunned_until=0.0,
            position="standing",
            last_maneuver=0,
            empath_saf_duration=0,
            empath_saf_burden=0,
            empath_permashock=False,
        )
        self.ndb = SimpleNamespace()
        self.messages = []
        self.location = object()
        self._circle = circle
        self.target = None

    def is_empath(self):
        return self.profession == "empath"

    def get_circle(self):
        return self._circle

    def msg(self, text):
        self.messages.append(str(text))

    def sync_client_state(self):
        return None

    def set_target(self, target):
        self.target = target

    def get_weapon_profile(self):
        return {}

    def get_range(self, target):
        _target = target
        return "melee"

    def get_wielded_weapon(self):
        return None

    def is_stunned(self):
        return False

    def consume_stun(self):
        return False

    def is_in_roundtime(self):
        return False

    def get_balance(self):
        return 100, 100

    def is_alive(self):
        return int(self.db.hp or 0) > 0

    def set_hp(self, value):
        self.db.hp = int(value)


class EmpathSafServiceTests(unittest.TestCase):
    def test_major_injury_applies_saf_stun_and_prone(self):
        empath = _DummyCharacter()
        target = _DummyCharacter(key="Target", profession="commoner")

        state = EmpathSafService.register_offense(empath, target, hit=True, damage=12, killed=False)

        self.assertGreater(int(state["duration"]), 0)
        self.assertEqual(int(state["burden"]), 20)
        self.assertTrue(bool(empath.db.stunned))
        self.assertEqual(empath.db.position, "prone")
        self.assertTrue(any("extreme shock" in line.lower() for line in empath.messages))

    def test_permashock_triggers_after_threshold_cross(self):
        empath = _DummyCharacter()
        target = _DummyCharacter(key="Target", profession="commoner")
        empath.db.empath_saf_burden = 490

        state = EmpathSafService.register_offense(empath, target, hit=True, damage=12, killed=False)

        self.assertTrue(bool(state["permashocked"]))
        self.assertEqual(int(empath.db.empath_saf_burden), EmpathSafService.PERMASHOCK_BURDEN)
        self.assertTrue(any("empathic abilities have disappeared" in line.lower() for line in empath.messages))

    def test_combat_hook_marks_missed_attack_as_saf_aggression(self):
        attacker = _DummyCharacter()
        target = _DummyCharacter(key="Target", profession="commoner")

        with patch.object(CombatService, "_validate_attack", return_value=None), patch.object(CombatService, "_prepare_attack", return_value=ActionResult.ok(data={"outcome": "ready"})), patch.object(CombatService, "_build_context", return_value={"is_ranged_weapon": False, "fatigue_cost": 0, "ambush": False, "current_range": "melee"}), patch("engine.services.combat_service.resolve_attack", return_value=AttackResolution(hit=False, damage=0, roundtime=1.0, details={})), patch.object(CombatService, "_apply_post_resolution_state", return_value=None), patch.object(CombatService, "_resolve_ranged_ammo_outcome", return_value=None), patch("engine.services.combat_service.CombatXP.award"), patch("engine.services.combat_service.StateService.apply_fatigue"), patch("engine.services.combat_service.StateService.apply_roundtime"):
            result = CombatService.attack(attacker, target)

        self.assertTrue(result.success)
        self.assertGreater(int(attacker.db.empath_saf_duration or 0), 0)
        self.assertGreater(float(attacker.db.stunned_until or 0.0), time.time())


if __name__ == "__main__":
    unittest.main()