import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from typeclasses.rooms import Room
from world.areas.crossing.barbarian_guild import build as guild_build
from world.areas.crossing.barbarian_pits import build


class CrossingBarbarianPitsBuildTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.original_lane_dbref = guild_build.LANE_DBREF
        self.original_lane_key = guild_build.LANE_KEY
        self.lane = self._create(Room, f"Cedarcoil Lane, East Reach {int(time.time() * 1000)}")
        guild_build.LANE_DBREF = self.lane.id
        guild_build.LANE_KEY = self.lane.key

    def tearDown(self):
        guild_build.LANE_DBREF = self.original_lane_dbref
        guild_build.LANE_KEY = self.original_lane_key
        cleanup_keys = [spec["key"] for spec in guild_build.ROOM_SPECS.values()]
        cleanup_keys += [spec["key"] for spec in build.PIT_ROOM_SPECS.values()]
        cleanup_keys += ["T'Kiel", *[spec["pit_master"] for spec in build.PIT_ROOM_SPECS.values()]]
        failures = safe_smoke_delete(*self.created, *list(ObjectDB.objects.filter(db_key__in=cleanup_keys)))
        self.assertEqual(failures, [])

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def test_ensure_creates_eight_pits_and_masters(self):
        rooms = build.ensure_crossing_barbarian_pits()
        guild_rooms = guild_build.ensure_crossing_barbarian_guildhall()

        self.assertEqual(len(rooms), 8)
        first_room = rooms["swan"]
        pits_exit = next(obj for obj in guild_rooms["training_floor"].contents if getattr(obj, "destination", None) == first_room)
        self.assertEqual(pits_exit.key, "pits")
        for dance_name, room in rooms.items():
            with self.subTest(dance=dance_name):
                self.assertEqual(int(getattr(room.db, "canonical_room_id", 0) or 0), int(build.PIT_ROOM_SPECS[dance_name]["canonical_room_id"]))
                master = next(obj for obj in room.contents if getattr(obj, "db_typeclass_path", "") == build.PIT_MASTER_TYPECLASS)
                self.assertEqual(getattr(master.db, "teaches_dance", None), dance_name)

    def test_ensure_is_idempotent_for_rooms_and_masters(self):
        first = build.ensure_crossing_barbarian_pits()
        second = build.ensure_crossing_barbarian_pits()

        self.assertEqual(first["dragon"].id, second["dragon"].id)
        for dance_name, room in second.items():
            with self.subTest(dance=dance_name):
                masters = [obj for obj in room.contents if getattr(obj, "db_typeclass_path", "") == build.PIT_MASTER_TYPECLASS]
                self.assertEqual(len(masters), 1)


if __name__ == "__main__":
    unittest.main()