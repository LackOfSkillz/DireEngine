import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import django
import yaml

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from server.conf import at_server_startstop
from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from web import views as web_views
from world.area_forge import map_api
from world.areas.the_crossing import ensure_full_canonical_crossing
from world.areas.the_crossing.import_canonical import get_canonical_crossing_arrival_room
from world.worlddata.services import export_zone_service


class LandingV2ManifestAndMapFilterTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        failures = safe_smoke_delete(*self.created)
        self.assertEqual(failures, [])

    def _create_room(self, key):
        room = create_object("typeclasses.rooms.Room", key=key, nohome=True)
        self.created.append(room)
        return room

    def _create_exit(self, location, key, destination, **flags):
        exit_obj = create_object("typeclasses.exits.Exit", key=key, location=location, destination=destination, home=location)
        for attr, value in flags.items():
            setattr(exit_obj.db, attr, value)
        self.created.append(exit_obj)
        return exit_obj

    def _payload_edge_metrics(self, payload):
        rooms = {room["id"]: room for room in list(payload.get("rooms") or [])}
        edge_count = 0
        max_manhattan = 0
        directions = set()
        for room in rooms.values():
            room_map = dict(room.get("map") or {})
            source_x = room_map.get("x")
            source_y = room_map.get("y")
            for direction, spec in dict(room.get("exits") or {}).items():
                target = rooms.get(str((spec or {}).get("target") or "").strip())
                if not target:
                    continue
                target_map = dict(target.get("map") or {})
                target_x = target_map.get("x")
                target_y = target_map.get("y")
                edge_count += 1
                directions.add(direction)
                if None not in (source_x, source_y, target_x, target_y):
                    max_manhattan = max(max_manhattan, abs(source_x - target_x) + abs(source_y - target_y))
        return {
            "edge_count": edge_count,
            "max_manhattan": max_manhattan,
            "directions": directions,
        }

    def test_write_zone_export_produces_v2_compatible_the_landing_yaml(self):
        ensure_full_canonical_crossing()

        with tempfile.TemporaryDirectory() as temp_dir:
            zones_dir = Path(temp_dir)
            with patch.object(export_zone_service, "_zones_dir", return_value=zones_dir), patch.object(web_views, "_worlddata_zones_dir", return_value=zones_dir):
                output_path = export_zone_service.write_zone_export("the_landing")
                with output_path.open("r", encoding="utf-8") as handle:
                    exported_payload = yaml.safe_load(handle)
                payload = web_views._load_builder_zone_yaml("the_landing")
                path_exists = output_path.exists()

        self.assertTrue(path_exists)
        self.assertEqual(len(exported_payload["rooms"]), 253)
        self.assertTrue(all("canonical_image" in room for room in exported_payload["rooms"]))
        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["zone_id"], "the_landing")
        self.assertEqual(len(payload["rooms"]), 201)

    def test_builder_payload_matches_in_game_filtered_landing_profile(self):
        ensure_full_canonical_crossing()

        with tempfile.TemporaryDirectory() as temp_dir:
            zones_dir = Path(temp_dir)
            with patch.object(export_zone_service, "_zones_dir", return_value=zones_dir), patch.object(web_views, "_worlddata_zones_dir", return_value=zones_dir):
                export_zone_service.write_zone_export("the_landing")
                builder_payload = web_views._load_builder_zone_yaml("the_landing")

        arrival = get_canonical_crossing_arrival_room()
        game_payload = map_api.get_zone_map(SimpleNamespace(location=arrival))
        builder_metrics = self._payload_edge_metrics(builder_payload)
        game_max_manhattan = 0
        game_rooms_by_id = {room["id"]: room for room in game_payload["rooms"]}
        for edge in game_payload["edges"]:
            source = game_rooms_by_id.get(edge["from"])
            target = game_rooms_by_id.get(edge["to"])
            if not source or not target:
                continue
            game_max_manhattan = max(game_max_manhattan, abs(source["x"] - target["x"]) + abs(source["y"] - target["y"]))

        self.assertEqual(len(builder_payload["rooms"]), len(game_payload["rooms"]))
        self.assertEqual(builder_metrics["edge_count"], len(game_payload["edges"]))
        self.assertEqual(builder_metrics["max_manhattan"], game_max_manhattan)
        self.assertLessEqual(builder_metrics["max_manhattan"], 160)
        self.assertEqual(builder_metrics["edge_count"], len(game_payload["edges"]))

    def test_archive_zone_export_removes_new_landing_from_v2_zone_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zones_dir = Path(temp_dir)
            archive_dir = zones_dir / "_archive"
            zones_dir.mkdir(parents=True, exist_ok=True)
            new_landing_path = zones_dir / "new_landing.yaml"
            with new_landing_path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump({"schema_version": "v1", "zone_id": "new_landing", "name": "New Landing", "rooms": [{"id": "room1", "name": "Room 1"}]}, handle, sort_keys=False)

            with patch.object(export_zone_service, "_zones_dir", return_value=zones_dir), patch.object(export_zone_service, "_archive_zones_dir", return_value=archive_dir), patch.object(web_views, "_worlddata_zones_dir", return_value=zones_dir):
                before_ids = [zone.get("id") for zone in web_views._serialize_yaml_builder_zones()]
                archived_path = export_zone_service.archive_zone_export("new_landing")
                after_ids = [zone.get("id") for zone in web_views._serialize_yaml_builder_zones()]
                archived_exists = archived_path.exists()

        self.assertIn("new_landing", before_ids)
        self.assertNotIn("new_landing", after_ids)
        self.assertIsNotNone(archived_path)
        self.assertTrue(archived_exists)

    def test_startup_helper_regenerates_missing_the_landing_yaml(self):
        with patch("server.conf.at_server_startstop._append_guard_startup_trace") as trace_mock, patch("world.builder.services.map_exporter._rooms_for_zone", return_value=[object()] * 253), patch("world.worlddata.services.export_zone_service.write_zone_export") as write_mock, patch("web.views._load_builder_zone_yaml", side_effect=[Exception("missing"), {"rooms": [object()] * 253}]):
            payload = at_server_startstop._ensure_canonical_v2_manifest("the_landing")

        self.assertEqual(len(payload["rooms"]), 253)
        write_mock.assert_called_once_with("the_landing")
        self.assertTrue(any(call.args[1] == "canonical_v2_manifest_regenerated" for call in trace_mock.call_args_list))

    def test_get_local_map_skips_hidden_and_secret_exits(self):
        origin = self._create_room("The Seating Area")
        visible = self._create_room("Visible Archway")
        hidden = self._create_room("Hidden Passage")
        secret = self._create_room("Secret Niche")
        self._create_exit(origin, "east", visible)
        self._create_exit(origin, "passage", hidden, hidden_exit=True)
        self._create_exit(origin, "crawl", secret, secret=True)

        payload = map_api.get_local_map(SimpleNamespace(location=origin))
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn((origin.id, visible.id, "east"), edge_dirs)
        self.assertNotIn((origin.id, hidden.id, "passage"), edge_dirs)
        self.assertNotIn((origin.id, secret.id, "crawl"), edge_dirs)

    def test_get_zone_map_skips_hidden_exits_but_keeps_visible_destinations(self):
        area_tag = "landing_hidden_exit_probe"
        origin = self._create_room("The Seating Area")
        visible = self._create_room("Visible Archway")
        hidden = self._create_room("Hidden Passage")
        alt_origin = self._create_room("Alt Path")
        for room in (origin, visible, hidden, alt_origin):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"

        self._create_exit(origin, "east", visible)
        self._create_exit(origin, "passage", hidden, hidden_exit=True)
        self._create_exit(alt_origin, "east", hidden)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}
        room_ids = {room["id"] for room in payload["rooms"]}

        self.assertIn((origin.id, visible.id, "east"), edge_dirs)
        self.assertNotIn((origin.id, hidden.id, "passage"), edge_dirs)
        self.assertIn(hidden.id, room_ids)

    def test_get_zone_map_keeps_dominant_coordinate_image_only(self):
        area_tag = "landing_spaghetti_probe"
        origin = self._create_room("Town Green North")
        visible = self._create_room("Town Green West")
        offsheet = self._create_room("Mongers' Square")

        for room in (origin, visible, offsheet):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"

        origin.db.map_x = 100
        origin.db.map_y = 100
        origin.db.canonical_image = "main.png"
        visible.db.map_x = 101
        visible.db.map_y = 100
        visible.db.canonical_image = "main.png"
        offsheet.db.map_x = 0
        offsheet.db.map_y = 0
        offsheet.db.canonical_image = ""

        self._create_exit(origin, "west", visible)
        self._create_exit(origin, "east", offsheet)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        room_ids = {room["id"] for room in payload["rooms"]}
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn(origin.id, room_ids)
        self.assertIn(visible.id, room_ids)
        self.assertNotIn(offsheet.id, room_ids)
        self.assertIn((origin.id, visible.id, "west"), edge_dirs)
        self.assertNotIn((origin.id, offsheet.id, "east"), edge_dirs)

    def test_get_zone_map_suppresses_discontinuous_long_edges(self):
        area_tag = "landing_long_edge_probe"
        origin = self._create_room("Immortals' Approach")
        destination = self._create_room("Chieftain Walk")

        for room in (origin, destination):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "main.png"

        origin.db.map_x = 10
        origin.db.map_y = 10
        destination.db.map_x = 260
        destination.db.map_y = 92

        self._create_exit(origin, "south", destination)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}
        room_ids = {room["id"] for room in payload["rooms"]}

        self.assertIn(origin.id, room_ids)
        self.assertIn(destination.id, room_ids)
        self.assertNotIn((origin.id, destination.id, "south"), edge_dirs)

    def test_cached_zone_template_filters_multi_image_payload(self):
        area_tag = "landing_cached_template_probe"
        primary_rooms = [self._create_room(f"Primary {index}") for index in range(5)]
        secondary_rooms = [self._create_room(f"Secondary {index}") for index in range(3)]
        imageless_rooms = [self._create_room(f"Imageless {index}") for index in range(2)]

        for index, room in enumerate(primary_rooms):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "primary.png"
            room.db.map_x = 100 + index
            room.db.map_y = 100 + (1 if index >= 3 else 0)

        for index, room in enumerate(secondary_rooms):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "secondary.png"
            room.db.map_x = 200 + index
            room.db.map_y = 200

        for index, room in enumerate(imageless_rooms):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = ""
            room.db.map_x = index
            room.db.map_y = index

        self._create_exit(primary_rooms[0], "east", primary_rooms[1])
        self._create_exit(primary_rooms[1], "east", primary_rooms[2])
        self._create_exit(primary_rooms[2], "east", primary_rooms[3])
        self._create_exit(primary_rooms[3], "east", primary_rooms[4])
        self._create_exit(primary_rooms[0], "southeast", primary_rooms[3])
        self._create_exit(primary_rooms[1], "south", primary_rooms[4])
        self._create_exit(primary_rooms[0], "east", secondary_rooms[0])
        self._create_exit(primary_rooms[2], "go bridge", primary_rooms[4])
        self._create_exit(primary_rooms[0], "south", self._create_room("Far South"), hidden_exit=False)
        self.created[-1].tags.add(area_tag, category="build")
        self.created[-1].db.zone = "The Landing"
        self.created[-1].db.zone_id = "the_landing"
        self.created[-1].db.canonical_image = "primary.png"
        self.created[-1].db.map_x = 100
        self.created[-1].db.map_y = 220

        map_api.clear_zone_map_cache(area_tag)
        template = map_api._get_cached_zone_template(area_tag)

        room_ids = {room["id"] for room in template["rooms"]}
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in template["edges"]}

        self.assertEqual(len(template["rooms"]), 5)
        self.assertEqual(len(template["edges"]), 7)
        self.assertEqual(room_ids, {room.id for room in primary_rooms})
        self.assertTrue(all(room.id not in room_ids for room in secondary_rooms + imageless_rooms))
        self.assertIn((primary_rooms[0].id, primary_rooms[1].id, "east"), edge_dirs)
        self.assertIn((primary_rooms[1].id, primary_rooms[4].id, "south"), edge_dirs)
        self.assertNotIn((primary_rooms[0].id, secondary_rooms[0].id, "east"), edge_dirs)
        self.assertIn((primary_rooms[2].id, primary_rooms[4].id, "go bridge"), edge_dirs)

    def test_filter_logic_version_invalidates_zone_template_cache(self):
        area_tag = "landing_filter_logic_version_probe"
        origin = self._create_room("Version Origin")
        destination = self._create_room("Version Destination")

        for index, room in enumerate((origin, destination)):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "primary.png"
            room.db.map_x = 10 + index
            room.db.map_y = 10

        self._create_exit(origin, "east", destination)

        map_api.clear_zone_map_cache(area_tag)
        map_api._get_cached_zone_template(area_tag)
        signature_before = map_api._ZONE_MAP_TEMPLATE_CACHE[area_tag]["signature"]

        with patch.object(map_api, "_FILTER_LOGIC_VERSION", "v2"):
            map_api._get_cached_zone_template(area_tag)
            signature_after = map_api._ZONE_MAP_TEMPLATE_CACHE[area_tag]["signature"]

        self.assertNotEqual(signature_before, signature_after)

    def test_compass_direction_normalization_handles_abbreviations(self):
        self.assertEqual(map_api._normalize_exit_direction("e"), "east")
        self.assertEqual(map_api._normalize_exit_direction("ne"), "northeast")
        self.assertEqual(map_api._normalize_exit_direction("east"), "east")
        self.assertEqual(map_api._normalize_exit_direction("go gate"), "go gate")

    def test_zone_map_keeps_named_exits_within_threshold(self):
        area_tag = "landing_non_compass_probe"
        origin = self._create_room("River Span")
        destination = self._create_room("Far Bank")

        for room in (origin, destination):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.map_x = 10 if room is origin else 11
            room.db.map_y = 10
            room.db.canonical_image = "main.png"

        self._create_exit(origin, "go bridge", destination)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn((origin.id, destination.id, "go bridge"), edge_dirs)

    def test_zone_map_keeps_compass_abbreviation_exits(self):
        area_tag = "landing_abbrev_probe"
        origin = self._create_room("Town Green North")
        destination = self._create_room("Town Green East")

        for room in (origin, destination):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "main.png"

        origin.db.map_x = 10
        origin.db.map_y = 10
        destination.db.map_x = 11
        destination.db.map_y = 10

        self._create_exit(origin, "e", destination)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn((origin.id, destination.id, "e"), edge_dirs)

    def test_zone_map_drops_long_compass_edges_over_threshold(self):
        area_tag = "landing_threshold_drop_probe"
        origin = self._create_room("Kertigen Road North")
        destination = self._create_room("Kertigen Road South")

        for room in (origin, destination):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "main.png"

        origin.db.map_x = 10
        origin.db.map_y = 10
        destination.db.map_x = 10
        destination.db.map_y = 190

        self._create_exit(origin, "south", destination)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertNotIn((origin.id, destination.id, "south"), edge_dirs)

    def test_zone_map_keeps_compass_edges_at_threshold(self):
        area_tag = "landing_threshold_keep_probe"
        origin = self._create_room("Ustial Road North")
        destination = self._create_room("Ustial Road South")

        for room in (origin, destination):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"
            room.db.canonical_image = "main.png"

        origin.db.map_x = 10
        origin.db.map_y = 10
        destination.db.map_x = 10
        destination.db.map_y = 170

        self._create_exit(origin, "south", destination)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn((origin.id, destination.id, "south"), edge_dirs)

    def test_local_map_applies_same_predicate(self):
        origin = self._create_room("Map Origin")
        short_abbrev = self._create_room("Short East")
        threshold_room = self._create_room("Threshold South")
        long_room = self._create_room("Long South")
        bridge_room = self._create_room("Bridge Room")

        origin.db.map_x = 10
        origin.db.map_y = 10
        origin.db.canonical_image = "main.png"

        short_abbrev.db.map_x = 11
        short_abbrev.db.map_y = 10
        short_abbrev.db.canonical_image = "main.png"

        threshold_room.db.map_x = 10
        threshold_room.db.map_y = 170
        threshold_room.db.canonical_image = "main.png"

        long_room.db.map_x = 10
        long_room.db.map_y = 190
        long_room.db.canonical_image = "main.png"

        bridge_room.db.map_x = 11
        bridge_room.db.map_y = 11
        bridge_room.db.canonical_image = "main.png"

        self._create_exit(origin, "e", short_abbrev)
        self._create_exit(origin, "south", threshold_room)
        self._create_exit(origin, "south", long_room)
        self._create_exit(origin, "go bridge", bridge_room)

        payload = map_api.get_local_map(SimpleNamespace(location=origin), radius=1)
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}
        room_ids = {room["id"] for room in payload["rooms"]}

        self.assertIn((origin.id, short_abbrev.id, "e"), edge_dirs)
        self.assertIn((origin.id, threshold_room.id, "south"), edge_dirs)
        self.assertNotIn((origin.id, long_room.id, "south"), edge_dirs)
        self.assertIn((origin.id, bridge_room.id, "go bridge"), edge_dirs)
        self.assertIn(short_abbrev.id, room_ids)
        self.assertIn(threshold_room.id, room_ids)
        self.assertNotIn(long_room.id, room_ids)
        self.assertIn(bridge_room.id, room_ids)

    def test_zone_map_drops_rooms_with_only_offsheet_destinations(self):
        area_tag = "landing_offsheet_only_probe"
        origin = self._create_room("Origin")
        offsheet = self._create_room("Offsheet")
        sub_image = self._create_room("Sub Image")

        for room in (origin, offsheet, sub_image):
            room.tags.add(area_tag, category="build")
            room.db.zone = "The Landing"
            room.db.zone_id = "the_landing"

        origin.db.map_x = 10
        origin.db.map_y = 10
        origin.db.canonical_image = "main.png"

        offsheet.db.map_x = 11
        offsheet.db.map_y = 10
        offsheet.db.canonical_image = "main.png"

        sub_image.db.map_x = 200
        sub_image.db.map_y = 200
        sub_image.db.canonical_image = "sub.png"

        self._create_exit(origin, "east", offsheet)
        self._create_exit(offsheet, "east", sub_image)

        map_api.clear_zone_map_cache(area_tag)
        payload = map_api.get_zone_map(SimpleNamespace(location=origin), build_cache=True)
        room_ids = {room["id"] for room in payload["rooms"]}
        edge_dirs = {(edge["from"], edge["to"], edge["dir"]) for edge in payload["edges"]}

        self.assertIn(origin.id, room_ids)
        self.assertNotIn(offsheet.id, room_ids)
        self.assertNotIn(sub_image.id, room_ids)
        self.assertNotIn((offsheet.id, sub_image.id, "east"), edge_dirs)


if __name__ == "__main__":
    unittest.main()