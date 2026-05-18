import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from server.conf import at_server_startstop
from systems import canonical_migration
from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from world.area_forge import map_api
from world.builder.services import zone_service
from world.areas.the_crossing import ensure_full_canonical_crossing, import_canonical


class _ProbeCharacter:
    def __init__(self, location):
        self.location = location


class CanonicalCrossingFullImportTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        failures = safe_smoke_delete(*self.created)
        self.assertEqual(failures, [])

    def _create_room(self, key, *, area=None):
        room = create_object("typeclasses.rooms.Room", key=key, nohome=True)
        room.db.area = area
        self.created.append(room)
        return room

    def _create_character(self, key, location=None, home=None):
        character = create_object("typeclasses.characters.Character", key=key, location=location, home=home or location, nohome=True)
        self.created.append(character)
        return character

    def test_full_import_is_idempotent_and_returns_expected_count(self):
        first = ensure_full_canonical_crossing()
        second = ensure_full_canonical_crossing()

        self.assertEqual(len(first), 253)
        self.assertEqual(len(second), 253)
        self.assertEqual(sorted(first.keys()), sorted(second.keys()))

    def test_full_import_applies_landing_zone_metadata_to_arrival(self):
        ensure_full_canonical_crossing()

        arrival = import_canonical.get_canonical_crossing_arrival_room()
        self.assertIsNotNone(arrival)
        self.assertEqual(arrival.db.zone, "The Landing")
        self.assertEqual(arrival.db.zone_id, "the_landing")
        self.assertEqual(arrival.db.area, "The Crossing")
        self.assertEqual(arrival.db.builder_id, "canonical_crossing_788")
        self.assertTrue(arrival.tags.has("the_landing", category="build"))

    def test_full_import_preserves_phase_tags_for_sample_rooms(self):
        rooms = ensure_full_canonical_crossing()

        self.assertEqual(rooms[788].db.canonical_phase, 1)
        self.assertEqual(rooms[768].db.canonical_phase, 2)
        self.assertEqual(rooms[769].db.canonical_phase, 3)
        self.assertEqual(rooms[838].db.canonical_phase, 4)
        self.assertEqual(rooms[899].db.canonical_phase, 5)
        self.assertEqual(rooms[895].db.canonical_phase, 6)
        self.assertEqual(rooms[7900].db.canonical_phase, "guildhall_stub")

    def test_zone_service_lists_the_landing_with_full_room_count(self):
        ensure_full_canonical_crossing()

        zones = zone_service.list_zones()
        self.assertIn("the_landing", zones)
        self.assertEqual(len(zones["the_landing"]["rooms"]), 253)

    def test_local_map_reports_the_landing_zone_for_canonical_room(self):
        ensure_full_canonical_crossing()

        arrival = import_canonical.get_canonical_crossing_arrival_room()
        payload = map_api.get_local_map(_ProbeCharacter(arrival))
        self.assertEqual(payload["zone"], "The Landing")

    def test_zone_map_reports_the_landing_zone_for_canonical_room(self):
        ensure_full_canonical_crossing()

        arrival = import_canonical.get_canonical_crossing_arrival_room()
        payload = map_api.get_zone_map(_ProbeCharacter(arrival))
        self.assertEqual(payload["zone"], "The Landing")
        self.assertGreaterEqual(len(payload["rooms"]), 31)

    def test_fixture_safety_still_preserves_canonical_room_after_full_import(self):
        rooms = ensure_full_canonical_crossing()
        arrival = rooms[788]

        result = safe_smoke_delete(arrival)

        self.assertEqual(list(result), [])
        self.assertEqual(result.filtered_count, 1)
        self.assertEqual(result.deleted_count, 0)
        self.assertEqual(import_canonical.get_canonical_crossing_arrival_room().id, arrival.id)

    def test_procedural_classifier_requires_new_landing_build_tag(self):
        feat_room = self._create_room("The Hall of Arcane Refinement", area="The Landing")
        feat_room.tags.add("landing-feat-trainers", category="build")
        procedural_room = self._create_room("Weathercrown Street, South Reach", area="New Landing")
        procedural_room.tags.add("new_landing", category="build")

        self.assertFalse(canonical_migration.is_procedural_landing_room(feat_room))
        self.assertTrue(canonical_migration.is_procedural_landing_room(procedural_room))

    def test_delete_procedural_landing_rooms_migrates_characters_and_deletes_targets(self):
        destination = self._create_room("Safe Destination", area="The Crossing")

        procedural_room = self._create_room("Weathercrown Street, South Reach", area="New Landing")
        procedural_room.tags.add("new_landing", category="build")
        character = self._create_character("Cleanup Traveler", location=procedural_room, home=procedural_room)
        prop = create_object("typeclasses.objects.Object", key="discarded crate", location=procedural_room, home=procedural_room)
        self.created.append(prop)

        with patch.object(canonical_migration, "iter_procedural_landing_rooms", return_value=[procedural_room]), patch.object(
            canonical_migration,
            "resolve_canonical_arrival_room",
            return_value=(destination, "fallback"),
        ):
            result = canonical_migration.delete_procedural_landing_rooms(fallback=lambda: destination)

        self.assertEqual(result["deleted_room_count"], 1)
        self.assertEqual(result["migrated_character_count"], 1)
        self.assertEqual(character.location, destination)
        self.assertEqual(character.home, destination)
        self.assertTrue(character.db.canonical_migrated)

    def test_tutorial_threshold_east_exit_targets_canonical_arrival(self):
        ensure_full_canonical_crossing()

        market_approach = self._create_room("Market Approach", area="Threshold Zone")
        canonical_arrival = import_canonical.get_canonical_crossing_arrival_room()
        self.assertIsNotNone(canonical_arrival)

        at_server_startstop._ensure_market_approach_canonical_exit(market_approach, canonical_arrival)

        landing_exit = at_server_startstop._find_exit(market_approach, "east")
        self.assertIsNotNone(landing_exit)
        self.assertEqual(getattr(getattr(landing_exit.destination, "db", None), "canonical_map_id", None), 788)


if __name__ == "__main__":
    unittest.main()