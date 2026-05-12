import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.characters import Character


class _DummyItem:
    def __init__(self, key="folio", *, skill="scholarship", difficulty=10, study_uses=0, is_study_item=True):
        self.key = key
        self.db = SimpleNamespace(
            skill=skill,
            difficulty=difficulty,
            study_uses=study_uses,
            is_study_item=is_study_item,
        )


class _DummyTarget:
    def __init__(self, key="sparring partner", target_id=42):
        self.key = key
        self.id = target_id


class _DummyCharacter:
    def __init__(self, *, scholarship=0, tactics=0):
        self._scholarship = scholarship
        self._tactics = tactics
        self.messages = []
        self.states = {}
        self.skill_awards = []
        self.skill_uses = []

    def get_skill(self, skill_name):
        if skill_name == "scholarship":
            return self._scholarship
        if skill_name == "tactics":
            return self._tactics
        return 0

    def msg(self, text):
        self.messages.append(str(text))

    def award_skill_experience(self, *args, **kwargs):
        self.skill_awards.append((args, kwargs))
        return 1.0

    def use_skill(self, *args, **kwargs):
        self.skill_uses.append((args, kwargs))
        return True

    def set_state(self, key, value):
        self.states[key] = value

    def _is_anatomy_study_item(self, item):
        return False


class LoreSkillAttemptTests(unittest.TestCase):
    def test_scholarship_success_awards_full_xp(self):
        character = _DummyCharacter(scholarship=20)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.recall_knowledge(character, "flora")

        helper.assert_not_called()
        self.assertEqual(len(character.skill_awards), 1)
        self.assertIn("You recall some useful details.", character.messages)

    def test_scholarship_skill_too_low_failure_awards_quarter_xp(self):
        character = _DummyCharacter(scholarship=0)
        item = _DummyItem(difficulty=12)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            result = Character.study_item(character, item)

        self.assertFalse(result)
        helper.assert_called_once_with(
            character,
            "scholarship",
            12,
            success=False,
            failure_reason="skill_too_low",
            event_key="study",
            failure_multiplier=0.25,
        )

    def test_scholarship_other_failure_awards_no_xp(self):
        character = _DummyCharacter(scholarship=20)
        item = _DummyItem(is_study_item=False)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            result = Character.study_item(character, item)

        self.assertFalse(result)
        helper.assert_not_called()
        self.assertEqual(character.skill_awards, [])

    def test_scholarship_at_zero_rank_can_attempt(self):
        character = _DummyCharacter(scholarship=0)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.recall_knowledge(character, "flora")

        helper.assert_called_once()
        self.assertEqual(character.messages[0], "You try to recall what you know about flora.")

    def test_tactics_success_awards_full_xp(self):
        character = _DummyCharacter(tactics=20)
        target = _DummyTarget()

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.assess_stance(character, target)

        helper.assert_not_called()
        self.assertEqual(len(character.skill_uses), 1)
        self.assertEqual(character.states["tactics_prep"]["target"], target.id)

    def test_tactics_skill_too_low_failure_awards_quarter_xp(self):
        character = _DummyCharacter(tactics=0)
        target = _DummyTarget()

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.assess_stance(character, target)

        helper.assert_called_once_with(
            character,
            "tactics",
            10,
            success=False,
            failure_reason="skill_too_low",
            event_key="assess_stance",
            failure_multiplier=0.25,
        )
        self.assertEqual(character.skill_uses, [])

    def test_tactics_other_failure_awards_no_xp(self):
        character = _DummyCharacter(tactics=0)
        target = _DummyTarget()

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.assess_stance(character, target)

        self.assertEqual(len(helper.call_args_list), 1)
        self.assertEqual(character.skill_awards, [])

    def test_tactics_at_zero_rank_can_attempt(self):
        character = _DummyCharacter(tactics=0)
        target = _DummyTarget()

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.assess_stance(character, target)

        helper.assert_called_once()
        self.assertIn("You struggle to read their intentions.", character.messages)


if __name__ == "__main__":
    unittest.main()