import unittest
from types import SimpleNamespace
from unittest.mock import patch

from domain.combat.maneuvers import ManeuverID
from domain.combat.verbs import DEFENSE_VERBS
from engine.services.defense_verb_service import DefenseVerbService


class DummyDefender:
    def __init__(self, *, hidden=False, stunned=False, roundtime=False, skill_rank=0, circle=1, weapon_skill="light_edge"):
        self.db = SimpleNamespace(last_maneuver=0, stealthed=hidden, circle=circle)
        self._hidden = hidden
        self._stunned = stunned
        self._roundtime = roundtime
        self._skill_rank = skill_rank
        self._weapon_skill = weapon_skill
        self.roundtime_set = None

    def is_hidden(self):
        return self._hidden

    def break_stealth(self):
        self._hidden = False
        self.db.stealthed = False

    def is_stunned(self):
        return self._stunned

    def consume_stun(self):
        self._stunned = False

    def is_in_roundtime(self):
        return self._roundtime

    def set_roundtime(self, seconds):
        self.roundtime_set = seconds

    def get_last_maneuver(self):
        return self.db.last_maneuver

    def set_last_maneuver(self, maneuver_id):
        self.db.last_maneuver = int(maneuver_id or 0)

    def get_weapon_profile(self):
        return {"skill": self._weapon_skill}

    def get_skill(self, _name):
        return self._skill_rank

    def get_circle(self):
        return int(self.db.circle or 1)

    def _sync_exp_skill_state(self, _skill_name):
        return SimpleNamespace(skillset="primary", recalc_pool=lambda: None)

    def _persist_exp_skill_state(self, _exp_skill):
        return None

    def get_exp_skillset_tier(self, _skill_name):
        return "primary"


class DefenseVerbServiceTests(unittest.TestCase):
    def test_parry_sets_canonical_last_maneuver_and_roundtime(self):
        defender = DummyDefender()

        with patch("engine.services.defense_verb_service.random.randint", return_value=4), patch("engine.services.defense_verb_service.SkillService.award_xp"):
            execution = DefenseVerbService.execute(defender, "parry")

        self.assertTrue(execution.result.success)
        self.assertEqual(defender.get_last_maneuver(), int(ManeuverID.PARRY))
        self.assertEqual(defender.roundtime_set, 4)
        self.assertEqual(execution.result.data["message"], "You move into a position to parry.")

    def test_dodge_sets_canonical_last_maneuver_and_roundtime(self):
        defender = DummyDefender()

        with patch("engine.services.defense_verb_service.random.randint", return_value=3):
            execution = DefenseVerbService.execute(defender, "dodge")

        self.assertTrue(execution.result.success)
        self.assertEqual(defender.get_last_maneuver(), int(ManeuverID.DODGE))
        self.assertEqual(defender.roundtime_set, 3)

    def test_already_parrying_uses_canonical_block_message(self):
        defender = DummyDefender()
        defender.set_last_maneuver(ManeuverID.PARRY)

        execution = DefenseVerbService.execute(defender, "parry")

        self.assertFalse(execution.result.success)
        self.assertEqual(execution.result.data.get("block_message"), DEFENSE_VERBS["parry"].already_message)

    def test_hidden_parry_breaks_stealth_before_positioning(self):
        defender = DummyDefender(hidden=True)

        with patch("engine.services.defense_verb_service.random.randint", return_value=4), patch("engine.services.defense_verb_service.SkillService.award_xp"):
            execution = DefenseVerbService.execute(defender, "parry")

        self.assertTrue(execution.result.success)
        self.assertTrue(execution.result.data.get("broke_stealth"))
        self.assertFalse(defender.db.stealthed)

    def test_parry_awards_remedial_training_when_under_circle(self):
        defender = DummyDefender(skill_rank=1, circle=10)

        with patch("engine.services.defense_verb_service.random.randint", side_effect=[6, 4]), patch("engine.services.defense_verb_service.SkillService.award_xp") as award_xp:
            execution = DefenseVerbService.execute(defender, "parry")

        self.assertTrue(execution.result.success)
        award_xp.assert_called_once()
        self.assertEqual(award_xp.call_args.args[1], "parry_ability")

    def test_get_parry_skill_name_ignores_weapon_profile(self):
        defender = DummyDefender(weapon_skill="polearm")

        self.assertEqual(DefenseVerbService._get_parry_skill_name(defender), "parry_ability")

    def test_dodge_does_not_award_remedial_parry_training(self):
        defender = DummyDefender(skill_rank=1, circle=10)

        with patch("engine.services.defense_verb_service.random.randint", return_value=4), patch("engine.services.defense_verb_service.SkillService.award_xp") as award_xp:
            execution = DefenseVerbService.execute(defender, "dodge")

        self.assertTrue(execution.result.success)
        award_xp.assert_not_called()