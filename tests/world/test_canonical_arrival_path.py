import json
import os
import tempfile
import unittest
from collections import deque
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from server.conf import at_server_startstop
from systems import canonical_migration, onboarding
from tests.fixtures.safe_smoke_delete import safe_smoke_delete
from world.areas.the_crossing import guildhall_stubs, import_canonical


class _DummyCharacter:
    def __init__(self, key="ArrivalTester", location=None, home=None):
        self.key = key
        self.location = location
        self.home = home
        self.moved_to = None
        self.messages = []
        self.db = SimpleNamespace(canonical_migrated=False, prelogout_location=None, canonical_migration_origin=None)

    def move_to(self, destination, quiet=True, use_destination=False):
        self.location = destination
        self.moved_to = {
            "destination": destination,
            "quiet": quiet,
            "use_destination": use_destination,
        }
        return True

    def msg(self, text, session=None):
        self.messages.append({"text": text, "session": session})


def _room(room_id, key, *, area=None, canonical_map_id=None, is_canonical_crossing=False):
    return SimpleNamespace(
        id=room_id,
        key=key,
        db=SimpleNamespace(
            area=area,
            canonical_map_id=canonical_map_id,
            is_canonical_crossing=is_canonical_crossing,
        ),
    )


def _sample_room(room_id, title, description, wayto, *, area_prefix="The Crossing"):
    commands = ", ".join(wayto.values())
    return {
        "id": room_id,
        "title": [f"[[{area_prefix}, {title}]]"],
        "description": [description],
        "paths": [f"Obvious paths: {commands}." if commands else "Obvious paths: out."],
        "wayto": wayto,
        "timeto": {destination: 1 for destination in wayto},
        "image": "zoluren-1-crossing-1377284934.png",
        "image_coords": [0, 0, 1, 1],
        "tags": [],
    }


def _reachable_map_ids(start_room):
    seen = set()
    queue = deque([start_room])
    reached = set()
    while queue:
        room = queue.popleft()
        room_id = getattr(room, "id", None)
        if room_id in seen or room_id is None:
            continue
        seen.add(room_id)
        canonical_map_id = getattr(getattr(room, "db", None), "canonical_map_id", None)
        if canonical_map_id is not None:
            reached.add(int(canonical_map_id))
        for exit_obj in list(getattr(room, "exits", []) or []):
            destination = getattr(exit_obj, "destination", None)
            if destination is not None:
                queue.append(destination)
    return reached


class CanonicalArrivalPathTests(unittest.TestCase):
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

    def _create_room(self, key, *, area=None, canonical_map_id=None, is_canonical_crossing=False):
        room = create_object("typeclasses.rooms.Room", key=key, nohome=True)
        room.db.area = area
        room.db.canonical_map_id = canonical_map_id
        room.db.is_canonical_crossing = is_canonical_crossing
        self.created.append(room)
        return room

    def test_release_to_world_prefers_canonical_arrival_room(self):
        character = _DummyCharacter()
        canonical_room = _room(47727, "Town Green North", canonical_map_id=788, is_canonical_crossing=True)
        recovery_room = _room(13212, "Empath Guild", area="Empath Guild")

        with patch.object(onboarding, "_cleanup_scripted_enemy"), patch.object(onboarding, "_set_between_state"), patch.object(
            onboarding, "_set_training_collapse"
        ), patch.object(onboarding, "set_onboarding_step"), patch.object(onboarding, "_resolve_recovery_destination", return_value=recovery_room), patch(
            "server.conf.at_server_startstop._resolve_landing_arrival_room", return_value=canonical_room
        ), patch("systems.aftermath.activate_new_player_state"), patch("systems.aftermath.note_room_entry"), patch.object(
            onboarding.logger, "log_info"
        ):
            ok, message = onboarding.release_to_world(character)

        self.assertTrue(ok)
        self.assertEqual(message, "")
        self.assertIs(character.location, canonical_room)
        self.assertIs(character.home, canonical_room)
        self.assertIs(character.moved_to["destination"], canonical_room)

    def test_release_to_world_falls_back_to_recovery_destination(self):
        character = _DummyCharacter()
        recovery_room = _room(13212, "Empath Guild", area="Empath Guild")

        with patch.object(onboarding, "_cleanup_scripted_enemy"), patch.object(onboarding, "_set_between_state"), patch.object(
            onboarding, "_set_training_collapse"
        ), patch.object(onboarding, "set_onboarding_step"), patch.object(onboarding, "_resolve_recovery_destination", return_value=recovery_room), patch(
            "server.conf.at_server_startstop._resolve_landing_arrival_room", return_value=None
        ), patch("systems.aftermath.activate_new_player_state"), patch("systems.aftermath.note_room_entry"), patch.object(
            onboarding.logger, "log_info"
        ):
            ok, message = onboarding.release_to_world(character)

        self.assertTrue(ok)
        self.assertEqual(message, "")
        self.assertIs(character.location, recovery_room)
        self.assertIs(character.home, recovery_room)
        self.assertIs(character.moved_to["destination"], recovery_room)

    def test_returning_character_migration_moves_procedural_login_to_canonical_arrival(self):
        procedural_room = _room(4254, "Elmbrook Lane, Midway", area="New Landing")
        canonical_room = _room(47727, "Town Green North", canonical_map_id=788, is_canonical_crossing=True)
        character = _DummyCharacter(location=procedural_room, home=procedural_room)
        character.db.prelogout_location = procedural_room
        session = object()

        with patch("server.conf.at_server_startstop._resolve_landing_arrival_room", return_value=canonical_room):
            migrated, destination = canonical_migration.migrate_character_to_canonical_arrival(character, session=session)

        self.assertTrue(migrated)
        self.assertIs(destination, canonical_room)
        self.assertIs(character.location, canonical_room)
        self.assertIs(character.home, canonical_room)
        self.assertIs(character.db.prelogout_location, canonical_room)
        self.assertTrue(character.db.canonical_migrated)
        self.assertEqual(character.db.canonical_migration_origin, 4254)
        self.assertEqual(character.messages[0]["text"], canonical_migration.CANONICAL_MIGRATION_MESSAGE)
        self.assertIs(character.messages[0]["session"], session)

    def test_returning_character_migration_is_idempotent_once_location_is_canonical(self):
        canonical_room = _room(47727, "Town Green North", canonical_map_id=788, is_canonical_crossing=True)
        character = _DummyCharacter(location=canonical_room, home=canonical_room)
        character.db.canonical_migrated = True
        character.db.prelogout_location = canonical_room

        migrated, destination = canonical_migration.migrate_character_to_canonical_arrival(character)

        self.assertFalse(migrated)
        self.assertIs(destination, canonical_room)
        self.assertEqual(character.messages, [])

    def test_market_approach_exit_targets_canonical_arrival(self):
        market_approach = self._create_room("Market Approach", area="Threshold Zone")
        canonical_room = self._create_room("Town Green North", area="The Crossing", canonical_map_id=788, is_canonical_crossing=True)

        at_server_startstop._ensure_market_approach_canonical_exit(market_approach, canonical_room)

        landing_exit = at_server_startstop._find_exit(market_approach, "east")
        self.assertIsNotNone(landing_exit)
        self.assertIs(landing_exit.destination, canonical_room)
        self.assertEqual(getattr(getattr(landing_exit.destination, "db", None), "canonical_map_id", None), 788)

    def test_procedural_bridge_routes_bellfound_steps_to_canonical_arrival(self):
        bellfound_steps = self._create_room("Bellfound Steps", area="New Landing")
        canonical_room = self._create_room("Town Green North", area="The Crossing", canonical_map_id=788, is_canonical_crossing=True)

        with patch.object(at_server_startstop, "_find_procedural_canonical_bridge_room", return_value=bellfound_steps):
            bridge_exit = at_server_startstop._ensure_procedural_canonical_bridge(canonical_room)

        self.assertIsNotNone(bridge_exit)
        self.assertEqual(bridge_exit.key, at_server_startstop.PROCEDURAL_CANONICAL_BRIDGE_EXIT_KEY)
        self.assertIs(bridge_exit.location, bellfound_steps)
        self.assertIs(bridge_exit.destination, canonical_room)
        self.assertTrue(bool(getattr(bridge_exit.db, "is_canonical_arrival_bridge", False)))
        self.assertEqual(getattr(bridge_exit.db, "bridge_target_canonical_map_id", None), 788)

    def test_resolver_still_prefers_canonical_arrival_when_present(self):
        canonical_room = _room(47727, "Town Green North", area="The Crossing", canonical_map_id=788, is_canonical_crossing=True)

        with patch.object(at_server_startstop, "get_canonical_crossing_arrival_room", return_value=canonical_room):
            resolved = at_server_startstop._resolve_landing_arrival_room()

        self.assertIs(resolved, canonical_room)

    def test_audit_stub_destinations_are_reachable_from_canonical_arrival(self):
        arrival_room = at_server_startstop._resolve_landing_arrival_room()
        self.assertIsNotNone(arrival_room)
        reached = _reachable_map_ids(arrival_room)
        self.assertTrue({7898, 5990, 5713, 7888, 823, 958, 7900, 9077}.issubset(reached))


if __name__ == "__main__":
    unittest.main()