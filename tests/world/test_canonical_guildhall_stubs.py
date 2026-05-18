import json
import os
import tempfile
import unittest
from collections import deque
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from world.areas.the_crossing import guildhall_stubs
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
    reached = {int(getattr(start_room.db, "canonical_map_id", 0) or 0)}
    while queue:
        room = queue.popleft()
        for obj in list(getattr(room, "contents", []) or []):
            destination = getattr(obj, "destination", None)
            if destination is None or destination.id in seen:
                continue
            seen.add(destination.id)
            queue.append(destination)
            reached.add(int(getattr(getattr(destination, "db", None), "canonical_map_id", 0) or 0))
    return reached


class CanonicalGuildhallStubTests(unittest.TestCase):
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

    def test_ensure_guildhall_stubs_drains_phase_pending_exits_and_builds_ranger_chain(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Phase 1 north.", "Obvious paths: east.", {"768": "east"}),
                _sample_room(768, "Clanthew Boulevard", "Phase 2 boulevard.", "Obvious paths: west, east.", {"788": "west", "769": "east"}),
                _sample_room(769, "Clanthew Boulevard", "Phase 3 boulevard.", "Obvious paths: east, west.", {"768": "west", "770": "east"}),
                _sample_room(770, "Clanthew Boulevard", "Phase 3 boulevard east.", "Obvious paths: north, east, west.", {"769": "west", "771": "east", "810": "north", "959": "go gate"}),
                _sample_room(771, "Clanthew Boulevard", "Phase 2 bard gate.", "Obvious paths: west.", {"770": "west", "7898": "go building"}),
                _sample_room(810, "Truffenyi Place", "Phase 3 place.", "Obvious paths: south, north.", {"770": "south", "819": "north"}),
                _sample_room(819, "Truffenyi Place", "Phase 2 place north.", "Obvious paths: south, west.", {"810": "south", "820": "west"}),
                _sample_room(820, "Sicle Grove Lane", "Phase 3 lane.", "Obvious paths: east, west.", {"819": "east", "821": "west"}),
                _sample_room(821, "Sicle Grove Lane", "Phase 4 lane west.", "Obvious paths: east.", {"820": "east", "850": "go gate"}),
                _sample_room(7898, "Commons", "Canonical bard commons.", "Obvious paths: out.", {"771": "out"}, area_prefix="Bards' Guild"),
                _sample_room(959, "Porte-cochere", "Canonical academy approach.", "Obvious paths: out.", {"770": "out", "958": "north"}, area_prefix="Asemath Academy"),
                _sample_room(958, "Entrance", "Canonical academy entrance.", "Obvious paths: south.", {"959": "south"}, area_prefix="Asemath Academy"),
                _sample_room(850, "Pine Needle Path", "Canonical wilds entry.", "Obvious paths: north.", {"821": "go gate", "851": "north"}, area_prefix="Wilds"),
                _sample_room(851, "Pine Needle Path", "Canonical wilds deeper.", "Obvious paths: south.", {"850": "south", "7900": "go guild"}, area_prefix="Wilds"),
                _sample_room(7900, "Main Hall", "Canonical ranger hall.", "Obvious paths: out.", {"851": "out", "13213": "go curt"}, area_prefix="Ranger Guild"),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768, 771, 819])
        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769, 770, 810, 820])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[821])
        stub_rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[7898, 959, 958, 850, 851, 7900])

        self.created.extend(phase1_rooms.values())
        self.created.extend(room for room in phase2_rooms.values() if room not in self.created)
        self.created.extend(room for room in phase3_rooms.values() if room not in self.created)
        self.created.extend(room for room in phase4_rooms.values() if room not in self.created)
        self.created.extend(room for room in stub_rooms.values() if room not in self.created)

        bard_exit = [obj for obj in phase2_rooms[771].contents if getattr(obj, "destination", None) == stub_rooms[7898]]
        ranger_gate = [obj for obj in phase4_rooms[821].contents if getattr(obj, "destination", None) == stub_rooms[850]]
        self.assertEqual(len(bard_exit), 1)
        self.assertEqual(len(ranger_gate), 1)
        self.assertEqual(phase2_rooms[771].db.pending_canonical_exits, [])
        self.assertEqual(phase4_rooms[821].db.pending_canonical_exits, [])
        self.assertEqual(stub_rooms[7900].db.pending_canonical_exits, [{"destination_id": 13213, "command": "go curt"}])
        reached = _reachable_map_ids(phase1_rooms[788])
        self.assertIn(7900, reached)
        self.assertIn(7898, reached)

    def test_ensure_guildhall_stubs_preserves_thieves_forward_reference_when_crossing_source_missing(self):
        map_path = self._write_map(
            [
                _sample_room(5995, "Foyer", "Canonical raven foyer.", "Obvious exits: north, northeast.", {"897": "go door", "5998": "northeast"}, area_prefix="The Raven's Court"),
                _sample_room(5998, "Ballroom", "Canonical raven ballroom.", "Obvious exits: southwest.", {"5995": "southwest", "6016": "go door"}, area_prefix="The Raven's Court"),
                _sample_room(6016, "Terrace", "Canonical raven terrace.", "Obvious paths: northwest.", {"5998": "go door", "6017": "northwest"}, area_prefix="The Raven's Court"),
                _sample_room(6017, "Silver Walk", "Canonical silver walk.", "Obvious paths: southeast.", {"6016": "southeast", "9077": "tap knocker"}, area_prefix="The Raven's Court"),
                _sample_room(9077, "Foyer", "Canonical thieves foyer.", "Obvious paths: out.", {"6017": "out"}, area_prefix="Thieves' Guild"),
            ]
        )

        rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[5995, 5998, 6016, 6017, 9077])
        self.created.extend(rooms.values())

        raven_foyer = rooms[5995]
        silver_walk = rooms[6017]
        thieves_foyer = rooms[9077]
        self.assertEqual(raven_foyer.db.pending_canonical_exits, [{"destination_id": 897, "command": "go door"}])
        knocker_exit = [obj for obj in silver_walk.contents if getattr(obj, "destination", None) == thieves_foyer]
        self.assertEqual(len(knocker_exit), 1)
        self.assertEqual(knocker_exit[0].key, "tap knocker")

    def test_ensure_guildhall_stubs_is_idempotent_and_creates_one_stub_guildleader(self):
        map_path = self._write_map(
            [
                _sample_room(7898, "Commons", "Canonical bard commons.", "Obvious paths: out.", {}, area_prefix="Bards' Guild"),
                _sample_room(7900, "Main Hall", "Canonical ranger hall.", "Obvious paths: out.", {}, area_prefix="Ranger Guild"),
            ]
        )

        first = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[7898, 7900])
        second = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[7898, 7900])
        self.created.extend(first.values())

        self.assertEqual(first[7898].id, second[7898].id)
        self.assertEqual(first[7900].id, second[7900].id)
        bard_leaders = [obj for obj in first[7898].contents if getattr(obj, "db_typeclass_path", "") == guildhall_stubs.STUB_GUILDLEADER_TYPECLASS]
        ranger_leaders = [obj for obj in first[7900].contents if getattr(obj, "db_typeclass_path", "") == guildhall_stubs.STUB_GUILDLEADER_TYPECLASS]
        self.assertEqual(len(bard_leaders), 1)
        self.assertEqual(len(ranger_leaders), 1)

    def test_stub_guildleader_inquiry_and_placeholder_metadata(self):
        map_path = self._write_map(
            [
                _sample_room(823, "Main Hall", "Canonical trader hall.", "Obvious paths: out.", {}, area_prefix="Traders' Guild"),
                _sample_room(9077, "Foyer", "Canonical thieves foyer.", "Obvious paths: out.", {}, area_prefix="Thieves' Guild"),
            ]
        )

        rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[823, 9077])
        self.created.extend(rooms.values())

        trader = next(obj for obj in rooms[823].contents if getattr(obj, "db_typeclass_path", "") == guildhall_stubs.STUB_GUILDLEADER_TYPECLASS)
        thief = next(obj for obj in rooms[9077].contents if getattr(obj, "db_typeclass_path", "") == guildhall_stubs.STUB_GUILDLEADER_TYPECLASS)
        actor = SimpleNamespace()
        self.assertIn("not yet open to new members", trader.handle_inquiry(actor, "join"))
        self.assertTrue(bool(getattr(trader.db, "is_placeholder", False)))
        self.assertFalse(bool(getattr(thief.db, "is_placeholder", True)))
        self.assertIsNone(getattr(thief.db, "canonical_name", None))

    def test_stub_room_metadata_and_descriptions_are_nonverbatim(self):
        map_path = self._write_map(
            [
                _sample_room(7898, "Commons", "Canonical bard commons text.", "Obvious paths: out.", {}, area_prefix="Bards' Guild"),
                _sample_room(5990, "Sanctorum", "Canonical cleric sanctorum text.", "Obvious paths: out.", {}, area_prefix="Clerics' Guild"),
                _sample_room(850, "Pine Needle Path", "Canonical wilds path text.", "Obvious paths: north.", {}, area_prefix="Wilds"),
            ]
        )

        rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[7898, 5990, 850])
        self.created.extend(rooms.values())

        self.assertEqual(rooms[7898].db.canonical_phase, guildhall_stubs.GUILDHALL_STUB_PHASE)
        self.assertEqual(rooms[5990].db.canonical_phase, guildhall_stubs.GUILDHALL_STUB_PHASE)
        self.assertEqual(rooms[850].db.canonical_phase, guildhall_stubs.GUILDHALL_STUB_PHASE)
        self.assertTrue(bool(getattr(rooms[7898].db, "is_canonical_guildhall_stub", False)))
        self.assertEqual(rooms[7898].db.canonical_source, "direlore:map-1777858104.json")
        self.assertNotEqual(rooms[7898].db.desc, "Canonical bard commons text.")
        self.assertNotEqual(rooms[5990].db.desc, "Canonical cleric sanctorum text.")
        self.assertNotEqual(rooms[850].db.desc, "Canonical wilds path text.")


if __name__ == "__main__":
    unittest.main()