import unittest
from unittest.mock import patch

from engine.bundles.builtin_skills import populate_skill_registry_fallback
from engine.bundles.skill_registry import skill_registry
from engine.services.pulse_service import PulseService


class DummySkill:
    def __init__(self, name):
        self.name = name


class DummySkillHandler:
    def __init__(self, skills):
        self.skills = skills


class DummyCharacter:
    def __init__(self, skills):
        self.exp_skills = DummySkillHandler(skills)


class PulseServiceTests(unittest.TestCase):
    def setUp(self):
        skill_registry.clear()
        populate_skill_registry_fallback(log=None)

    def tearDown(self):
        skill_registry.clear()

    def test_process_skill_pulse_respects_registry_pulse_group(self):
        character = DummyCharacter({"stealth": DummySkill("stealth"), "athletics": DummySkill("athletics")})
        with patch("engine.services.pulse_service.is_active", return_value=True), patch("engine.services.pulse_service.pulse") as pulse_mock:
            processed = PulseService.process_skill_pulse(character, global_tick=120, skill_group_offsets={120: 120, 100: 100})
        self.assertEqual(processed, 1)
        pulse_mock.assert_called_once_with(character.exp_skills.skills["stealth"])

    def test_process_skill_pulse_defaults_unknown_skill_to_base_group(self):
        character = DummyCharacter({"unknown_7": DummySkill("unknown_7")})
        with patch("engine.services.pulse_service.is_active", return_value=True), patch("engine.services.pulse_service.pulse") as pulse_mock:
            processed = PulseService.process_skill_pulse(character, global_tick=100, skill_group_offsets={100: 100})
        self.assertEqual(processed, 1)
        pulse_mock.assert_called_once_with(character.exp_skills.skills["unknown_7"])


if __name__ == "__main__":
    unittest.main()