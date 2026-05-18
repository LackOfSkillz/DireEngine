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


class CanonicalCrossingPhase3Tests(unittest.TestCase):
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

    def test_ensure_phase3_drains_phase2_pending_exits_and_preserves_future_pending(self):
        map_path = self._write_map(
            [
                _sample_room(768, "Clanthew Boulevard", "Phase 2 boulevard.", "Obvious paths: east.", {"769": "east"}),
                _sample_room(769, "Clanthew Boulevard", "Phase 3 boulevard one.", "Obvious paths: east, west.", {"768": "east", "770": "west", "781": "south"}),
                _sample_room(770, "Clanthew Boulevard", "Phase 3 boulevard two.", "Obvious paths: east, west, north.", {"769": "east", "771": "west", "810": "north"}),
                _sample_room(810, "Truffenyi Place", "Phase 3 square.", "Obvious paths: south, north.", {"770": "south", "819": "north"}),
                _sample_room(771, "Clanthew Boulevard", "Phase 2 farther boulevard.", "Obvious paths: east.", {}),
                _sample_room(819, "Truffenyi Place", "Phase 2 place.", "Obvious paths: south.", {}),
            ]
        )

        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768, 771, 819])
        self.created.extend(phase2_rooms.values())
        self.assertEqual(phase2_rooms[768].db.pending_canonical_exits, [{"destination_id": 769, "command": "east"}])

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769, 770, 810])
        self.created.extend(room for room in phase3_rooms.values() if room not in self.created)

        boulevard = phase2_rooms[768]
        exits_to_769 = [obj for obj in boulevard.contents if getattr(obj, "destination", None) == phase3_rooms[769]]
        self.assertEqual(len(exits_to_769), 1)
        self.assertEqual(exits_to_769[0].key, "east")
        self.assertEqual(boulevard.db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[770].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[810].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[769].db.pending_canonical_exits, [{"destination_id": 781, "command": "south"}])

    def test_ensure_phase3_supports_group_b_adjacent_completion_rooms(self):
        map_path = self._write_map(
            [
                _sample_room(773, "Sirenberry Row", "Phase 3 row.", "Obvious paths: south.", {"774": "south"}),
                _sample_room(774, "Lorethew Street", "Phase 3 lorethew west.", "Obvious paths: north, east.", {"773": "north", "780": "east"}),
                _sample_room(780, "Lorethew Street", "Phase 3 lorethew east.", "Obvious paths: west, east.", {"774": "west", "782": "east"}),
                _sample_room(782, "Lorethew Street", "Phase 3 lorethew approach.", "Obvious paths: west.", {"780": "west"}),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[773, 774, 780, 782])
        self.created.extend(rooms.values())

        self.assertEqual(rooms[774].key, "Lorethew Street")
        self.assertEqual(rooms[780].key, "Lorethew Street")
        west_exits = sorted(obj.key for obj in rooms[774].contents if getattr(obj, "destination", None) is not None)
        east_exits = sorted(obj.key for obj in rooms[780].contents if getattr(obj, "destination", None) is not None)
        self.assertEqual(west_exits, ["east", "north"])
        self.assertEqual(east_exits, ["east", "west"])
        self.assertEqual(rooms[774].db.pending_canonical_exits, [])
        self.assertEqual(rooms[780].db.pending_canonical_exits, [])

    def test_ensure_phase3_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(768, "Clanthew Boulevard", "Phase 2 boulevard.", "Obvious paths: east.", {"769": "east"}),
                _sample_room(769, "Clanthew Boulevard", "Phase 3 boulevard one.", "Obvious paths: east, west.", {"768": "east", "770": "west"}),
                _sample_room(770, "Clanthew Boulevard", "Phase 3 boulevard two.", "Obvious paths: east, west, north.", {"769": "east", "771": "west", "810": "north"}),
                _sample_room(771, "Clanthew Boulevard", "Phase 2 farther boulevard.", "Obvious paths: east.", {}),
                _sample_room(810, "Truffenyi Place", "Phase 3 square.", "Obvious paths: south.", {"770": "south"}),
            ]
        )

        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768, 771])
        first = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769, 770, 810])
        second = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769, 770, 810])
        self.created.extend(phase2_rooms.values())
        self.created.extend(room for room in first.values() if room not in self.created)

        self.assertEqual(first[769].id, second[769].id)
        exits = [obj for obj in phase2_rooms[768].contents if getattr(obj, "destination", None) == first[769]]
        self.assertEqual(len(exits), 1)


if __name__ == "__main__":
    unittest.main()