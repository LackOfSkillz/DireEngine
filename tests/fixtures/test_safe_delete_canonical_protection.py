import os
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from tools.diretest.core.harness import _is_canonical_room
from tools.diretest.core.harness import safe_delete
from typeclasses.objects import Object
from typeclasses.rooms import Room
from world.areas.the_crossing import import_canonical


class SafeDeleteCanonicalProtectionTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        for obj in self.created:
            if not ObjectDB.objects.filter(id=getattr(obj, "id", 0)).exists():
                continue
            if hasattr(getattr(obj, "db", None), "canonical_map_id"):
                obj.db.canonical_map_id = None
                obj.db.canonical_phase = None
                obj.db.canonical_source = None
            safe_smoke_delete(obj)

    def _create_room(self, key, *, canonical_map_id=None, canonical_phase=None, canonical_source=None):
        room = create_object(Room, key=key, nohome=True)
        room.db.canonical_map_id = canonical_map_id
        room.db.canonical_phase = canonical_phase
        room.db.canonical_source = canonical_source
        self.created.append(room)
        return room

    def _create_exit(self, key, location, destination):
        exit_obj = create_object("typeclasses.exits.Exit", key=key, location=location, destination=destination, nohome=True)
        self.created.append(exit_obj)
        return exit_obj

    def test_safe_delete_refuses_canonical_room(self):
        room = self._create_room("Canonical Direct Guard", canonical_map_id=900001, canonical_phase="probe")

        with patch("tools.diretest.core.harness.logger.log_warn") as mock_warn:
            ok, failure = safe_delete(room)

        self.assertTrue(ok)
        self.assertIsNone(failure)
        self.assertTrue(ObjectDB.objects.filter(id=room.id).exists())
        self.assertIn("canonical_map_id=900001", mock_warn.call_args[0][0])

    def test_safe_smoke_delete_filters_canonical_room(self):
        room = self._create_room("Canonical Wrapper Guard", canonical_map_id=900002, canonical_phase="probe")

        with patch("tools.diretest.core.harness.logger.log_warn") as mock_warn:
            failures = safe_smoke_delete(room)

        self.assertEqual(failures, [])
        self.assertEqual(failures.deleted_count, 0)
        self.assertEqual(failures.filtered_count, 1)
        self.assertTrue(ObjectDB.objects.filter(id=room.id).exists())
        self.assertIn("canonical_map_id=900002", mock_warn.call_args[0][0])

    def test_neighbor_cleanup_does_not_delete_adjacent_canonical_room(self):
        canonical = self._create_room("Canonical Neighbor", canonical_map_id=900003, canonical_phase="probe")
        source = self._create_room("Regular Source")
        target = self._create_room("Regular Target")
        self._create_exit("to canonical", source, canonical)
        self._create_exit("to target", canonical, target)

        ok, failure = safe_delete(source)

        self.assertTrue(ok)
        self.assertIsNone(failure)
        self.assertTrue(ObjectDB.objects.filter(id=canonical.id).exists())
        self.assertFalse(ObjectDB.objects.filter(id=source.id).exists())

    def test_safe_smoke_delete_skips_canonical_and_deletes_regular_rooms(self):
        canonical_one = self._create_room("Canonical One", canonical_map_id=900004, canonical_phase="probe")
        regular = self._create_room("Regular Room")
        canonical_two = self._create_room("Canonical Two", canonical_map_id=900005, canonical_source="probe")

        failures = safe_smoke_delete(canonical_one, regular, canonical_two)

        self.assertEqual(failures, [])
        self.assertEqual(failures.deleted_count, 1)
        self.assertEqual(failures.filtered_count, 2)
        self.assertTrue(ObjectDB.objects.filter(id=canonical_one.id).exists())
        self.assertFalse(ObjectDB.objects.filter(id=regular.id).exists())
        self.assertTrue(ObjectDB.objects.filter(id=canonical_two.id).exists())

    def test_real_importer_output_survives_safe_smoke_delete(self):
        first = import_canonical.ensure_canonical_crossing_phase1(map_path=import_canonical.DEFAULT_MAP_PATH, room_ids=[788, 794])
        before_ids = sorted(room.id for room in first.values())
        before_count = ObjectDB.objects.filter(id__in=before_ids).count()

        failures = safe_smoke_delete(*first.values())
        second = import_canonical.ensure_canonical_crossing_phase1(map_path=import_canonical.DEFAULT_MAP_PATH, room_ids=[788, 794])
        after_ids = sorted(room.id for room in second.values())
        after_count = ObjectDB.objects.filter(id__in=after_ids).count()

        self.assertEqual(failures, [])
        self.assertEqual(failures.deleted_count, 0)
        self.assertEqual(failures.filtered_count, len(first))
        self.assertEqual(after_count, before_count)
        self.assertEqual(after_ids, before_ids)

    def test_is_canonical_room_matches_marker_presence(self):
        canonical = self._create_room("Canonical Marker", canonical_map_id=900006)
        regular = self._create_room("Regular Marker")
        obj = create_object(Object, key="Marker Object")
        self.created.append(obj)

        self.assertTrue(_is_canonical_room(canonical))
        self.assertFalse(_is_canonical_room(regular))
        self.assertFalse(_is_canonical_room(obj))
        self.assertFalse(_is_canonical_room(object()))


if __name__ == "__main__":
    unittest.main()