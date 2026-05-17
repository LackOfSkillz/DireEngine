import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.area_forge.character_api import _get_status_list, get_character_payload
from world.professions.subsystems import RangerSubsystem


class _Room:
    def get_environment_type(self):
        return "wilderness"

    def get_terrain_type(self):
        return "forest"


class _Character:
    def __init__(self):
        self.key = "Tracker"
        self.db = SimpleNamespace(
            canonical_saf=-42,
            profession="ranger",
            guild="ranger",
            race="human",
            hp=100,
            max_hp=100,
            max_balance=100,
            balance=100,
            max_fatigue=100,
            fatigue=0,
            max_attunement=100,
            attunement=100,
            coins=0,
            in_combat=False,
            stance={"offense": 50, "defense": 50},
            equipment={},
        )
        self.location = _Room()
        self.contents = []
        self.account = None
        self.permissions = None

    def get_profession(self):
        return "ranger"

    def is_profession(self, name):
        return str(name or "").strip().lower() == "ranger"

    def get_race_display_name(self):
        return "Human"

    def get_profession_rank(self):
        return 1

    def get_ranger_instinct(self):
        return 11

    def get_nature_focus(self):
        return 23

    def get_ranger_terrain_type(self):
        return "forest"

    def get_ranger_companion(self):
        return {"state": "inactive", "bond": 0, "name": "wolf"}

    def get_wilderness_bond(self):
        return 42

    def get_wilderness_bond_state(self):
        return "distant"


class RangerIdentityMigrationTests(unittest.TestCase):
    def test_status_list_reports_saf_percent_for_rangers(self):
        character = _Character()

        statuses = _get_status_list(character)

        self.assertIn("SAF: 42%", statuses)
        self.assertNotIn("Bond: Distant", statuses)

    def test_character_payload_exports_saf_percent_and_compat_value(self):
        character = _Character()

        payload = get_character_payload(character)

        self.assertEqual(payload["ranger_saf_percent"], 42)
        self.assertEqual(payload["wilderness_bond"], 42)
        self.assertEqual(payload["nature_focus"], 23)

    def test_ranger_subsystem_reports_saf_percent(self):
        character = _Character()

        state = RangerSubsystem("ranger").get_state(character)

        self.assertEqual(state["saf_percent"], 42)
        self.assertEqual(state["wilderness_bond"], 42)
        self.assertEqual(state["bond_state"], "distant")


if __name__ == "__main__":
    unittest.main()
