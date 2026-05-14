import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from engine.services.guildhall_locator import _GUILDHALL_REGISTRY, get_guildhall_room_key, list_available_guildhalls, register_guildhall


class GuildhallLocatorTests(unittest.TestCase):
    def tearDown(self):
        _GUILDHALL_REGISTRY.pop("test_profession", None)

    def test_empath_guildhall_registered(self):
        self.assertEqual(get_guildhall_room_key("empath"), "Empath Guild")

    def test_cleric_guildhall_registered(self):
        self.assertEqual(get_guildhall_room_key("cleric"), "Cleric Guild")

    def test_ranger_guildhall_registered(self):
        self.assertEqual(get_guildhall_room_key("ranger"), "Ranger Guild")

    def test_unbuilt_professions_return_none(self):
        for profession in [
            "barbarian",
            "bard",
            "moon_mage",
            "necromancer",
            "paladin",
            "thief",
            "trader",
            "warrior",
            "warrior_mage",
        ]:
            self.assertIsNone(get_guildhall_room_key(profession))

    def test_unknown_profession_returns_none(self):
        self.assertIsNone(get_guildhall_room_key("nonexistent_profession"))

    def test_register_guildhall_adds_to_registry(self):
        register_guildhall("test_profession", "Test Guild")
        self.assertEqual(get_guildhall_room_key("test_profession"), "Test Guild")

    def test_list_available_guildhalls_returns_snapshot(self):
        available = list_available_guildhalls()
        self.assertIn("empath", available)
        self.assertIn("cleric", available)
        self.assertIn("ranger", available)
        self.assertGreaterEqual(len(available), 3)