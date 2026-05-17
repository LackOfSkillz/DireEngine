import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object
from evennia.utils.search import search_object

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from typeclasses.characters import Character
from typeclasses.npcs import RangerCompanion
from typeclasses.rooms import Room
from world.systems.ranger.companion import RACCOON_COMPANION_TYPE, WOLF_COMPANION_TYPE, validate_companion_type


class RangerCompanionTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        stamp = int(time.time() * 1000)
        self.wild_room = self._create(Room, f"Companion Wilds {stamp}")
        self.wild_room.set_environment_type("wilderness")
        self.wild_room.set_terrain_type("forest")
        self.city_room = self._create(Room, f"Companion City {stamp}")
        self.city_room.set_environment_type("urban")
        self.city_room.set_terrain_type("urban")

    def tearDown(self):
        safe_smoke_delete(*self.created)

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def _create_character(self, key, *, profession, location):
        character = self._create(Character, key, location=location, home=location)
        character.ensure_core_defaults()
        character.ensure_stat_defaults()
        character.db.profession = profession
        return character

    def test_type_registry_enforces_gap4(self):
        self.assertEqual(validate_companion_type("wolf"), WOLF_COMPANION_TYPE)
        self.assertEqual(validate_companion_type("raccoon"), RACCOON_COMPANION_TYPE)
        with self.assertRaises(ValueError):
            validate_companion_type("cat")

    def test_constructor_rejects_invalid_species(self):
        with self.assertRaises(ValueError):
            RangerCompanion(species="cat")

    def test_summon_wolf_creates_entity_and_owner_link(self):
        ranger = self._create_character("Companion Ranger Wolf", profession="ranger", location=self.wild_room)

        ok, message = ranger.call_ranger_companion(species="wolf")

        self.assertTrue(ok)
        self.assertIn("wolf", message.lower())
        companion = ranger.get_ranger_companion_entity()
        self.assertIsNotNone(companion)
        self.assertEqual(companion.location, self.wild_room)
        self.assertEqual(companion.db.owner_id, ranger.id)
        self.assertEqual(companion.db.companion_type_id, WOLF_COMPANION_TYPE)
        record = ranger.get_ranger_companion()
        self.assertEqual(record["entity_id"], companion.id)
        self.assertEqual(record["type"], "wolf")
        self.assertEqual(record["state"], "present")

    def test_summon_raccoon_creates_entity_and_owner_link(self):
        ranger = self._create_character("Companion Ranger Raccoon", profession="ranger", location=self.wild_room)

        ok, message = ranger.call_ranger_companion(species="raccoon")

        self.assertTrue(ok)
        self.assertIn("raccoon", message.lower())
        companion = ranger.get_ranger_companion_entity()
        self.assertIsNotNone(companion)
        self.assertEqual(companion.db.companion_type_id, RACCOON_COMPANION_TYPE)
        self.assertEqual(ranger.get_ranger_companion()["type_id"], RACCOON_COMPANION_TYPE)

    def test_invalid_species_is_rejected_at_summon_entry(self):
        ranger = self._create_character("Companion Ranger Reject", profession="ranger", location=self.wild_room)

        ok, message = ranger.call_ranger_companion(species="cat")

        self.assertFalse(ok)
        self.assertIn("raccoon or wolf", message.lower())
        self.assertIsNone(ranger.get_ranger_companion_entity())

    def test_dismiss_removes_entity_and_clears_active_link(self):
        ranger = self._create_character("Companion Ranger Dismiss", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()
        self.assertIsNotNone(companion)
        companion_id = companion.id

        ok, message = ranger.dismiss_ranger_companion()

        self.assertTrue(ok)
        self.assertIn("wolf", message.lower())
        self.assertFalse(search_object(f"#{companion_id}"))
        self.assertIsNone(ranger.get_ranger_companion_entity())
        record = ranger.get_ranger_companion()
        self.assertEqual(record["state"], "dismissed")
        self.assertIsNone(record["entity_id"])

    def test_companion_record_survives_owner_room_move(self):
        ranger = self._create_character("Companion Ranger Move", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        ranger.move_to(self.city_room, quiet=True, move_type="walk")

        record = ranger.get_ranger_companion()
        self.assertEqual(record["entity_id"], companion.id)
        self.assertEqual(record["state"], "present")
        self.assertEqual(ranger.get_ranger_companion_entity().id, companion.id)

    def test_persisted_entity_id_rehydrates_live_record(self):
        ranger = self._create_character("Companion Ranger Persist", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()
        ranger.db.ranger_companion = {
            "type_id": WOLF_COMPANION_TYPE,
            "state": "present",
            "bond": 57,
            "entity_id": companion.id,
        }

        record = ranger.get_ranger_companion()

        self.assertEqual(record["entity_id"], companion.id)
        self.assertEqual(record["owner_id"], ranger.id)
        self.assertEqual(record["type"], "wolf")

    def test_off_class_summon_refusal(self):
        cleric = self._create_character("Companion Cleric Reject", profession="cleric", location=self.wild_room)

        ok, message = cleric.call_ranger_companion(species="wolf")

        self.assertFalse(ok)
        self.assertIn("no bond", message.lower())
        self.assertIsNone(cleric.get_ranger_companion_entity())