import json
import os
import tempfile
import unittest
from collections import deque

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


def _reachable_map_ids(start_room):
    seen = {start_room.id}
    queue = deque([start_room])
    reached = {int(start_room.db.canonical_map_id)}
    while queue:
        room = queue.popleft()
        for obj in list(getattr(room, "contents", []) or []):
            destination = getattr(obj, "destination", None)
            if destination is None or destination.id in seen:
                continue
            if not bool(getattr(getattr(destination, "db", None), "is_canonical_crossing", False)):
                continue
            seen.add(destination.id)
            queue.append(destination)
            reached.add(int(destination.db.canonical_map_id))
    return reached


class CanonicalCrossingPhase5Tests(unittest.TestCase):
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

    def test_ensure_phase5_drains_phase1_4_pending_exits_and_preserves_future_pending(self):
        map_path = self._write_map(
            [
                _sample_room(732, "Hodierna Way", "Phase 3 approach west.", "Obvious paths: southwest.", {"741": "southwest"}),
                _sample_room(734, "Alamhif Trace", "Phase 3 approach south.", "Obvious paths: south.", {"739": "south"}),
                _sample_room(825, "Riverpine Way", "Phase 4 riverpine bridge.", "Obvious paths: northeast.", {"826": "northeast"}),
                _sample_room(919, "Lemicus Square", "Phase 4 esplanade bridge.", "Obvious paths: northeast.", {"899": "northeast"}),
                _sample_room(16507, "Tatting Street", "Phase 4 riverlace bridge.", "Obvious paths: east.", {"16508": "east"}),
                _sample_room(739, "Immortals' Approach", "Phase 5 approach one.", "Obvious paths: north, northeast.", {"741": "north", "13591": "northeast", "13592": "go stair"}),
                _sample_room(741, "Immortals' Approach", "Phase 5 approach two.", "Obvious paths: northeast, east.", {"732": "northeast", "739": "east"}),
                _sample_room(899, "Esplanade Eluned", "Phase 5 esplanade one.", "Obvious paths: northeast, southwest.", {"915": "northeast", "919": "southwest"}),
                _sample_room(915, "Esplanade Eluned", "Phase 5 esplanade two.", "Obvious paths: north, southwest.", {"899": "southwest", "916": "north", "931": "go arch"}),
                _sample_room(916, "Esplanade Eluned", "Phase 5 esplanade three.", "Obvious paths: south.", {"915": "south"}),
                _sample_room(826, "Riverpine Circle", "Phase 5 circle one.", "Obvious paths: east, southwest.", {"825": "southwest", "827": "east"}),
                _sample_room(827, "Riverpine Circle", "Phase 5 circle two.", "Obvious paths: east, west.", {"826": "west", "828": "east"}),
                _sample_room(828, "Riverpine Circle", "Phase 5 circle three.", "Obvious paths: west.", {"827": "west", "833": "go gate"}),
                _sample_room(16508, "Riverlace Lane", "Phase 5 lane one.", "Obvious paths: east, west.", {"16507": "west", "16509": "east"}),
                _sample_room(16509, "Riverlace Lane", "Phase 5 lane two.", "Obvious paths: east, west.", {"16508": "west", "16510": "east"}),
                _sample_room(16510, "Riverlace Lane", "Phase 5 lane three.", "Obvious paths: west.", {"16509": "west", "16514": "go arch"}),
                _sample_room(13591, "Immortals' Walk", "Phase 5 walk one.", "Obvious paths: southwest, west.", {"739": "southwest", "13590": "west"}),
                _sample_room(13590, "Immortals' Walk", "Phase 5 walk two.", "Obvious paths: east.", {"13591": "east"}),
                _sample_room(947, "Mongers' Square", "Phase 5 square hub.", "Obvious paths: east, north.", {"948": "east", "949": "north", "954": "west"}),
                _sample_room(948, "Mongers' Bazaar", "Phase 5 bazaar east.", "Obvious paths: west.", {"947": "west"}),
                _sample_room(949, "Mongers' Bazaar", "Phase 5 bazaar north.", "Obvious paths: south.", {"947": "south"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[732, 734])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[825, 919, 16507])
        phase5_rooms = import_canonical.ensure_canonical_crossing_phase5(
            map_path=map_path,
            room_ids=[739, 741, 899, 915, 916, 826, 827, 828, 16508, 16509, 16510, 13591, 13590, 947, 948, 949],
        )

        self.assertEqual(phase3_rooms[732].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[734].db.pending_canonical_exits, [])
        self.assertEqual(phase4_rooms[825].db.pending_canonical_exits, [])
        self.assertEqual(phase4_rooms[919].db.pending_canonical_exits, [])
        self.assertEqual(phase4_rooms[16507].db.pending_canonical_exits, [])
        self.assertEqual(phase5_rooms[739].db.pending_canonical_exits, [{"destination_id": 13592, "command": "go stair"}])
        self.assertEqual(phase5_rooms[915].db.pending_canonical_exits, [{"destination_id": 931, "command": "go arch"}])
        self.assertEqual(phase5_rooms[828].db.pending_canonical_exits, [{"destination_id": 833, "command": "go gate"}])
        self.assertEqual(phase5_rooms[16510].db.pending_canonical_exits, [{"destination_id": 16514, "command": "go arch"}])
        mongers_square_live_954 = [
            obj for obj in phase5_rooms[947].contents if int(getattr(getattr(obj, "destination", None), "db", object()).canonical_map_id or 0) == 954
        ]
        if mongers_square_live_954:
            self.assertEqual(len(mongers_square_live_954), 1)
            self.assertEqual(mongers_square_live_954[0].key, "west")
            self.assertEqual(phase5_rooms[947].db.pending_canonical_exits, [])
        else:
            self.assertEqual(phase5_rooms[947].db.pending_canonical_exits, [{"destination_id": 954, "command": "west"}])

    def test_ensure_phase5_supports_mongers_square_hub_pattern(self):
        map_path = self._write_map(
            [
                _sample_room(947, "Mongers' Square", "Phase 5 square hub.", "Obvious paths: east, north, northwest, west, southwest, south.", {"948": "east", "949": "north", "950": "northwest", "951": "west", "952": "southwest", "953": "south"}),
                _sample_room(948, "Mongers' Bazaar", "Phase 5 bazaar east.", "Obvious paths: west.", {"947": "west"}),
                _sample_room(949, "Mongers' Bazaar", "Phase 5 bazaar north.", "Obvious paths: south.", {"947": "south"}),
                _sample_room(950, "Mongers' Bazaar", "Phase 5 bazaar northwest.", "Obvious paths: southeast.", {"947": "southeast"}),
                _sample_room(951, "Mongers' Bazaar", "Phase 5 bazaar west.", "Obvious paths: east.", {"947": "east"}),
                _sample_room(952, "Mongers' Bazaar", "Phase 5 bazaar southwest.", "Obvious paths: northeast.", {"947": "northeast"}),
                _sample_room(953, "Mongers' Bazaar", "Phase 5 bazaar south.", "Obvious paths: north.", {"947": "north"}),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[947, 948, 949, 950, 951, 952, 953])

        exit_keys = sorted(obj.key for obj in rooms[947].contents if getattr(obj, "destination", None) is not None)
        self.assertEqual(exit_keys, ["east", "north", "northwest", "south", "southwest", "west"])
        self.assertEqual(rooms[947].db.canonical_phase, 5)
        self.assertEqual(rooms[947].db.pending_canonical_exits, [])
        for room_id in [948, 949, 950, 951, 952, 953]:
            self.assertEqual(rooms[room_id].db.pending_canonical_exits, [])

    def test_ensure_phase5_supports_immortals_approach_bridge_closure(self):
        map_path = self._write_map(
            [
                _sample_room(734, "Alamhif Trace", "Phase 3 trace.", "Obvious paths: south.", {"739": "south"}),
                _sample_room(739, "Immortals' Approach", "Phase 5 approach one.", "Obvious paths: north, northeast.", {"741": "north", "13591": "northeast"}),
                _sample_room(741, "Immortals' Approach", "Phase 5 approach two.", "Obvious paths: east, northeast.", {"739": "east", "732": "northeast"}),
                _sample_room(13591, "Immortals' Walk", "Phase 5 walk one.", "Obvious paths: southwest, west.", {"739": "southwest", "13590": "west"}),
                _sample_room(13590, "Immortals' Walk", "Phase 5 walk two.", "Obvious paths: east.", {"13591": "east"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[734])
        phase5_rooms = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[739, 741, 13591, 13590])

        exits_to_739 = [obj for obj in phase3_rooms[734].contents if getattr(obj, "destination", None) == phase5_rooms[739]]
        self.assertEqual(len(exits_to_739), 1)
        self.assertEqual(exits_to_739[0].key, "south")
        self.assertEqual(phase5_rooms[739].db.pending_canonical_exits, [])
        exits_to_732 = [
            obj for obj in phase5_rooms[741].contents if int(getattr(getattr(obj, "destination", None), "db", object()).canonical_map_id or 0) == 732
        ]
        if exits_to_732:
            self.assertEqual(len(exits_to_732), 1)
            self.assertEqual(exits_to_732[0].key, "northeast")
            self.assertEqual(phase5_rooms[741].db.pending_canonical_exits, [])
        else:
            self.assertEqual(phase5_rooms[741].db.pending_canonical_exits, [{"destination_id": 732, "command": "northeast"}])

    def test_ensure_phase5_combined_phase_idempotence(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Phase 1 north.", "Obvious paths: east.", {"768": "east"}),
                _sample_room(768, "Clanthew Boulevard", "Phase 2 boulevard.", "Obvious paths: west, east.", {"788": "west", "769": "east"}),
                _sample_room(769, "Clanthew Boulevard", "Phase 3 boulevard.", "Obvious paths: east, west.", {"768": "east", "919": "west"}),
                _sample_room(919, "Lemicus Square", "Phase 4 square.", "Obvious paths: northeast, west.", {"769": "west", "899": "northeast"}),
                _sample_room(899, "Esplanade Eluned", "Phase 5 esplanade.", "Obvious paths: southwest.", {"919": "southwest", "915": "north"}),
                _sample_room(915, "Esplanade Eluned", "Phase 5 esplanade north.", "Obvious paths: south.", {"899": "south"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768])
        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[919])
        first = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[899, 915])
        second = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[899, 915])

        self.assertEqual(first[899].id, second[899].id)
        exits = [obj for obj in phase4_rooms[919].contents if getattr(obj, "destination", None) == first[899]]
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].key, "northeast")

    def test_ensure_phase5_supports_representative_arrival_reachability(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Phase 1 north.", "Obvious paths: east, west, north, south, northeast.", {"919": "east", "825": "west", "16507": "north", "739": "south", "947": "northeast"}),
                _sample_room(919, "Lemicus Square", "Phase 4 square.", "Obvious paths: west, northeast.", {"788": "west", "899": "northeast"}),
                _sample_room(825, "Riverpine Way", "Phase 4 riverpine bridge.", "Obvious paths: east, northeast.", {"788": "east", "826": "northeast"}),
                _sample_room(16507, "Tatting Street", "Phase 4 riverlace bridge.", "Obvious paths: south, east.", {"788": "south", "16508": "east"}),
                _sample_room(739, "Immortals' Approach", "Phase 5 approach.", "Obvious paths: north, south.", {"788": "north", "13591": "south"}),
                _sample_room(947, "Mongers' Square", "Phase 5 square hub.", "Obvious paths: southwest, east.", {"788": "southwest", "948": "east"}),
                _sample_room(899, "Esplanade Eluned", "Phase 5 esplanade.", "Obvious paths: southwest.", {"919": "southwest"}),
                _sample_room(826, "Riverpine Circle", "Phase 5 circle.", "Obvious paths: southwest.", {"825": "southwest"}),
                _sample_room(16508, "Riverlace Lane", "Phase 5 lane.", "Obvious paths: west.", {"16507": "west"}),
                _sample_room(13591, "Immortals' Walk", "Phase 5 walk.", "Obvious paths: north.", {"739": "north"}),
                _sample_room(948, "Mongers' Bazaar", "Phase 5 bazaar.", "Obvious paths: west.", {"947": "west"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[919, 825, 16507])
        phase5_rooms = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[739, 947, 899, 826, 16508, 13591, 948])

        reached = _reachable_map_ids(phase1_rooms[788])
        for room_id in [899, 826, 16508, 13591, 948]:
            self.assertIn(room_id, reached)
        self.assertEqual(phase5_rooms[899].db.canonical_phase, 5)
        self.assertEqual(phase5_rooms[826].db.canonical_phase, 5)
        self.assertEqual(phase5_rooms[16508].db.canonical_phase, 5)
        self.assertEqual(phase5_rooms[13591].db.canonical_phase, 5)
        self.assertEqual(phase5_rooms[948].db.canonical_phase, 5)


if __name__ == "__main__":
    unittest.main()