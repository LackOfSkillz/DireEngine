import unittest
from unittest.mock import patch

from engine.services.combat_xp import CombatXP, DEFENSE_XP_MULT


class DummyActor:
    def get_stat(self, _name):
        return 10

    def get_skill(self, _name):
        return 10


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


if __name__ == "__main__":
    unittest.main()