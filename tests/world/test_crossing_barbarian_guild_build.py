import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.rooms import Room
from world.areas.crossing.barbarian_guild import build


class CrossingBarbarianGuildBuildTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.original_lane_dbref = build.LANE_DBREF
        self.original_lane_key = build.LANE_KEY
        self.lane = self._create(Room, build.LANE_KEY)
        build.LANE_DBREF = self.lane.id
        build.LANE_KEY = self.lane.key

    def tearDown(self):
        build.LANE_DBREF = self.original_lane_dbref
        build.LANE_KEY = self.original_lane_key
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass
        cleanup_keys = [spec["key"] for spec in build.ROOM_SPECS.values()] + ["T'Kiel"]
        for obj in list(ObjectDB.objects.filter(db_key__in=cleanup_keys)):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def _create_character(self, key, room):
        character = self._create(
            "typeclasses.characters.Character",
            key,
            location=room,
            home=room,
        )
        character.ensure_core_defaults()
        character.ensure_stat_defaults()
        return character

    def test_ensure_creates_tkiel_and_lane_access(self):
        rooms = build.ensure_crossing_barbarian_guildhall()

        main_hall = rooms["main_hall"]
        self.assertEqual(main_hall.key, "Barbarian Guild")
        self.assertTrue(main_hall.tags.has(build.CANONICAL_TAG))
        self.assertTrue(main_hall.tags.has(build.JOIN_SITE_TAG))

        lane_exit = next(obj for obj in self.lane.contents if getattr(obj, "destination", None) == main_hall)
        self.assertEqual(lane_exit.key, "guild")

        tkiel = next(obj for obj in main_hall.contents if getattr(obj, "key", "") == "T'Kiel")
        self.assertEqual(getattr(tkiel.db, "trains_profession", None), "barbarian")
        self.assertEqual(getattr(tkiel.db, "guild_role", None), "guildmaster")
        self.assertEqual(getattr(tkiel.db, "profession_id", None), 1)
        self.assertEqual(getattr(tkiel.db, "gender", None), "female")

    def test_ensure_is_idempotent_for_room_and_tkiel(self):
        first_rooms = build.ensure_crossing_barbarian_guildhall()
        second_rooms = build.ensure_crossing_barbarian_guildhall()

        self.assertEqual(first_rooms["main_hall"].id, second_rooms["main_hall"].id)
        tkiels = [obj for obj in list(second_rooms["main_hall"].contents or []) if getattr(obj, "key", "") == "T'Kiel"]
        self.assertEqual(len(tkiels), 1)

    def test_guild_speech_matches_canonical_excerpt(self):
        rooms = build.ensure_crossing_barbarian_guildhall()
        tkiel = next(obj for obj in rooms["main_hall"].contents if getattr(obj, "key", "") == "T'Kiel")

        speech = tkiel.get_guild_speech()

        self.assertIn("The Barbarian Guild has a simple task -- to turn soft and tender would-be adventurers into hard and dangerous warriors.", speech)
        self.assertIn("Steel and iron, speed and strength...these are our tools.", speech)
        self.assertIn("No fancy spells, no calling on the Gods for help.", speech)

    def test_join_profession_clears_barbarian_saf_on_commitment(self):
        rooms = build.ensure_crossing_barbarian_guildhall()
        character = self._create_character(f"Barbarian Join Test {int(time.time() * 1000)}", rooms["main_hall"])
        character.db.canonical_saf = 50

        ok, _message = character.join_profession("barbarian")

        self.assertTrue(ok)
        self.assertEqual(character.get_profession(), "barbarian")
        self.assertEqual(getattr(character.db, "canonical_saf", None), 0)

    def test_join_handler_routes_through_character_join(self):
        rooms = build.ensure_crossing_barbarian_guildhall()
        tkiel = next(obj for obj in rooms["main_hall"].contents if getattr(obj, "key", "") == "T'Kiel")
        character = self._create_character(f"Barbarian Handler Test {int(time.time() * 1000)}", rooms["main_hall"])
        character.db.canonical_saf = 80

        ok, _message = tkiel.join_handler(character)

        self.assertTrue(ok)
        self.assertEqual(character.get_profession(), "barbarian")
        self.assertEqual(getattr(character.db, "canonical_saf", None), 0)

    def test_magic_inquiry_ejects_off_class_actor(self):
        rooms = build.ensure_crossing_barbarian_guildhall()
        tkiel = next(obj for obj in rooms["main_hall"].contents if getattr(obj, "key", "") == "T'Kiel")
        actor = self._create_character(f"Cleric Visit {int(time.time() * 1000)}", rooms["main_hall"])
        actor.set_profession("cleric")

        response = tkiel.handle_inquiry(actor, "magic")

        self.assertIn("Magic?! Barbarians don't need no stinkin' magic!!", response)
        self.assertEqual(actor.location, self.lane)

    def test_cross_class_commit_refusal_blocks_existing_profession(self):
        rooms = build.ensure_crossing_barbarian_guildhall()
        actor = self._create_character(f"Cleric Join Refusal {int(time.time() * 1000)}", rooms["main_hall"])
        actor.set_profession("cleric")

        ok, message = actor.join_profession("barbarian")

        self.assertFalse(ok)
        self.assertIn("already chose a profession", message)
        self.assertEqual(actor.get_profession(), "cleric")

    def test_guildhall_locator_registers_barbarian(self):
        from engine.services.guildhall_locator import get_guildhall_room_key

        self.assertEqual(get_guildhall_room_key("barbarian"), "Barbarian Guild")


if __name__ == "__main__":
    unittest.main()