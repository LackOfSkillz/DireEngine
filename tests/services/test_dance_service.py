import unittest
from types import SimpleNamespace

from domain.combat.resolution import compute_edf, compute_offensive_factor, compute_parry, compute_shield
from domain.abilities.roars.inspiration_shared import inspiration_strength
from engine.services.dance_service import DanceService
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import DummyCombatant, DummyRoom


class DanceServiceTests(unittest.TestCase):
    def test_cobra_bonus_increases_melee_offense_factor(self):
        room = DummyRoom(29)
        actor = DummyCombatant("Barbarian", room, circle=80)
        target = DummyCombatant("Goblin", room)
        actor.db.skills.update({"light_edge": 100, "tactics": 80})
        baseline = compute_offensive_factor(actor, target, {"profile": {"skill": "light_edge", "balance": 50}, "skill_name": "light_edge"}).base
        actor.set_spellbook2(1 << 2)
        self.assertTrue(DanceService.begin_dance(actor, "cobra").success)
        boosted = compute_offensive_factor(actor, target, {"profile": {"skill": "light_edge", "balance": 50}, "skill_name": "light_edge"}).base

        self.assertGreater(boosted, baseline)

    def test_panther_bonus_increases_ranged_evasion_defense(self):
        room = DummyRoom(291)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.db.skills.update({"evasion": 90})
        baseline = compute_edf(actor, context={"is_ranged_weapon": True}).usable_evasion_pct
        actor.set_spellbook2(1 << 7)
        self.assertTrue(DanceService.begin_dance(actor, "panther").success)
        boosted = compute_edf(actor, context={"is_ranged_weapon": True}).usable_evasion_pct

        self.assertGreater(boosted, baseline)

    def test_badger_bonus_increases_parry_and_shield_scores(self):
        room = DummyRoom(292)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.db.skills.update({"parry_ability": 90, "shield_usage": 70})
        actor.get_weapon_profile = lambda: {"balance": 50}
        actor.get_equipment = lambda: {"shield": [SimpleNamespace(db=SimpleNamespace(mindef=10, maxdef=60))]}
        baseline_parry = compute_parry(actor, 120).parry_score
        baseline_shield = compute_shield(actor, 120).shield_score
        actor.set_spellbook2(1 << 3)
        self.assertTrue(DanceService.begin_dance(actor, "badger").success)
        boosted_parry = compute_parry(actor, 120).parry_score
        boosted_shield = compute_shield(actor, 120).shield_score

        self.assertGreater(boosted_parry, baseline_parry)
        self.assertGreater(boosted_shield, baseline_shield)

    def test_begin_dance_requires_learning(self):
        room = DummyRoom(30)
        actor = DummyCombatant("Barbarian", room, circle=80)

        result = DanceService.begin_dance(actor, "swan")

        self.assertFalse(result.success)
        self.assertIn("proper instruction", result.errors[0])

    def test_begin_dance_sets_main_and_cyclic_effects(self):
        room = DummyRoom(31)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.set_spellbook2(1 << 1)

        result = DanceService.begin_dance(actor, "swan")

        self.assertTrue(result.success)
        self.assertIsNotNone(actor.get_state(DanceService.STATE_KEY))
        self.assertIsNotNone(actor.get_state("effect_3387100"))
        self.assertIsNotNone(actor.get_state("effect_3387001"))

    def test_starting_new_dance_ends_previous_one(self):
        room = DummyRoom(32)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.set_spellbook2((1 << 1) | (1 << 2))

        first = DanceService.begin_dance(actor, "swan")
        second = DanceService.begin_dance(actor, "cobra")

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(DanceService.get_active_dance(actor)["name"], "cobra")
        self.assertIn("inner fire cool", second.messages[0])

    def test_duration_formula_shortens_with_armor_and_encumbrance(self):
        room = DummyRoom(33)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.db.ccp = 200
        definition = type("Def", (), {"bit_index": 5})

        actor.db.armor_penalty = 0
        actor.db.encumberance = 0
        light = DanceService.compute_duration_seconds(actor, definition)
        actor.db.armor_penalty = 80
        actor.db.encumberance = 80
        heavy = DanceService.compute_duration_seconds(actor, definition)

        self.assertGreater(light, heavy)

    def test_wolverine_boosts_intimidation_power(self):
        room = DummyRoom(34)
        actor = DummyCombatant("Barbarian", room, circle=80)
        target = DummyCombatant("Goblin", room)
        actor.set_spellbook2(1 << 6)

        baseline = RoarService.calculate_margin(actor, target, style="kuniyo", modifier=100, randomizer=lambda _low, _high: 0)
        self.assertTrue(DanceService.begin_dance(actor, "wolverine").success)
        boosted = RoarService.calculate_margin(actor, target, style="kuniyo", modifier=100, randomizer=lambda _low, _high: 0)

        self.assertGreater(boosted, baseline)

    def test_eagle_boosts_inspiration_power(self):
        room = DummyRoom(35)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.set_spellbook2(1 << 4)

        baseline = inspiration_strength(RoarService, actor, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 0)
        self.assertTrue(DanceService.begin_dance(actor, "eagle").success)
        boosted = inspiration_strength(RoarService, actor, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 0)

        self.assertGreater(boosted, baseline)

    def test_end_dance_clears_states(self):
        room = DummyRoom(36)
        actor = DummyCombatant("Barbarian", room, circle=80)
        actor.set_spellbook2(1 << 1)
        DanceService.begin_dance(actor, "swan")

        result = DanceService.end_dance(actor)

        self.assertTrue(result.success)
        self.assertIsNone(actor.get_state(DanceService.STATE_KEY))
        self.assertIsNone(actor.get_state("effect_3387100"))
        self.assertIsNone(actor.get_state("effect_3387001"))


if __name__ == "__main__":
    unittest.main()