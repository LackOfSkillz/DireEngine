import json
import os
import tempfile
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from world.areas.the_crossing import import_canonical


def _sample_room(room_id, title, description, paths, wayto, tags=None, area_prefix="The Crossing"):
    return {
        "id": room_id,
        "title": [f"[[{area_prefix}, {title}]]"],
        "description": [description],
        "paths": [paths],
        "wayto": wayto,
        "timeto": {destination: 1 for destination in wayto},
        "image": "zoluren-1-crossing-1377284934.png",
        "image_coords": [0, 0, 1, 1],
        "tags": list(tags or []),
    }


class CanonicalCrossingPhase2Tests(unittest.TestCase):
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

    def test_ensure_phase2_drains_phase1_pending_exits_and_populates_new_pending(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Canonical text north.", "Obvious paths: east.", {"768": "east"}),
                _sample_room(768, "Clanthew Boulevard", "Canonical text boulevard.", "Obvious paths: west, east.", {"788": "west", "771": "east"}),
                _sample_room(771, "Clanthew Boulevard", "Canonical text farther boulevard.", "Obvious paths: west.", {"768": "west"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        self.created.extend(phase1_rooms.values())
        self.assertEqual(phase1_rooms[788].db.pending_canonical_exits, [{"destination_id": 768, "command": "east"}])

        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768])
        self.created.extend(room for room in phase2_rooms.values() if room not in self.created)

        north = phase1_rooms[788]
        boulevard = phase2_rooms[768]
        north_exit_keys = sorted(obj.key for obj in north.contents if getattr(obj, "destination", None) is not None)
        self.assertEqual(north_exit_keys, ["east"])
        self.assertEqual(north.db.pending_canonical_exits, [])
        self.assertEqual(boulevard.db.pending_canonical_exits, [{"destination_id": 771, "command": "east"}])

    def test_ensure_phase2_supports_crossing_subarea_titles(self):
        map_path = self._write_map(
            [
                _sample_room(
                    13493,
                    "The Back Lawn",
                    "Canonical amphitheater text.",
                    "Obvious paths: go Amphi gate, east.",
                    {"13494": "east"},
                    area_prefix="The Crossing Amphitheater",
                )
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[13493])
        self.created.extend(rooms.values())

        lawn = rooms[13493]
        self.assertEqual(lawn.key, "The Back Lawn")
        self.assertEqual(lawn.db.canonical_title, "The Back Lawn")
        self.assertTrue(lawn.db.is_canonical_crossing)
        self.assertNotEqual(lawn.db.desc, "Canonical amphitheater text.")
        self.assertEqual(lawn.db.pending_canonical_exits, [{"destination_id": 13494, "command": "east"}])

    def test_ensure_phase2_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Canonical text north.", "Obvious paths: east.", {"768": "east"}),
                _sample_room(768, "Clanthew Boulevard", "Canonical text boulevard.", "Obvious paths: west.", {"788": "west"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        first = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768])
        second = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768])
        self.created.extend(phase1_rooms.values())
        self.created.extend(room for room in first.values() if room not in self.created)

        self.assertEqual(first[768].id, second[768].id)
        exits = [obj for obj in phase1_rooms[788].contents if getattr(obj, "destination", None) == first[768]]
        self.assertEqual(len(exits), 1)

    def test_ensure_phase2_supports_apostrophe_and_numbered_titles(self):
        map_path = self._write_map(
            [
                _sample_room(889, "Varlet's Run", "Canonical varlet text.", "Obvious paths: east.", {}),
                _sample_room(925, "3 Retainers' Crescent", "Canonical crescent text.", "Obvious paths: west.", {}),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[889, 925])
        self.created.extend(rooms.values())

        self.assertEqual(rooms[889].key, "Varlet's Run")
        self.assertEqual(rooms[925].key, "3 Retainers' Crescent")
        self.assertTrue(rooms[889].db.is_canonical_crossing)
        self.assertTrue(rooms[925].db.is_canonical_crossing)


if __name__ == "__main__":
    unittest.main()