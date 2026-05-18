import json
import os
import tempfile
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from world.areas.the_crossing import import_canonical


def _sample_room(room_id, title, description, paths, wayto, tags=None):
    return {
        "id": room_id,
        "title": [f"[[The Crossing, {title}]]"],
        "description": [description],
        "paths": [paths],
        "wayto": wayto,
        "timeto": {destination: 1 for destination in wayto},
        "image": "zoluren-1-crossing-1377284934.png",
        "image_coords": [0, 0, 1, 1],
        "tags": list(tags or []),
    }


class CanonicalCrossingPhase1Tests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        failures = safe_smoke_delete(*self.created)
        self.assertEqual(failures, [])

    def _write_map(self, rooms):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(rooms, handle)
        handle.close()
        self.addCleanup(lambda: os.path.exists(handle.name) and os.remove(handle.name))
        return handle.name

    def test_load_map_rejects_non_list_root(self):
        path = self._write_map({"bad": True})

        with self.assertRaises(ValueError):
            import_canonical.load_canonical_crossing_map(path)

    def test_ensure_phase1_builds_metadata_and_skips_pending_exits(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Canonical text north.", "Obvious paths: north, east.", {"787": "north", "794": "east", "6871": "go pond"}, ["tgn"]),
                _sample_room(794, "Town Green Northeast", "Canonical text northeast.", "Obvious paths: south, west.", {"788": "west", "793": "south"}, ["tgne"]),
                _sample_room(793, "Town Green Southeast", "Canonical text southeast.", "Obvious paths: north, west.", {"788": "northwest", "794": "north"}, ["tgse"]),
                _sample_room(6871, "Town Green Pond", "Canonical text pond.", "Obvious paths: out.", {"788": "out"}, ["pond"]),
            ]
        )
        legacy = create_object("typeclasses.rooms.Room", key="Bellfound Steps", nohome=True)
        legacy.db.area = "New Landing"
        self.created.append(legacy)

        rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788, 794, 793, 6871])

        north = rooms[788]
        self.assertEqual(north.key, "Town Green North")
        self.assertTrue(north.db.is_canonical_crossing)
        self.assertEqual(north.db.canonical_map_id, 788)
        self.assertEqual(north.db.canonical_title, "Town Green North")
        self.assertEqual(north.db.canonical_paths, "Obvious paths: north, east.")
        self.assertNotEqual(north.db.desc, "Canonical text north.")
        self.assertEqual(north.db.pending_canonical_exits, [{"destination_id": 787, "command": "north"}])
        exit_keys = sorted(obj.key for obj in north.contents if getattr(obj, "destination", None) is not None)
        self.assertIn("east", exit_keys)
        self.assertIn("pond", exit_keys)
        self.assertTrue(bool(getattr(legacy.db, "deprecated_area", False)))

    def test_ensure_phase1_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Canonical text north.", "Obvious paths: east.", {"794": "east"}),
                _sample_room(794, "Town Green Northeast", "Canonical text northeast.", "Obvious paths: west.", {"788": "west"}),
            ]
        )

        first = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788, 794])
        second = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788, 794])

        self.assertEqual(first[788].id, second[788].id)
        exits = [obj for obj in first[788].contents if getattr(obj, "destination", None) == first[794]]
        self.assertEqual(len(exits), 1)


if __name__ == "__main__":
    unittest.main()