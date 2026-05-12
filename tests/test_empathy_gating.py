import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_diagnose import CmdDiagnose
from commands.cmd_study_anatomy import CmdStudyAnatomy
from typeclasses.characters import Character


class _AnatomyStudyItem:
    def __init__(self, difficulty=10):
        self.key = "anatomy chart"
        self.db = SimpleNamespace(is_study_item=True, study_uses=0, skill="scholarship", difficulty=difficulty, anatomy_study=True)


class _StudyCharacter:
    def __init__(self, *, empath=False, empathy=0):
        self.messages = []
        self.awards = []
        self._empath = empath
        self._empathy = empathy

    def get_skill(self, skill_name):
        if skill_name in {"scholarship", "first_aid"}:
            return 20
        if skill_name == "empathy":
            return self._empathy
        return 0

    def msg(self, text):
        self.messages.append(str(text))

    def award_skill_experience(self, skill, difficulty, **kwargs):
        self.awards.append((skill, difficulty, kwargs))

    def _is_anatomy_study_item(self, item):
        return bool(getattr(getattr(item, "db", None), "anatomy_study", False))

    def is_empath(self):
        return self._empath


class _DiagnoseCaller:
    def __init__(self, *, empath=False, empathy=0):
        self._empath = empath
        self._empathy = empathy
        self.messages = []
        self.skill_uses = []

    def is_empath(self):
        return self._empath

    def msg(self, text):
        self.messages.append(str(text))

    def get_skill(self, skill_name):
        if skill_name == "empathy":
            return self._empathy
        return 0

    def use_skill(self, *args, **kwargs):
        self.skill_uses.append((args, kwargs))

    def search(self, *_args, **_kwargs):
        return None


class _DiagnoseTarget:
    def __init__(self):
        self.lines = ["Minor wounds."]

    def format_empath_diagnosis(self, precise=False):
        return list(self.lines)

    def get_empath_wounds(self):
        return {"head": 3, "arm": 2}


class _BodyTarget:
    def __init__(self):
        self.key = "patient"
        self.db = SimpleNamespace(is_study_item=False)

    def get_body_part(self, *_args, **_kwargs):
        return None


class _StudyAnatomyCommand:
    def __init__(self, caller, target):
        self.caller = caller
        self.args = target.key
        self._target = target

    def resolve_target(self, *_args, **_kwargs):
        return self._target, None, None, None, None

    def msg_target_matches(self, *_args, **_kwargs):
        raise AssertionError("should not be called")


class _DiagnoseCommand:
    def __init__(self, caller, target):
        self.caller = caller
        self.args = "target"
        self._target = target

    def resolve_target(self, *_args, **_kwargs):
        return self._target, None, None, None, None

    def msg_target_matches(self, *_args, **_kwargs):
        raise AssertionError("should not be called")


class EmpathyGatingTests(unittest.TestCase):
    def test_anatomy_study_item_does_not_award_empathy_to_non_empaths(self):
        character = _StudyCharacter(empath=False)
        item = _AnatomyStudyItem()

        Character.study_item(character, item)

        skills = [entry[0] for entry in character.awards]
        self.assertIn("scholarship", skills)
        self.assertIn("first_aid", skills)
        self.assertNotIn("empathy", skills)

    def test_anatomy_study_item_awards_empathy_to_empaths(self):
        character = _StudyCharacter(empath=True, empathy=10)
        item = _AnatomyStudyItem()

        Character.study_item(character, item)

        skills = [entry[0] for entry in character.awards]
        self.assertIn("empathy", skills)

    def test_anatomy_study_item_low_rank_empath_uses_failure_learning(self):
        character = _StudyCharacter(empath=True, empathy=0)
        item = _AnatomyStudyItem(difficulty=14)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            Character.study_item(character, item)

        helper.assert_called_once_with(
            character,
            "empathy",
            10,
            success=False,
            failure_reason="skill_too_low",
            event_key="empathy_study",
            failure_multiplier=0.25,
        )

    def test_study_anatomy_body_target_does_not_award_empathy_to_non_empaths(self):
        caller = _StudyCharacter(empath=False)
        command = _StudyAnatomyCommand(caller, _BodyTarget())

        CmdStudyAnatomy.func(command)

        skills = [entry[0] for entry in caller.awards]
        self.assertNotIn("empathy", skills)

    def test_diagnose_blocks_non_empaths(self):
        caller = _DiagnoseCaller(empath=False)
        target = _DiagnoseTarget()

        CmdDiagnose.func(_DiagnoseCommand(caller, target))

        self.assertEqual(caller.messages, ["You do not know how to diagnose injuries that way."])
        self.assertEqual(caller.skill_uses, [])

    def test_diagnose_allows_empaths(self):
        caller = _DiagnoseCaller(empath=True, empathy=20)
        target = _DiagnoseTarget()

        CmdDiagnose.func(_DiagnoseCommand(caller, target))

        self.assertIn("Minor wounds.", caller.messages)
        self.assertEqual(len(caller.skill_uses), 1)

    def test_diagnose_low_rank_empath_uses_failure_learning(self):
        caller = _DiagnoseCaller(empath=True, empathy=0)
        target = _DiagnoseTarget()

        with patch("commands.cmd_diagnose.attempt_with_failure_learning") as helper:
            CmdDiagnose.func(_DiagnoseCommand(caller, target))

        helper.assert_called_once_with(
            caller,
            "empathy",
            10,
            success=False,
            failure_reason="skill_too_low",
            event_key="diagnose",
            failure_multiplier=0.25,
        )
        self.assertEqual(caller.skill_uses, [])


if __name__ == "__main__":
    unittest.main()