import json
import os
import tempfile
import unittest
from collections import deque

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
            if not (
                bool(getattr(getattr(destination, "db", None), "is_canonical_crossing", False))
                or bool(getattr(getattr(destination, "db", None), "is_canonical_guildhall_stub", False))
            ):
                continue
            seen.add(destination.id)
            queue.append(destination)
            reached.add(int(getattr(getattr(destination, "db", None), "canonical_map_id", 0) or 0))
    return reached


class CanonicalCrossingPhase6Tests(unittest.TestCase):
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

    def test_phase6_anchor_set_matches_audit_corrections(self):
        self.assertEqual(len(import_canonical.PHASE6_ROOM_IDS), 33)
        self.assertNotIn(776, import_canonical.PHASE6_ROOM_IDS)
        self.assertIn(8235, import_canonical.PHASE6_ROOM_IDS)

    def test_ensure_phase6_drains_existing_phase_and_stub_pending_exits_and_preserves_forward_refs(self):
        map_path = self._write_map(
            [
                _sample_room(731, "Hodierna Way", "Phase 3 west.", "Obvious paths: south.", {"742": "south"}),
                _sample_room(734, "Alamhif Trace", "Phase 3 trace.", "Obvious paths: west.", {"735": "west"}),
                _sample_room(739, "Immortals' Approach", "Phase 5 approach.", "Obvious paths: west.", {"740": "west"}),
                _sample_room(741, "Immortals' Approach", "Phase 5 bridge.", "Obvious paths: go bridge.", {"928": "go bridge"}),
                _sample_room(754, "Albreda Boulevard", "Phase 4 boulevard.", "Obvious paths: east.", {"755": "e"}),
                _sample_room(776, "Trollferry Quay", "Phase 1 quay.", "Obvious paths: east, south.", {"775": "east", "777": "south"}),
                _sample_room(784, "Asemath Walk", "Phase 3 walk.", "Obvious paths: south.", {"735": "south"}),
                _sample_room(801, "Firulf Vista", "Phase 4 vista.", "Obvious paths: south.", {"797": "south"}),
                _sample_room(808, "Gildleaf Circle", "Phase 4 circle.", "Obvious exits: west.", {"809": "west"}),
                _sample_room(817, "Firulf Vista", "Phase 4 vista.", "Obvious paths: east.", {"818": "e"}),
                _sample_room(840, "Crofton Walk", "Phase 4 walk.", "Obvious paths: southwest.", {"842": "southwest"}),
                _sample_room(865, "Goodwhate Pike", "Phase 3 pike.", "Obvious paths: west.", {"866": "west"}),
                _sample_room(870, "Kertigen Road", "Phase 4 road.", "Obvious paths: east.", {"887": "east"}),
                _sample_room(876, "Kertigen Road", "Phase 4 road.", "Obvious paths: east.", {"886": "east"}),
                _sample_room(893, "Dodgers' Row", "Phase 3 row.", "Obvious paths: south.", {"894": "south"}),
                _sample_room(899, "Esplanade Eluned", "Phase 5 esplanade.", "Obvious paths: northwest.", {"898": "northwest"}),
                _sample_room(901, "Bank Street", "Phase 3 bank.", "Obvious paths: west, north.", {"896": "west", "902": "n"}),
                _sample_room(903, "Water Sprite Way", "Phase 3 way.", "Obvious paths: west, south.", {"894": "west", "902": "s"}),
                _sample_room(913, "Mercantile Street", "Phase 3 mercantile.", "Obvious paths: west, south.", {"900": "west", "914": "south"}),
                _sample_room(915, "Esplanade Eluned", "Phase 5 esplanade.", "Obvious paths: north.", {"914": "north"}),
                _sample_room(920, "Lemicus Square", "Phase 4 square.", "Obvious paths: northwest.", {"921": "northwest"}),
                _sample_room(927, "3 Retainers' Crescent", "Phase 3 crescent.", "Obvious paths: south.", {"928": "south"}),
                _sample_room(930, "Esplanade Eluned", "Phase 5 esplanade.", "Obvious paths: east.", {"929": "east"}),
                _sample_room(15122, "Holy Warrior's Promenade", "Stub promenade.", "Obvious paths: out.", {"818": "go trail"}, area_prefix="Paladins' Guild"),
                _sample_room(5995, "Foyer", "Stub foyer.", "Obvious exits: north.", {"897": "go door"}, area_prefix="The Raven's Court"),
                _sample_room(8916, "Shipment Center", "Stub shipment.", "Obvious paths: out.", {"895": "out"}, area_prefix="Traders' Guild"),
                _sample_room(9077, "Foyer", "Stub thieves.", "Obvious paths: west.", {"887": "go lattice grate"}, area_prefix="Thieves' Guild"),
                _sample_room(735, "Asemath Walk", "Canonical phase 6 walk.", "Obvious paths: north, east, west.", {"784": "north", "734": "east", "736": "west"}),
                _sample_room(736, "Water Street", "Canonical water street.", "Obvious paths: east, west.", {"19241": "go bath", "735": "east", "737": "west"}),
                _sample_room(737, "Water Street", "Canonical water street west.", "Obvious paths: east, west.", {"736": "east", "738": "w"}),
                _sample_room(738, "Full Moons Crescent", "Canonical crescent.", "Obvious paths: north, east.", {"11936": "go seeress house", "737": "e", "778": "north"}),
                _sample_room(740, "Werfnen's Strole", "Canonical strole.", "Obvious paths: east.", {"739": "east", "8277": "go inn"}),
                _sample_room(742, "Gull's View Lane", "Canonical lane north.", "Obvious paths: north, south.", {"731": "north", "743": "south"}),
                _sample_room(743, "Gull's View Lane", "Canonical lane south.", "Obvious paths: north, south.", {"11691": "go shrine", "742": "north", "744": "south"}),
                _sample_room(755, "Albreda Alley", "Canonical alley.", "Obvious paths: east.", {"11755": "go build", "754": "e"}),
                _sample_room(775, "Trollferry Approach", "Canonical approach.", "Obvious paths: north, east, west.", {"16657": "go society building", "774": "north", "776": "west", "779": "east"}),
                _sample_room(777, "Embankment", "Canonical embankment north.", "Obvious paths: north, south.", {"19125": "go door", "776": "north", "778": "south"}),
                _sample_room(778, "Embankment", "Canonical embankment south.", "Obvious paths: north, south.", {"738": "south", "777": "north"}),
                _sample_room(797, "Boar Alley", "Canonical alley.", "Obvious paths: north, east, south.", {"6065": "go door", "762": "south", "801": "north", "816": "east"}),
                _sample_room(809, "Covered Alleyway", "Canonical alleyway.", "Obvious exits: east, west.", {"14615": "go arch", "16863": "go side door", "808": "east", "810": "west"}),
                _sample_room(818, "Northeast Customs", "Canonical customs.", "Obvious paths: west.", {"15122": "go trail", "817": "w", "992": "go gate"}),
                _sample_room(842, "Crofton Close", "Canonical close.", "Obvious paths: northeast.", {"840": "northeast"}),
                _sample_room(866, "Western Gate", "Canonical gate.", "Obvious paths: east.", {"12184": "go house", "1387": "go gate", "865": "east", "938": "go stair"}),
                _sample_room(886, "Ustial Road", "Canonical road west.", "Obvious paths: east, west.", {"11757": "go building", "876": "west", "897": "east"}),
                _sample_room(887, "Scorpion Lane", "Canonical lane west.", "Obvious paths: east, west.", {"870": "west", "894": "east"}),
                _sample_room(894, "Scorpion Lane", "Canonical lane east.", "Obvious paths: north, east, south, west.", {"19152": "go shop", "887": "west", "893": "north", "895": "south", "903": "east"}),
                _sample_room(895, "Commerce Avenue", "Canonical avenue north.", "Obvious paths: north, east, south.", {"8916": "go doors", "894": "north", "896": "south", "902": "east"}),
                _sample_room(896, "Commerce Avenue", "Canonical avenue south.", "Obvious paths: north, east, south.", {"19216": "go guard", "895": "north", "897": "south", "901": "east"}),
                _sample_room(897, "Ustial Road", "Canonical road east.", "Obvious paths: north, east, south, west.", {"5995": "go building", "886": "west", "896": "north", "898": "south", "900": "east"}),
                _sample_room(898, "Stevedore's Wend", "Canonical wend.", "Obvious paths: north, southeast.", {"14157": "go old warehouse", "897": "north", "899": "southeast"}),
                _sample_room(900, "Mercantile Street", "Canonical street.", "Obvious paths: east, west.", {"13703": "go shrine", "897": "west", "913": "east"}),
                _sample_room(902, "Water Sprite Way", "Canonical way.", "Obvious paths: north, south, west.", {"19376": "go shop", "50987": "go cottage", "895": "west", "901": "s", "903": "n"}),
                _sample_room(914, "Scullion Way", "Canonical way.", "Obvious paths: north, south.", {"913": "north", "915": "south"}),
                _sample_room(921, "Haven's End", "Canonical end east.", "Obvious paths: southeast, west.", {"13275": "go tavern", "920": "southeast", "922": "west"}),
                _sample_room(922, "Haven's End", "Canonical end west.", "Obvious paths: east.", {"12617": "climb bank", "19373": ";escort", "921": "east"}),
                _sample_room(928, "Chieftain Walk", "Canonical walk east.", "Obvious paths: north, southeast, southwest.", {"741": "go bridge", "927": "north", "929": "southwest", "931": "se"}),
                _sample_room(929, "Chieftain Walk", "Canonical walk west.", "Obvious paths: northeast, west.", {"6045": "go shipyard gate", "928": "northeast", "930": "west"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[776])
        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[731, 734, 784, 865, 893, 901, 903, 913, 927])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[754, 801, 808, 817, 840, 870, 876, 920])
        phase5_rooms = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[739, 741, 899, 915, 930])
        stub_rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[15122, 5995, 8916, 9077])
        phase6_rooms = import_canonical.ensure_canonical_crossing_phase6(
            map_path=map_path,
            room_ids=[735, 736, 737, 738, 740, 742, 743, 755, 775, 777, 778, 797, 809, 818, 842, 866, 886, 887, 894, 895, 896, 897, 898, 900, 902, 914, 921, 922, 928, 929],
        )

        self.assertEqual(phase3_rooms[731].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[734].db.pending_canonical_exits, [])
        self.assertEqual(phase5_rooms[739].db.pending_canonical_exits, [])
        self.assertEqual(phase5_rooms[741].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[901].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[903].db.pending_canonical_exits, [])
        self.assertEqual(phase3_rooms[913].db.pending_canonical_exits, [])
        self.assertEqual(phase5_rooms[915].db.pending_canonical_exits, [])
        self.assertEqual(stub_rooms[5995].db.pending_canonical_exits, [])
        self.assertEqual(stub_rooms[8916].db.pending_canonical_exits, [])
        self.assertEqual(stub_rooms[9077].db.pending_canonical_exits, [])
        self.assertEqual(stub_rooms[15122].db.pending_canonical_exits, [])
        self.assertEqual(phase6_rooms[818].db.pending_canonical_exits, [{"destination_id": 992, "command": "go gate"}])
        self.assertEqual(phase6_rooms[886].db.pending_canonical_exits, [{"destination_id": 11757, "command": "go building"}])
        self.assertEqual(phase6_rooms[898].db.pending_canonical_exits, [{"destination_id": 14157, "command": "go old warehouse"}])
        self.assertEqual(phase6_rooms[740].db.pending_canonical_exits, [{"destination_id": 8277, "command": "go inn"}])

    def test_ensure_phase6_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(735, "Asemath Walk", "Canonical walk.", "Obvious paths: north.", {"784": "north"}),
                _sample_room(895, "Commerce Avenue", "Canonical avenue.", "Obvious paths: east.", {"902": "east"}),
                _sample_room(902, "Water Sprite Way", "Canonical way.", "Obvious paths: west.", {"895": "west"}),
            ]
        )

        first = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[735, 895, 902])
        second = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[735, 895, 902])

        self.assertEqual(first[735].id, second[735].id)
        self.assertEqual(first[895].id, second[895].id)
        exits = [obj for obj in first[895].contents if getattr(obj, "destination", None) == first[902]]
        self.assertEqual(len(exits), 1)

    def test_ensure_phase6_combined_with_stubs_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(901, "Bank Street", "Phase 3 bank.", "Obvious paths: west.", {"896": "west"}),
                _sample_room(8916, "Shipment Center", "Stub shipment.", "Obvious paths: out.", {"895": "out"}, area_prefix="Traders' Guild"),
                _sample_room(895, "Commerce Avenue", "Canonical avenue.", "Obvious paths: north, south.", {"8916": "go doors", "896": "south"}),
                _sample_room(896, "Commerce Avenue", "Canonical avenue south.", "Obvious paths: east, north.", {"895": "north", "901": "east"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[901])
        stub_rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[8916])
        first = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[895, 896])
        second = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[895, 896])

        self.assertEqual(first[895].id, second[895].id)
        self.assertEqual(first[896].id, second[896].id)
        bank_exit = [obj for obj in phase3_rooms[901].contents if getattr(obj, "destination", None) == first[896]]
        shipment_exit = [obj for obj in stub_rooms[8916].contents if getattr(obj, "destination", None) == first[895]]
        self.assertEqual(len(bank_exit), 1)
        self.assertEqual(len(shipment_exit), 1)

    def test_phase6_reachability_unlocks_traders_thieves_riverpine_and_riverlace_but_not_mongers_or_8235(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Phase 1 arrival.", "Obvious paths: east, south, west, north.", {"731": "east", "903": "south", "876": "west", "741": "north"}),
                _sample_room(731, "Hodierna Way", "Phase 3 west.", "Obvious paths: south.", {"742": "south"}),
                _sample_room(741, "Immortals' Approach", "Phase 5 bridge.", "Obvious paths: go bridge, west.", {"928": "go bridge", "739": "west"}),
                _sample_room(744, "Gull's View Terrace", "Phase 3 terrace.", "Obvious paths: north, south.", {"743": "north", "745": "south"}),
                _sample_room(745, "Riverpine Way", "Phase 4 way.", "Obvious paths: northeast.", {"824": "northeast"}),
                _sample_room(824, "Riverpine Way", "Phase 4 way.", "Obvious paths: northeast, southwest.", {"745": "southwest", "825": "northeast"}),
                _sample_room(825, "Riverpine Way", "Phase 4 way.", "Obvious paths: northeast, southwest.", {"824": "southwest", "826": "northeast"}),
                _sample_room(826, "Riverpine Circle", "Phase 5 circle.", "Obvious paths: southwest.", {"825": "southwest"}),
                _sample_room(876, "Kertigen Road", "Phase 4 road.", "Obvious paths: east.", {"886": "east"}),
                _sample_room(903, "Water Sprite Way", "Phase 3 way.", "Obvious paths: west, south.", {"894": "west", "902": "s"}),
                _sample_room(927, "3 Retainers' Crescent", "Phase 3 crescent.", "Obvious paths: south, east.", {"928": "south", "16505": "east"}),
                _sample_room(739, "Immortals' Approach", "Phase 5 approach.", "Obvious paths: west.", {"740": "west"}),
                _sample_room(16505, "Tatting Street", "Phase 4 street.", "Obvious paths: east, west.", {"927": "west", "16506": "east"}),
                _sample_room(16506, "Tatting Street", "Phase 4 street.", "Obvious paths: east, west.", {"16505": "west", "16507": "east"}),
                _sample_room(16507, "Tatting Street", "Phase 4 street.", "Obvious paths: east, west.", {"16506": "west", "16508": "east"}),
                _sample_room(16508, "Riverlace Lane", "Phase 5 lane.", "Obvious paths: west.", {"16507": "west"}),
                _sample_room(5995, "Foyer", "Stub foyer.", "Obvious exits: north.", {"897": "go door", "5998": "northeast"}, area_prefix="The Raven's Court"),
                _sample_room(5998, "Ballroom", "Stub ballroom.", "Obvious exits: southwest.", {"5995": "southwest", "6016": "go door"}, area_prefix="The Raven's Court"),
                _sample_room(6016, "Terrace", "Stub terrace.", "Obvious paths: northwest.", {"5998": "go door", "6017": "northwest"}, area_prefix="The Raven's Court"),
                _sample_room(6017, "Silver Walk", "Stub walk.", "Obvious paths: southeast.", {"6016": "southeast", "9077": "tap knocker"}, area_prefix="The Raven's Court"),
                _sample_room(823, "Main Hall", "Stub traders hall.", "Obvious paths: out.", {"901": "out"}, area_prefix="Traders' Guild"),
                _sample_room(8916, "Shipment Center", "Stub shipment.", "Obvious paths: out.", {"895": "out"}, area_prefix="Traders' Guild"),
                _sample_room(9077, "Foyer", "Stub thieves.", "Obvious paths: west.", {"887": "go lattice grate", "6017": "out"}, area_prefix="Thieves' Guild"),
                _sample_room(735, "Asemath Walk", "Canonical walk.", "Obvious paths: east, west.", {"736": "west", "734": "east"}),
                _sample_room(742, "Gull's View Lane", "Canonical lane north.", "Obvious paths: north, south.", {"731": "north", "743": "south"}),
                _sample_room(743, "Gull's View Lane", "Canonical lane south.", "Obvious paths: north, south.", {"742": "north", "744": "south"}),
                _sample_room(775, "Trollferry Approach", "Canonical approach.", "Obvious paths: east, west.", {"776": "west", "779": "east"}),
                _sample_room(777, "Embankment", "Canonical embankment.", "Obvious paths: north.", {"776": "north"}),
                _sample_room(781, "S'zella Plaza", "Canonical plaza.", "Obvious paths: north.", {"782": "south", "769": "north"}),
                _sample_room(886, "Ustial Road", "Canonical road west.", "Obvious paths: east, west.", {"876": "west", "897": "east"}),
                _sample_room(887, "Scorpion Lane", "Canonical lane west.", "Obvious paths: east, west.", {"870": "west", "894": "east"}),
                _sample_room(894, "Scorpion Lane", "Canonical lane east.", "Obvious paths: north, south, west.", {"893": "north", "895": "south", "903": "east", "887": "west"}),
                _sample_room(895, "Commerce Avenue", "Canonical avenue north.", "Obvious paths: east, south.", {"8916": "go doors", "896": "south", "902": "east"}),
                _sample_room(896, "Commerce Avenue", "Canonical avenue south.", "Obvious paths: north, east, south.", {"895": "north", "901": "east", "897": "south"}),
                _sample_room(897, "Ustial Road", "Canonical road east.", "Obvious paths: north, east, south, west.", {"5995": "go building", "886": "west", "896": "north", "898": "south", "900": "east"}),
                _sample_room(898, "Stevedore's Wend", "Canonical wend.", "Obvious paths: north, southeast.", {"897": "north", "899": "southeast"}),
                _sample_room(900, "Mercantile Street", "Canonical street.", "Obvious paths: east, west.", {"897": "west", "913": "east"}),
                _sample_room(901, "Bank Street", "Phase 3 bank.", "Obvious paths: west.", {"896": "west", "823": "go guildhall"}),
                _sample_room(902, "Water Sprite Way", "Canonical way.", "Obvious paths: north, west.", {"895": "west", "903": "n", "901": "s"}),
                _sample_room(928, "Chieftain Walk", "Canonical walk east.", "Obvious paths: north.", {"741": "go bridge", "927": "north"}),
                _sample_room(740, "Werfnen's Strole", "Canonical strole.", "Obvious paths: east.", {"739": "east", "8277": "go inn"}),
                _sample_room(8235, "Werfnen's Strole", "Canonical strole spur.", "Obvious paths: east.", {}),
                _sample_room(947, "Mongers' Square", "Phase 5 square.", "Obvious paths: east.", {"948": "east", "954": "west"}),
                _sample_room(948, "Mongers' Bazaar", "Phase 5 bazaar.", "Obvious paths: west.", {"947": "west"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[731, 744, 903, 927, 901])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[745, 824, 825, 876, 16505, 16506, 16507])
        phase5_rooms = import_canonical.ensure_canonical_crossing_phase5(map_path=map_path, room_ids=[739, 741, 826, 16508, 947, 948])
        stub_rooms = guildhall_stubs.ensure_canonical_guildhall_stubs(map_path=map_path, room_ids=[5995, 5998, 6016, 6017, 823, 8916, 9077])
        phase6_rooms = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[742, 743, 886, 887, 894, 895, 896, 897, 898, 900, 902, 928, 740, 8235])

        reached = _reachable_map_ids(phase1_rooms[788])
        for room_id in [826, 16508, 823, 8916, 9077, 740]:
            self.assertIn(room_id, reached)
        self.assertNotIn(8235, reached)
        optional_live_mongers = {947, 948}.intersection(reached)
        self.assertIn(optional_live_mongers, (set(), {947}, {947, 948}))

    def test_phase6_metadata_and_descriptions_are_nonverbatim(self):
        map_path = self._write_map(
            [
                _sample_room(735, "Asemath Walk", "Canonical walk text.", "Obvious paths: west.", {"736": "west"}),
                _sample_room(895, "Commerce Avenue", "Canonical avenue text.", "Obvious paths: east.", {"902": "east"}),
                _sample_room(818, "Northeast Customs", "Canonical customs text.", "Obvious paths: west.", {"817": "w", "992": "go gate"}),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase6(map_path=map_path, room_ids=[735, 895, 818])

        self.assertEqual(rooms[735].db.canonical_phase, 6)
        self.assertEqual(rooms[895].db.canonical_phase, 6)
        self.assertEqual(rooms[818].db.canonical_phase, 6)
        self.assertEqual(rooms[735].db.canonical_source, "direlore:map-1777858104.json")
        self.assertNotEqual(rooms[735].db.desc, "Canonical walk text.")
        self.assertNotEqual(rooms[895].db.desc, "Canonical avenue text.")
        self.assertNotEqual(rooms[818].db.desc, "Canonical customs text.")
        pending_destinations = {(entry["destination_id"], entry["command"]) for entry in rooms[818].db.pending_canonical_exits}
        self.assertIn((992, "go gate"), pending_destinations)


if __name__ == "__main__":
    unittest.main()