import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.rooms import Room
from world.areas.crossing.ranger_guild import build


class CrossingRangerGuildBuildTests(unittest.TestCase):
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
        cleanup_keys = [spec["key"] for spec in build.ROOM_SPECS.values()] + ["Kalika"]
        for obj in list(ObjectDB.objects.filter(db_key__in=cleanup_keys)):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def test_ensure_creates_kalika_and_lane_access(self):
        rooms = build.ensure_crossing_ranger_guildhall()

        main_hall = rooms["main_hall"]
        self.assertEqual(main_hall.key, "Ranger Guild")
        self.assertTrue(main_hall.tags.has(build.CANONICAL_TAG))
        self.assertTrue(main_hall.tags.has(build.JOIN_SITE_TAG))

        lane_exit = next(obj for obj in self.lane.contents if getattr(obj, "destination", None) == main_hall)
        self.assertEqual(lane_exit.key, "guild")

        kalika = next(obj for obj in main_hall.contents if getattr(obj, "key", "") == "Kalika")
        self.assertEqual(getattr(kalika.db, "trains_profession", None), "ranger")
        self.assertEqual(getattr(kalika.db, "guild_role", None), "guildmaster")

    def test_ensure_is_idempotent_for_room_and_kalika(self):
        first_rooms = build.ensure_crossing_ranger_guildhall()
        second_rooms = build.ensure_crossing_ranger_guildhall()

        self.assertEqual(first_rooms["main_hall"].id, second_rooms["main_hall"].id)

        kalikas = [
            obj for obj in list(second_rooms["main_hall"].contents or [])
            if getattr(obj, "key", "") == "Kalika"
        ]
        self.assertEqual(len(kalikas), 1)

    def test_join_profession_clears_ranger_saf_on_commitment(self):
        rooms = build.ensure_crossing_ranger_guildhall()
        character = self._create(
            "typeclasses.characters.Character",
            f"Ranger Join Test {int(time.time() * 1000)}",
            location=rooms["main_hall"],
            home=rooms["main_hall"],
        )
        character.ensure_core_defaults()
        character.ensure_stat_defaults()
        stats = dict(character.db.stats or {})
        stats.update({
            "strength": 8,
            "stamina": 8,
            "agility": 8,
            "reflex": 7,
            "intelligence": 7,
            "charisma": 6,
            "wisdom": 6,
        })
        character.db.stats = stats
        character.db.canonical_saf = -50

        ok, _message = character.join_profession("ranger")

        self.assertTrue(ok)
        self.assertEqual(character.get_profession(), "ranger")
        self.assertEqual(getattr(character.db, "canonical_saf", None), 0)