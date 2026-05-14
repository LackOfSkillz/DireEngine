import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.learning.tdp_cost import tdp_cost_for_character, tdp_cost_to_project, tdp_cost_to_raise
from world.races.utils import get_racial_tdp_modifier


class TdpCostTests(unittest.TestCase):
    def test_cost_to_raise_human_strength_21_to_22(self):
        self.assertEqual(tdp_cost_to_raise(21, 0), 63)

    def test_cost_to_raise_volgrin_strength_21_to_22(self):
        self.assertEqual(tdp_cost_to_raise(21, -3), 33)

    def test_cost_to_raise_zero_current_returns_zero(self):
        self.assertEqual(tdp_cost_to_raise(0, 0), 0)
        self.assertEqual(tdp_cost_to_raise(0, -3), 0)
        self.assertEqual(tdp_cost_to_raise(0, 3), 0)

    def test_cost_to_raise_clamps_negative_cost_to_zero(self):
        self.assertEqual(tdp_cost_to_raise(2, -10), 0)

    def test_cost_to_project_human_60_to_75(self):
        self.assertEqual(tdp_cost_to_project(60, 75, 0), 3015)

    def test_cost_to_project_volgrin_60_to_75(self):
        self.assertEqual(tdp_cost_to_project(60, 75, -3), 1518)

    def test_cost_to_project_zero_when_target_not_higher(self):
        self.assertEqual(tdp_cost_to_project(50, 50, 0), 0)
        self.assertEqual(tdp_cost_to_project(50, 40, 0), 0)

    def test_racial_modifier_lookup_all_11_races_all_8_stats(self):
        races = [
            "human",
            "dwarf",
            "elf",
            "gnome",
            "halfling",
            "volgrin",
            "saurathi",
            "valran",
            "aethari",
            "felari",
            "lunari",
        ]
        stats = [
            "strength",
            "stamina",
            "agility",
            "reflex",
            "charisma",
            "discipline",
            "wisdom",
            "intelligence",
        ]
        for race in races:
            for stat in stats:
                mod = get_racial_tdp_modifier(race, stat)
                self.assertIsInstance(mod, int)
                self.assertGreaterEqual(mod, -3)
                self.assertLessEqual(mod, 3)

    def test_racial_modifier_unknown_race_returns_zero(self):
        self.assertEqual(get_racial_tdp_modifier("dragon", "strength"), 0)

    def test_racial_modifier_unknown_stat_returns_zero(self):
        self.assertEqual(get_racial_tdp_modifier("human", "luck"), 0)

    def test_human_baseline_is_balanced(self):
        for stat in [
            "strength",
            "stamina",
            "agility",
            "reflex",
            "charisma",
            "discipline",
            "wisdom",
            "intelligence",
        ]:
            self.assertEqual(get_racial_tdp_modifier("human", stat), 0)

    def test_cost_for_character_uses_race_and_stat(self):
        character = SimpleNamespace(
            db=SimpleNamespace(
                race="volgrin",
                stats={"strength": 21},
            )
        )
        self.assertEqual(tdp_cost_for_character(character, "strength"), 33)
