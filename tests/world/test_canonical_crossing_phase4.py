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


class CanonicalCrossingPhase4Tests(unittest.TestCase):
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

    def test_ensure_phase4_drains_phase3_pending_exits_and_preserves_future_pending(self):
        map_path = self._write_map(
            [
                _sample_room(813, "Flamethorn Way", "Phase 3 way.", "Obvious paths: north, east, south.", {"804": "north", "812": "west", "19076": "go shop"}),
                _sample_room(804, "Eylhaar Bane Road", "Phase 4 road.", "Obvious paths: east, south, west.", {"803": "east", "805": "west", "812": "south"}),
                _sample_room(805, "Eylhaar Bane Road", "Phase 4 road west.", "Obvious paths: east, south, west.", {"804": "east", "807": "south", "10081": "go arch"}),
                _sample_room(807, "Gildleaf Circle", "Phase 4 circle.", "Obvious paths: north, south.", {"805": "north", "808": "south"}),
                _sample_room(808, "Gildleaf Circle", "Phase 4 circle center.", "Obvious paths: north, east, west.", {"807": "north", "809": "west", "811": "east"}),
                _sample_room(811, "Gildleaf Circle", "Phase 4 circle east.", "Obvious paths: north, west.", {"808": "west", "812": "north"}),
                _sample_room(812, "Gildleaf Circle", "Phase 4 circle north.", "Obvious paths: north, east, south.", {"804": "north", "811": "south", "813": "east"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[813])
        self.created.extend(phase3_rooms.values())
        self.assertEqual(
            phase3_rooms[813].db.pending_canonical_exits,
            [{"destination_id": 804, "command": "north"}, {"destination_id": 812, "command": "west"}, {"destination_id": 19076, "command": "go shop"}],
        )

        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[804, 805, 807, 808, 811, 812])
        self.created.extend(room for room in phase4_rooms.values() if room not in self.created)

        exits_to_812 = [obj for obj in phase3_rooms[813].contents if getattr(obj, "destination", None) == phase4_rooms[812]]
        exits_to_804 = [obj for obj in phase3_rooms[813].contents if getattr(obj, "destination", None) == phase4_rooms[804]]
        self.assertEqual(len(exits_to_812), 1)
        self.assertEqual(exits_to_812[0].key, "west")
        self.assertEqual(len(exits_to_804), 1)
        self.assertEqual(exits_to_804[0].key, "north")
        self.assertEqual(phase3_rooms[813].db.pending_canonical_exits, [{"destination_id": 19076, "command": "go shop"}])
        self.assertEqual(phase4_rooms[808].db.pending_canonical_exits, [{"destination_id": 809, "command": "west"}])

    def test_ensure_phase4_supports_crossing_temple_subarea_cluster(self):
        map_path = self._write_map(
            [
                _sample_room(5752, "Entrance Hall", "Temple entrance text.", "Obvious paths: clockwise, widdershins.", {"5751": "go door", "5753": "go clockwise", "5778": "go widdershin", "5779": "go pill"}, area_prefix="The Crossing Temple"),
                _sample_room(5753, "Hallway", "Temple hall text one.", "Obvious paths: clockwise, widdershins.", {"5752": "go widdershin", "5754": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5754, "Hallway", "Temple hall text two.", "Obvious paths: clockwise, widdershins.", {"5753": "go widdershin", "5755": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5755, "Hallway", "Temple hall text three.", "Obvious paths: clockwise, widdershins.", {"5754": "go widdershin", "5756": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5756, "Hallway", "Temple hall text four.", "Obvious paths: clockwise, widdershins.", {"5755": "go widdershin", "5772": "go clockwise", "5757": "go arch"}, area_prefix="The Crossing Temple"),
                _sample_room(5772, "Hallway", "Temple hall text five.", "Obvious paths: clockwise, widdershins.", {"5756": "go widdershin", "5773": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5773, "Hallway", "Temple hall text six.", "Obvious paths: clockwise, widdershins.", {"5772": "go widdershin", "5774": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5774, "Hallway", "Temple hall text seven.", "Obvious paths: clockwise, widdershins.", {"5773": "go widdershin", "5775": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5775, "Hallway", "Temple hall text eight.", "Obvious paths: clockwise, widdershins.", {"5774": "go widdershin", "5776": "go clockwise", "5771": "go arch"}, area_prefix="The Crossing Temple"),
                _sample_room(5776, "Hallway", "Temple hall text nine.", "Obvious paths: clockwise, widdershins.", {"5775": "go widdershin", "5777": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5777, "Hallway", "Temple hall text ten.", "Obvious paths: clockwise, widdershins.", {"5776": "go widdershin", "5778": "go clockwise"}, area_prefix="The Crossing Temple"),
                _sample_room(5778, "Hallway", "Temple hall text eleven.", "Obvious paths: clockwise, widdershins.", {"5752": "go clockwise", "5777": "go widdershin"}, area_prefix="The Crossing Temple"),
                _sample_room(5779, "Main Arch", "Temple arch text.", "Obvious exits: none.", {"5752": "go pill", "5768": "go arch"}, area_prefix="The Crossing Temple"),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[5752, 5753, 5754, 5755, 5756, 5772, 5773, 5774, 5775, 5776, 5777, 5778, 5779])
        self.created.extend(rooms.values())

        entrance = rooms[5752]
        clockwise = [obj for obj in entrance.contents if getattr(obj, "destination", None) == rooms[5753]]
        widdershin = [obj for obj in entrance.contents if getattr(obj, "destination", None) == rooms[5778]]
        pill = [obj for obj in entrance.contents if getattr(obj, "destination", None) == rooms[5779]]
        self.assertEqual(len(clockwise), 1)
        self.assertEqual(clockwise[0].key, "clockwise")
        self.assertEqual(len(widdershin), 1)
        self.assertEqual(widdershin[0].key, "widdershin")
        self.assertEqual(len(pill), 1)
        self.assertEqual(pill[0].key, "pill")
        self.assertEqual(entrance.db.pending_canonical_exits, [{"destination_id": 5751, "command": "go door"}])
        self.assertEqual(rooms[5779].db.pending_canonical_exits, [{"destination_id": 5768, "command": "go arch"}])
        self.assertTrue(rooms[5752].db.is_canonical_crossing)
        self.assertEqual(rooms[5752].db.canonical_phase, 4)

    def test_ensure_phase4_supports_kertigen_road_chain(self):
        map_path = self._write_map(
            [
                _sample_room(865, "Goodwhate Pike", "Phase 3 pike.", "Obvious paths: east, west, south.", {"867": "south"}),
                _sample_room(867, "Kertigen Road", "Phase 4 road one.", "Obvious paths: north, south.", {"865": "north", "868": "south"}),
                _sample_room(868, "Kertigen Road", "Phase 4 road two.", "Obvious paths: north, south.", {"867": "north", "869": "south"}),
                _sample_room(869, "Kertigen Road", "Phase 4 road three.", "Obvious paths: north, south.", {"868": "north", "870": "south"}),
                _sample_room(870, "Kertigen Road", "Phase 4 road four.", "Obvious paths: north, east, south.", {"869": "north", "871": "south", "887": "east"}),
                _sample_room(871, "Kertigen Road", "Phase 4 road five.", "Obvious paths: north, south.", {"870": "north", "872": "south"}),
                _sample_room(872, "Kertigen Road", "Phase 4 road six.", "Obvious paths: north, south, west.", {"871": "north", "873": "west", "876": "south"}),
                _sample_room(876, "Kertigen Road", "Phase 4 road seven.", "Obvious paths: north, east, south, west.", {"872": "north", "877": "west", "880": "south", "886": "east"}),
                _sample_room(880, "Kertigen Road", "Phase 4 road eight.", "Obvious paths: north, south, west.", {"876": "north", "881": "west", "884": "south"}),
                _sample_room(884, "Kertigen Road", "Phase 4 road nine.", "Obvious paths: north, southeast.", {"880": "north", "885": "southeast"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[865])
        phase4_rooms = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[867, 868, 869, 870, 871, 872, 876, 880, 884])
        self.created.extend(phase3_rooms.values())
        self.created.extend(room for room in phase4_rooms.values() if room not in self.created)

        exits_to_867 = [obj for obj in phase3_rooms[865].contents if getattr(obj, "destination", None) == phase4_rooms[867]]
        self.assertEqual(len(exits_to_867), 1)
        self.assertEqual(exits_to_867[0].key, "south")
        self.assertEqual(phase4_rooms[870].db.pending_canonical_exits, [{"destination_id": 887, "command": "east"}])
        self.assertEqual(phase4_rooms[884].db.pending_canonical_exits, [{"destination_id": 885, "command": "southeast"}])

    def test_ensure_phase4_completes_representative_district_clusters(self):
        map_path = self._write_map(
            [
                _sample_room(837, "Smithy Lane", "Phase 3 smithy.", "Obvious paths: northeast.", {"838": "northeast"}),
                _sample_room(838, "Smithy Lane", "Phase 4 smithy one.", "Obvious paths: north, east, southwest.", {"837": "southwest", "839": "east", "840": "north"}),
                _sample_room(839, "Smithy Lane", "Phase 4 smithy two.", "Obvious paths: north, west.", {"838": "west", "843": "north"}),
                _sample_room(840, "Crofton Walk", "Phase 4 crofton one.", "Obvious paths: east, south, west.", {"838": "south", "841": "west", "843": "east"}),
                _sample_room(841, "Crofton Walk", "Phase 4 crofton two.", "Obvious paths: north, east.", {"840": "east", "846": "north"}),
                _sample_room(843, "Smithy Lane", "Phase 4 smithy three.", "Obvious paths: north, south, west.", {"839": "south", "840": "west", "844": "north"}),
                _sample_room(844, "Smithy Lane", "Phase 4 smithy four.", "Obvious paths: south, west.", {"843": "south", "845": "west"}),
                _sample_room(845, "Smithy Lane", "Phase 4 smithy five.", "Obvious paths: east.", {"844": "east", "846": "go bridge"}),
                _sample_room(846, "Crofton Walk", "Phase 4 crofton three.", "Obvious paths: south.", {"841": "south", "845": "go bridge"}),
                _sample_room(867, "Kertigen Road", "Phase 4 kertigen one.", "Obvious paths: north, south.", {"865": "north", "868": "south"}),
                _sample_room(868, "Kertigen Road", "Phase 4 kertigen two.", "Obvious paths: north, south.", {"867": "north", "869": "south"}),
                _sample_room(869, "Kertigen Road", "Phase 4 kertigen three.", "Obvious paths: north, south.", {"868": "north", "870": "south"}),
                _sample_room(870, "Kertigen Road", "Phase 4 kertigen four.", "Obvious paths: north, south.", {"869": "north", "871": "south"}),
                _sample_room(871, "Kertigen Road", "Phase 4 kertigen five.", "Obvious paths: north, south.", {"870": "north", "872": "south"}),
                _sample_room(872, "Kertigen Road", "Phase 4 kertigen six.", "Obvious paths: north, south, west.", {"871": "north", "873": "west", "876": "south"}),
                _sample_room(873, "Swithen's Court", "Phase 4 court one.", "Obvious paths: east, west.", {"872": "east", "874": "west"}),
                _sample_room(874, "Swithen's Court", "Phase 4 court two.", "Obvious paths: east, west.", {"873": "east", "875": "west"}),
                _sample_room(875, "Swithen's Court", "Phase 4 court three.", "Obvious paths: east.", {"874": "east"}),
                _sample_room(876, "Kertigen Road", "Phase 4 kertigen seven.", "Obvious paths: north, south, west.", {"872": "north", "877": "west", "880": "south"}),
                _sample_room(877, "Inkhorne Street", "Phase 4 ink one.", "Obvious paths: east, west.", {"876": "east", "878": "west"}),
                _sample_room(878, "Inkhorne Street", "Phase 4 ink two.", "Obvious paths: east, west.", {"877": "east", "879": "west"}),
                _sample_room(879, "Inkhorne Street", "Phase 4 ink three.", "Obvious paths: east.", {"878": "east"}),
                _sample_room(880, "Kertigen Road", "Phase 4 kertigen eight.", "Obvious paths: north, south, west.", {"876": "north", "881": "west", "884": "south"}),
                _sample_room(881, "Elmod Close", "Phase 4 elmod one.", "Obvious paths: east, west.", {"880": "east", "882": "west"}),
                _sample_room(882, "Elmod Close", "Phase 4 elmod two.", "Obvious paths: east, west.", {"881": "east", "883": "west"}),
                _sample_room(883, "Elmod Close", "Phase 4 elmod three.", "Obvious paths: east.", {"882": "east"}),
                _sample_room(884, "Kertigen Road", "Phase 4 kertigen nine.", "Obvious paths: north, southeast.", {"880": "north", "885": "southeast"}),
                _sample_room(885, "Lemicus Square", "Phase 4 lemicus one.", "Obvious paths: east, south, northwest.", {"884": "northwest", "919": "east", "920": "south"}),
                _sample_room(919, "Lemicus Square", "Phase 4 lemicus two.", "Obvious paths: southwest, west.", {"885": "west", "920": "southwest"}),
                _sample_room(920, "Lemicus Square", "Phase 4 lemicus three.", "Obvious paths: north, northeast.", {"885": "north", "919": "northeast"}),
            ]
        )

        rooms = import_canonical.ensure_canonical_crossing_phase4(
            map_path=map_path,
            room_ids=[838, 839, 840, 841, 843, 844, 845, 846, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 919, 920],
        )
        self.created.extend(rooms.values())

        self.assertEqual(rooms[838].db.canonical_phase, 4)
        self.assertEqual(rooms[870].db.canonical_phase, 4)
        self.assertEqual(rooms[885].db.canonical_phase, 4)
        smithy_backlink = [
            obj for obj in rooms[838].contents if int(getattr(getattr(obj, "destination", None), "db", object()).canonical_map_id or 0) == 837
        ]
        if smithy_backlink:
            self.assertEqual(len(smithy_backlink), 1)
            self.assertEqual(smithy_backlink[0].key, "southwest")
            self.assertEqual(rooms[838].db.pending_canonical_exits, [])
        else:
            self.assertEqual(rooms[838].db.pending_canonical_exits, [{"destination_id": 837, "command": "southwest"}])
        self.assertEqual(rooms[845].db.pending_canonical_exits, [])
        self.assertEqual(rooms[870].db.pending_canonical_exits, [])
        self.assertEqual(rooms[884].db.pending_canonical_exits, [])
        self.assertEqual(rooms[919].db.pending_canonical_exits, [])

    def test_ensure_phase4_combined_phase_idempotence(self):
        map_path = self._write_map(
            [
                _sample_room(788, "Town Green North", "Phase 1 north.", "Obvious paths: east.", {"768": "east"}),
                _sample_room(768, "Clanthew Boulevard", "Phase 2 boulevard.", "Obvious paths: west, east.", {"788": "west", "769": "east"}),
                _sample_room(769, "Clanthew Boulevard", "Phase 3 boulevard.", "Obvious paths: east, west.", {"768": "east", "804": "west"}),
                _sample_room(804, "Eylhaar Bane Road", "Phase 4 road.", "Obvious paths: east, south, west.", {"769": "east", "805": "west", "812": "south"}),
                _sample_room(805, "Eylhaar Bane Road", "Phase 4 road west.", "Obvious paths: east, south.", {"804": "east", "807": "south"}),
                _sample_room(807, "Gildleaf Circle", "Phase 4 circle.", "Obvious paths: north, south.", {"805": "north", "808": "south"}),
                _sample_room(808, "Gildleaf Circle", "Phase 4 circle center.", "Obvious paths: north, east.", {"807": "north", "811": "east"}),
                _sample_room(811, "Gildleaf Circle", "Phase 4 circle east.", "Obvious paths: north, west.", {"808": "west", "812": "north"}),
                _sample_room(812, "Gildleaf Circle", "Phase 4 circle north.", "Obvious paths: north, east, south.", {"804": "north", "811": "south", "813": "east"}),
            ]
        )

        phase1_rooms = import_canonical.ensure_canonical_crossing_phase1(map_path=map_path, room_ids=[788])
        phase2_rooms = import_canonical.ensure_canonical_crossing_phase2(map_path=map_path, room_ids=[768])
        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[769])
        first = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[804, 805, 807, 808, 811, 812])
        second = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[804, 805, 807, 808, 811, 812])

        self.created.extend(phase1_rooms.values())
        self.created.extend(room for room in phase2_rooms.values() if room not in self.created)
        self.created.extend(room for room in phase3_rooms.values() if room not in self.created)
        self.created.extend(room for room in first.values() if room not in self.created)

        self.assertEqual(first[804].id, second[804].id)
        exits = [obj for obj in phase3_rooms[769].contents if getattr(obj, "destination", None) == first[804]]
        self.assertEqual(len(exits), 1)
        self.assertEqual(exits[0].key, "west")
        self.assertEqual(first[812].db.pending_canonical_exits, [{"destination_id": 813, "command": "east"}])

    def test_ensure_phase4_is_idempotent(self):
        map_path = self._write_map(
            [
                _sample_room(865, "Goodwhate Pike", "Phase 3 pike.", "Obvious paths: east, west, south.", {"867": "south"}),
                _sample_room(867, "Kertigen Road", "Phase 4 road one.", "Obvious paths: north, south.", {"865": "north", "868": "south"}),
                _sample_room(868, "Kertigen Road", "Phase 4 road two.", "Obvious paths: north, south.", {"867": "north", "869": "south"}),
                _sample_room(869, "Kertigen Road", "Phase 4 road three.", "Obvious paths: north, south.", {"868": "north", "870": "south"}),
                _sample_room(870, "Kertigen Road", "Phase 4 road four.", "Obvious paths: north, east, south.", {"869": "north", "871": "south"}),
                _sample_room(871, "Kertigen Road", "Phase 4 road five.", "Obvious paths: north, south.", {"870": "north", "872": "south"}),
                _sample_room(872, "Kertigen Road", "Phase 4 road six.", "Obvious paths: north, south, west.", {"871": "north", "876": "south"}),
                _sample_room(876, "Kertigen Road", "Phase 4 road seven.", "Obvious paths: north, east, south, west.", {"872": "north", "880": "south"}),
                _sample_room(880, "Kertigen Road", "Phase 4 road eight.", "Obvious paths: north, south, west.", {"876": "north", "884": "south"}),
                _sample_room(884, "Kertigen Road", "Phase 4 road nine.", "Obvious paths: north, southeast.", {"880": "north"}),
            ]
        )

        phase3_rooms = import_canonical.ensure_canonical_crossing_phase3(map_path=map_path, room_ids=[865])
        first = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[867, 868, 869, 870, 871, 872, 876, 880, 884])
        second = import_canonical.ensure_canonical_crossing_phase4(map_path=map_path, room_ids=[867, 868, 869, 870, 871, 872, 876, 880, 884])
        self.created.extend(phase3_rooms.values())
        self.created.extend(room for room in first.values() if room not in self.created)

        self.assertEqual(first[867].id, second[867].id)
        exits = [obj for obj in phase3_rooms[865].contents if getattr(obj, "destination", None) == first[867]]
        self.assertEqual(len(exits), 1)


if __name__ == "__main__":
    unittest.main()