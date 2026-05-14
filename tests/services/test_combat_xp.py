import unittest
from unittest.mock import patch

from domain.combat.resolution import CombatOutcome
from engine.services.combat_xp import CombatXP, DEFENSE_XP_MULT


class DummyActor:
    def __init__(self, *, incoming_attackers=1):
        self.incoming_attackers = incoming_attackers

    def get_stat(self, _name):
        return 10

    def get_skill(self, _name):
        return 10

    def get_weapon_profile(self):
        return {"skill": "light_edge"}


class CombatXPTests(unittest.TestCase):
    @patch("engine.services.combat_xp.SkillService.award_xp")
    def test_final_chance_zero_is_preserved(self, award_xp):
        attacker = DummyActor()
        target = DummyActor()

        CombatXP.award(attacker, target, {"final_chance": 0, "accuracy": 0}, hit=False)

        award_xp.assert_called_once_with(
            target,
            "evasion",
            10,
            source={"mode": "difficulty"},
            success=True,
            context_multiplier=DEFENSE_XP_MULT,
        )

    @patch("engine.services.combat_xp.SkillService.award_xp")
    def test_leftover_of_path_uses_offensive_factor_for_defense_xp(self, award_xp):
        attacker = DummyActor()
        target = DummyActor()

        CombatXP.award(
            attacker,
            target,
            {"leftover_of": -5, "offensive_factor_total": 80, "evasion_defense_factor_total": 100},
            hit=False,
        )

        award_xp.assert_called_once_with(
            target,
            "evasion",
            80,
            source={"mode": "difficulty"},
            success=True,
            context_multiplier=DEFENSE_XP_MULT * 1.25,
        )

    @patch("engine.services.combat_xp.SkillService.award_xp")
    def test_successful_parry_awards_parry_ability_defense_xp(self, award_xp):
        attacker = DummyActor()
        target = DummyActor()

        CombatXP.award(
            attacker,
            target,
            {
                "leftover_of": 10,
                "offensive_factor_total": 80,
                "evasion_defense_factor_total": 40,
                "combat_outcome": CombatOutcome.FULLY_PARRIED.value,
                "parry": {"block_pct": 100},
            },
            hit=False,
        )

        self.assertEqual(award_xp.call_count, 2)
        self.assertEqual(award_xp.call_args_list[1].args[1], "parry_ability")

    @patch("engine.services.combat_xp.SkillService.award_xp")
    def test_successful_shield_block_awards_shield_usage(self, award_xp):
        attacker = DummyActor()
        target = DummyActor()

        CombatXP.award(
            attacker,
            target,
            {
                "leftover_of": 10,
                "offensive_factor_total": 80,
                "evasion_defense_factor_total": 40,
                "combat_outcome": CombatOutcome.FULLY_SHIELDED.value,
                "shield": {"block_pct": 100},
            },
            hit=False,
        )

        self.assertEqual(award_xp.call_count, 2)
        self.assertEqual(award_xp.call_args_list[1].args[1], "shield_usage")

    @patch("engine.services.combat_xp.SkillService.award_xp")
    def test_multiple_opponents_awards_moe_smaller_than_primary_defense(self, award_xp):
        attacker = DummyActor()
        target = DummyActor(incoming_attackers=2)

        CombatXP.award(
            attacker,
            target,
            {
                "leftover_of": -5,
                "offensive_factor_total": 80,
                "evasion_defense_factor_total": 100,
            },
            hit=False,
        )

        self.assertEqual(award_xp.call_count, 2)
        self.assertEqual(award_xp.call_args_list[0].args[1], "evasion")
        self.assertEqual(award_xp.call_args_list[1].args[1], "multiple_engaged_opponent")
        self.assertLess(award_xp.call_args_list[1].kwargs["context_multiplier"], award_xp.call_args_list[0].kwargs["context_multiplier"])


if __name__ == "__main__":
    unittest.main()