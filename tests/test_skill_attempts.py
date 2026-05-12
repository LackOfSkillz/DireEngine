from unittest import TestCase
from unittest.mock import patch

from engine.services.result import ActionResult
from world.helpers.skill_attempts import attempt_with_failure_learning


class _DummyCharacter:
    pass


class SkillAttemptHelperTests(TestCase):
    def test_success_awards_full_xp(self):
        character = _DummyCharacter()
        with patch(
            "world.helpers.skill_attempts.SkillService.award_xp",
            return_value=ActionResult.ok(data={"amount": 7.0}),
        ) as award_xp:
            result = attempt_with_failure_learning(
                character,
                "perception",
                14,
                success=True,
                event_key="search",
            )

        award_xp.assert_called_once_with(
            character,
            "perception",
            14,
            source={"mode": "difficulty"},
            success=True,
            outcome="success",
            event_key="search",
            context_multiplier=1.0,
        )
        self.assertEqual(result["awarded"], 7.0)
        self.assertTrue(result["awarded_xp"])

    def test_skill_too_low_failure_awards_quarter_xp(self):
        character = _DummyCharacter()
        with patch(
            "world.helpers.skill_attempts.SkillService.award_xp",
            return_value=ActionResult.ok(data={"amount": 2.0}),
        ) as award_xp:
            result = attempt_with_failure_learning(
                character,
                "scholarship",
                20,
                success=False,
                failure_reason="skill_too_low",
                event_key="study",
            )

        award_xp.assert_called_once_with(
            character,
            "scholarship",
            20,
            source={"mode": "difficulty"},
            success=False,
            outcome="failure",
            event_key="study",
            context_multiplier=0.25,
        )
        self.assertEqual(result["failure_reason"], "skill_too_low")
        self.assertEqual(result["awarded"], 2.0)

    def test_other_failure_awards_no_xp(self):
        character = _DummyCharacter()
        with patch("world.helpers.skill_attempts.SkillService.award_xp") as award_xp:
            result = attempt_with_failure_learning(
                character,
                "arcana",
                18,
                success=False,
                failure_reason="no_focus",
                event_key="charge",
            )

        award_xp.assert_not_called()
        self.assertEqual(result["awarded"], 0.0)
        self.assertFalse(result["awarded_xp"])
        self.assertEqual(result["failure_reason"], "no_focus")

    def test_unknown_skill_logs_warning(self):
        character = _DummyCharacter()
        with (
            patch("world.helpers.skill_attempts._skill_exists", return_value=False),
            patch("world.helpers.skill_attempts.logger.warning") as warning,
            patch("world.helpers.skill_attempts.SkillService.award_xp") as award_xp,
        ):
            result = attempt_with_failure_learning(character, "mystery_skill", 10, success=True)

        warning.assert_called_once()
        award_xp.assert_not_called()
        self.assertEqual(result["failure_reason"], "unknown_skill")

    def test_helper_returns_xp_metadata(self):
        character = _DummyCharacter()
        with patch(
            "world.helpers.skill_attempts.SkillService.award_xp",
            return_value=ActionResult.ok(data={"amount": 3.5}),
        ):
            result = attempt_with_failure_learning(character, "tactics", 12, success=True, event_key="assess_stance")

        self.assertEqual(
            result,
            {
                "skill": "tactics",
                "difficulty": 12,
                "awarded": 3.5,
                "awarded_xp": True,
                "outcome": "success",
                "failure_reason": None,
            },
        )

    def test_custom_multipliers_respected(self):
        character = _DummyCharacter()
        with patch(
            "world.helpers.skill_attempts.SkillService.award_xp",
            return_value=ActionResult.ok(data={"amount": 1.0}),
        ) as award_xp:
            attempt_with_failure_learning(
                character,
                "perception",
                16,
                success=False,
                failure_reason="skill_too_low",
                failure_multiplier=0.4,
            )

        self.assertEqual(award_xp.call_args.kwargs["context_multiplier"], 0.4)