import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.combat.damage import MANEUVER_DAMAGE_MODS
from domain.combat.resolution import calculate_roundtime
from domain.combat.verbs import ATTACK_VERBS
from engine.services.attack_verb_service import AttackVerbService, EMPATH_ATTACK_BLOCK_MESSAGE
from engine.services.combat_service import CombatService
from engine.services.result import ActionResult


class DummyAliases:
    def __init__(self, *aliases):
        self._aliases = list(aliases)

    def all(self):
        return list(self._aliases)


class DummyTarget:
    def __init__(self, key="training dummy", *, hook=None, is_choppable=False, aliases=()):
        self.key = key
        self.aliases = DummyAliases(*aliases)
        self.db = SimpleNamespace(is_corpse=False, hp=100, max_hp=100, is_npc=False)
        self.location = None
        self.id = id(self)
        self._hook = hook
        self.is_choppable = is_choppable

    def on_attack_attempt(self, attacker, verb="slice"):
        if self._hook is None:
            return None
        return self._hook(attacker, verb=verb)

    def set_target(self, target):
        self._target = target

    def is_alive(self):
        return True

    def is_typeclass(self, path, exact=False):
        return path == "typeclasses.characters.Character"


class DummyRoom:
    def __init__(self, contents=None):
        self.contents = list(contents or [])


class DummyAttacker:
    def __init__(self, *, profession="commoner", target=None, room=None):
        self._profession = profession
        self._target = target
        self.location = room or DummyRoom()
        self.key = "Attacker"

    def get_target(self):
        return self._target

    def get_profession(self):
        return self._profession

    def is_profession(self, name):
        return str(name or "").strip().lower() == self._profession


class RoundtimeDummy:
    def __init__(self):
        self.db = SimpleNamespace(position_state="neutral")

    def is_warrior_overextended(self):
        return False


class AttackVerbRoutingTests(unittest.TestCase):
    def assert_routes(self, verb_key, rt_seconds, verb_id):
        target = DummyTarget(key=f"{verb_key} dummy")
        attacker = DummyAttacker(target=target)

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, verb_key, target_arg="")

        self.assertIs(execution.target, target)
        self.assertTrue(execution.result.success)
        combat_attack.assert_called_once_with(attacker, target, verb=verb_key, verb_rt=rt_seconds, verb_id=verb_id)

    def test_thrust_routes_with_5_rt_and_thrust_verb_string(self):
        """GSL S00031: thrust sets b5=5, v9=2, s9='thrust'."""
        self.assert_routes("thrust", 5, 2)

    def test_lunge_routes_with_7_rt_and_lunge_verb_string(self):
        """GSL S00032: lunge sets b5=7, v9=3, s9='lunge'."""
        self.assert_routes("lunge", 7, 3)

    def test_slice_routes_with_5_rt_and_slice_verb_string(self):
        """GSL S00033: slice sets b5=5, v9=4, s9='slice'."""
        self.assert_routes("slice", 5, 4)

    def test_chop_routes_with_5_rt_and_chop_verb_string(self):
        """GSL S00034: chop sets b5=5, v9=5, s9='chop'."""
        self.assert_routes("chop", 5, 5)

    def test_sweep_routes_with_5_rt_and_sweep_verb_string(self):
        """GSL S00035: sweep sets b5=5, v9=6, s9='sweep'."""
        self.assert_routes("sweep", 5, 6)

    def test_feint_routes_with_3_rt_and_feint_verb_string(self):
        """GSL S00036: feint sets b5=3, v9=7, s9='feint'."""
        self.assert_routes("feint", 3, 7)

    def test_jab_routes_with_4_rt_and_jab_verb_string(self):
        """GSL S00037: jab sets b5=4, v9=8, s9='jab'."""
        self.assert_routes("jab", 4, 8)

    def test_attack_verb_table_matches_canon(self):
        self.assertEqual(ATTACK_VERBS["thrust"].rt_seconds, 5)
        self.assertEqual(ATTACK_VERBS["thrust"].verb_id, 2)
        self.assertEqual(ATTACK_VERBS["lunge"].rt_seconds, 7)
        self.assertEqual(ATTACK_VERBS["lunge"].verb_id, 3)
        self.assertTrue(ATTACK_VERBS["slice"].triggers_defender_script)
        self.assertTrue(ATTACK_VERBS["chop"].has_terrain_guard)
        self.assertTrue(ATTACK_VERBS["feint"].uses_engagement_target)
        self.assertEqual(ATTACK_VERBS["jab"].rt_seconds, 4)
        self.assertEqual(ATTACK_VERBS["jab"].verb_id, 8)

    def test_all_seven_verbs_exist_in_maneuver_damage_mods(self):
        for key in ("thrust", "lunge", "slice", "chop", "sweep", "feint", "jab"):
            self.assertIn(key, MANEUVER_DAMAGE_MODS)

    def test_empath_blocked_from_all_attack_verbs(self):
        attacker = DummyAttacker(profession="empath")
        for verb_key in ATTACK_VERBS:
            with self.subTest(verb=verb_key):
                execution = AttackVerbService.execute(attacker, verb_key, target_arg="training dummy")
                self.assertFalse(execution.result.success)
                self.assertEqual(execution.result.data.get("block_message"), EMPATH_ATTACK_BLOCK_MESSAGE)

    def test_chop_trees_with_no_choppable_yields_terrain_message(self):
        attacker = DummyAttacker(room=DummyRoom())

        execution = AttackVerbService.execute(attacker, "chop", target_arg="trees")

        self.assertFalse(execution.result.success)
        self.assertEqual(execution.result.data.get("block_message"), "There are no trees around here you really want to chop.")

    def test_chop_vines_with_no_choppable_yields_terrain_message(self):
        attacker = DummyAttacker(room=DummyRoom())

        execution = AttackVerbService.execute(attacker, "chop", target_arg="vines")

        self.assertFalse(execution.result.success)
        self.assertEqual(execution.result.data.get("block_message"), "There are no vines around here you really want to chop.")

    def test_chop_target_proceeds_to_combat(self):
        target = DummyTarget(key="orc")
        attacker = DummyAttacker(room=DummyRoom([target]))
        target.location = attacker.location

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, "chop", target_arg="orc")

        self.assertTrue(execution.result.success)
        combat_attack.assert_called_once()

    def test_slice_defender_hook_halts_when_target_returns_false(self):
        target = DummyTarget(hook=lambda attacker, verb="slice": False)
        attacker = DummyAttacker(target=target)

        with patch.object(CombatService, "attack") as combat_attack:
            execution = AttackVerbService.execute(attacker, "slice", target_arg="")

        self.assertTrue(execution.result.success)
        self.assertEqual(execution.result.data.get("outcome"), "handled")
        combat_attack.assert_not_called()

    def test_slice_no_hook_attribute_proceeds_normally(self):
        class NoHookTarget(DummyTarget):
            on_attack_attempt = None

        target = NoHookTarget()
        attacker = DummyAttacker(target=target)

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, "slice", target_arg="")

        self.assertTrue(execution.result.success)
        combat_attack.assert_called_once()

    def test_feint_with_no_target_falls_back_to_engagement(self):
        target = DummyTarget()
        attacker = DummyAttacker(target=target)

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, "feint", target_arg="")

        self.assertIs(execution.target, target)
        combat_attack.assert_called_once_with(attacker, target, verb="feint", verb_rt=3, verb_id=7)

    def test_feint_with_explicit_target_uses_it(self):
        current = DummyTarget(key="current dummy")
        explicit = DummyTarget(key="explicit dummy")
        room = DummyRoom([explicit])
        explicit.location = room
        attacker = DummyAttacker(target=current, room=room)

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, "feint", target_arg="explicit")

        self.assertIs(execution.target, explicit)
        combat_attack.assert_called_once_with(attacker, explicit, verb="feint", verb_rt=3, verb_id=7)

    def test_attack_service_strips_at_prefix_before_resolution(self):
        target = DummyTarget(key="training dummy")
        room = DummyRoom([target])
        target.location = room
        attacker = DummyAttacker(room=room)

        with patch.object(CombatService, "attack", return_value=ActionResult.ok(data={"outcome": "hit"})) as combat_attack:
            execution = AttackVerbService.execute(attacker, "thrust", target_arg="at training dummy")

        self.assertIs(execution.target, target)
        combat_attack.assert_called_once()

    def test_calculate_roundtime_prefers_explicit_verb_rt(self):
        attacker = RoundtimeDummy()
        target = RoundtimeDummy()
        context = {
            "profile": {"speed": 3.0},
            "attacker_berserk": None,
            "ambush": False,
            "partial_ambush": False,
            "hit": False,
            "leftover_of": 0,
            "fatigue_cost": 0,
            "verb_rt": 7,
        }

        roundtime = calculate_roundtime(attacker, target, context=context)

        self.assertEqual(roundtime, 7)

    def test_build_result_payload_preserves_explicit_verb(self):
        details = {
            "current_range": "melee",
            "damage_type": "puncture",
            "location_name": "head",
            "outcome": "hit",
            "quality": "good",
            "verb": "lunge",
            "weapon_name": "training sword",
        }
        attacker = SimpleNamespace(key="Attacker")
        target = SimpleNamespace(key="Target")
        resolution = SimpleNamespace(hit=True, roundtime=7)
        damage_result = ActionResult.ok(data={"amount": 3, "injury_events": []})

        payload = CombatService._build_result_payload(attacker, target, details, resolution, damage_result)

        self.assertEqual(payload["verb"], "lunge")
