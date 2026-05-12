import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_mark import CmdMark
from typeclasses.abilities_perception import ObserveAbility, SearchAbility
from typeclasses.characters import Character


class _DummyTrap:
    def __init__(self, concealment, *, owner=None, active=True):
        self.db = SimpleNamespace(is_trap_device=True, concealment=concealment, owner=owner)
        self.detected_by = []
        self._active = active

    def is_active(self):
        return self._active

    def remember_detection(self, user):
        self.detected_by.append(user)


class _DummyHiddenObserver:
    def __init__(self, *, key="lurker", defense_total=20, hidden=True):
        self.key = key
        self._defense_total = defense_total
        self._hidden = hidden
        self.broken = False

    def is_hidden(self):
        return self._hidden

    def get_stealth_total(self):
        return self._defense_total

    def get_hidden_strength(self):
        return 0

    def break_stealth(self):
        self.broken = True


class _PerceptionCharacter:
    def __init__(self, *, perception=0, wisdom=0, location=None):
        self._perception = perception
        self._wisdom = wisdom
        self.location = location
        self.messages = []
        self.skill_uses = []
        self.awareness = None
        self.states = {}
        self.key = "Scout"

    def get_skill(self, skill_name):
        return self._perception if skill_name == "perception" else 0

    def get_stat(self, stat_name):
        return self._wisdom if stat_name == "wisdom" else 0

    def msg(self, text):
        self.messages.append(str(text))

    def use_skill(self, *args, **kwargs):
        self.skill_uses.append((args, kwargs))

    def set_awareness(self, value):
        self.awareness = value

    def set_state(self, key, value):
        self.states[key] = value

    def get_room_observers(self):
        return []

    def get_perception_total(self):
        return self._perception + self._wisdom

    def detect_traps_in_room(self):
        return []


class _DummyTarget:
    def __init__(self, key="mark target", target_id=99, *, location=None, perception_rank=20):
        self.key = key
        self.id = target_id
        self.location = location
        self.db = SimpleNamespace(theft_memory={}, attention_state="idle")
        self._perception_rank = perception_rank

    def get_skill_rank(self, skill_name):
        if skill_name == "perception":
            return self._perception_rank
        return 0


class _MarkCaller:
    def __init__(self, *, perception=0, location=None):
        self._perception = perception
        self.location = location
        self.db = SimpleNamespace()
        self.id = 7
        self.messages = []

    def msg(self, text):
        self.messages.append(str(text))

    def is_profession(self, key):
        return False

    def get_skill(self, skill_name):
        return self._perception if skill_name == "perception" else 0

    def search(self, *_args, **_kwargs):
        return None


class _DummyMarkCommand:
    def __init__(self, caller, target):
        self.caller = caller
        self.args = target.key
        self._target = target

    def resolve_target(self, *_args, **_kwargs):
        return self._target, None, None, None, None

    def msg_target_matches(self, *_args, **_kwargs):
        raise AssertionError("should not be called")


class PerceptionFailureLearningTests(unittest.TestCase):
    def test_detect_traps_success_uses_normal_skill_award(self):
        trap = _DummyTrap(8)
        room = SimpleNamespace(contents=[trap])
        character = _PerceptionCharacter(perception=6, wisdom=5, location=room)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            detected = Character.detect_traps_in_room(character)

        self.assertEqual(detected, [trap])
        helper.assert_not_called()
        self.assertEqual(len(character.skill_uses), 1)

    def test_detect_traps_low_rank_failure_uses_helper(self):
        trap = _DummyTrap(15)
        room = SimpleNamespace(contents=[trap])
        character = _PerceptionCharacter(perception=5, wisdom=5, location=room)

        with patch("typeclasses.characters.attempt_with_failure_learning") as helper:
            detected = Character.detect_traps_in_room(character)

        self.assertEqual(detected, [])
        helper.assert_called_once_with(
            character,
            "perception",
            15,
            success=False,
            failure_reason="skill_too_low",
            event_key="detect_traps",
            failure_multiplier=0.25,
        )

    def test_search_low_rank_failure_uses_helper(self):
        observer = _DummyHiddenObserver(defense_total=18)
        user = _PerceptionCharacter(perception=0, wisdom=0)
        user.get_room_observers = lambda: [observer]

        with patch("typeclasses.abilities_perception.run_contest", return_value={"outcome": "failure"}), patch(
            "typeclasses.abilities_perception.attempt_with_failure_learning"
        ) as helper, patch("typeclasses.abilities_perception.msg_actor"), patch("typeclasses.abilities_perception.react_or_message_target"), patch(
            "typeclasses.abilities_perception.msg_room"
        ):
            SearchAbility().execute(user)

        helper.assert_called_once_with(
            user,
            "perception",
            18,
            success=False,
            failure_reason="skill_too_low",
            event_key="search",
            failure_multiplier=0.25,
        )

    def test_observe_low_rank_failure_uses_helper(self):
        user = _PerceptionCharacter(perception=0, wisdom=0)

        with patch("typeclasses.abilities_perception.attempt_with_failure_learning") as helper, patch(
            "typeclasses.abilities_perception.msg_actor"
        ), patch("typeclasses.abilities_perception.msg_room"), patch("typeclasses.abilities_perception.schedule_event"):
            ObserveAbility().execute(user)

        helper.assert_called_once_with(
            user,
            "perception",
            10,
            success=False,
            failure_reason="skill_too_low",
            event_key="observe",
            failure_multiplier=0.25,
        )

    def test_mark_low_rank_failure_uses_helper(self):
        location = object()
        caller = _MarkCaller(perception=0, location=location)
        target = _DummyTarget(location=location, perception_rank=18)
        command = _DummyMarkCommand(caller, target)

        with patch("commands.cmd_mark.attempt_with_failure_learning") as helper, patch(
            "commands.cmd_mark.SkillService.award_xp"
        ) as award_xp, patch("commands.cmd_mark.record_mark_attempt"), patch("commands.cmd_mark.random.randint", return_value=33):
            CmdMark.func(command)

        award_xp.assert_called_once()
        helper.assert_called_once_with(
            caller,
            "perception",
            13,
            success=False,
            failure_reason="skill_too_low",
            event_key="mark",
            failure_multiplier=0.25,
        )


if __name__ == "__main__":
    unittest.main()