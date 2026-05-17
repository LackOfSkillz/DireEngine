import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from tests.fixtures.orphan_helpers import count_orphan_attributes
from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from typeclasses.characters import Character
from typeclasses.objects import Object
from typeclasses.rooms import Room
from world.areas.crossing.ranger_guild import build


class SafeSmokeDeleteInvariantTests(unittest.TestCase):
    def test_nested_room_with_exits_invariant(self):
        before = count_orphan_attributes()
        stamp = int(time.time() * 1000)
        room = create_object(Room, key=f"Invariant Room {stamp}", nohome=True)
        target = create_object(Room, key=f"Invariant Target {stamp}", nohome=True)
        for index in range(4):
            create_object("typeclasses.exits.Exit", key=f"Invariant Exit {index} {stamp}", location=room, destination=target, nohome=True)
        for index in range(2):
            create_object(Object, key=f"Invariant Item {index} {stamp}", location=room, home=room)

        safe_smoke_delete(room, target)

        after = count_orphan_attributes()
        self.assertEqual(after, before, f"Nested room cleanup leaked {after - before} orphan attributes")

    def test_ranger_guild_build_invariant(self):
        before = count_orphan_attributes()
        stamp = int(time.time() * 1000)
        original_lane_dbref = build.LANE_DBREF
        original_lane_key = build.LANE_KEY
        lane = create_object(Room, key=f"Cracked Bell Alley, East Reach {stamp}", nohome=True)
        build.LANE_DBREF = lane.id
        build.LANE_KEY = lane.key
        try:
            rooms = build.ensure_crossing_ranger_guildhall()
            tracked = [lane, *list(rooms.values()), *list(ObjectDB.objects.filter(db_key="Kalika"))]
            safe_smoke_delete(*tracked)
        finally:
            build.LANE_DBREF = original_lane_dbref
            build.LANE_KEY = original_lane_key

        after = count_orphan_attributes()
        self.assertEqual(after, before, f"Ranger guild build leaked {after - before} orphan attributes")

    def test_ranger_companion_invariant(self):
        before = count_orphan_attributes()
        stamp = int(time.time() * 1000)
        room = create_object(Room, key=f"Invariant Wilds {stamp}", nohome=True)
        room.set_environment_type("wilderness")
        room.set_terrain_type("forest")
        ranger = create_object(Character, key=f"Invariant Ranger {stamp}", location=room, home=room)
        ranger.ensure_core_defaults()
        ranger.ensure_stat_defaults()
        ranger.db.profession = "ranger"
        create_object(Object, key=f"Invariant Corn {stamp}", location=ranger, home=ranger)
        ok, message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok, message)

        safe_smoke_delete(room)

        after = count_orphan_attributes()
        self.assertEqual(after, before, f"Ranger companion cleanup leaked {after - before} orphan attributes")