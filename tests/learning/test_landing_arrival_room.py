import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from server.conf import at_server_startstop


def _room(room_id, area, region, key):
    return SimpleNamespace(
        id=room_id,
        key=key,
        db=SimpleNamespace(area=area, region_name=region),
    )


class LandingArrivalRoomTests(unittest.TestCase):
    def test_resolver_prefers_new_landing_map_rooms_over_legacy_landing_rooms(self):
        rooms = [
            _room(10, "The Landing", "The Landing", "The Strength Society"),
            _room(20, "New Landing", "Upper Crossing", "Amberwick Lane, Midway"),
            _room(30, "New Landing", "Central Crossing", "Briar Crown Street and Pennybright Lane"),
        ]

        with patch.object(at_server_startstop, "get_canonical_crossing_arrival_room", return_value=None), patch.object(
            at_server_startstop.ObjectDB.objects, "filter", return_value=rooms
        ):
            resolved = at_server_startstop._resolve_landing_arrival_room()

        self.assertIs(resolved, rooms[2])

    def test_resolver_prefers_canonical_crossing_arrival_when_present(self):
        canonical_room = _room(99, "The Crossing", "The Crossing", "Town Green North")

        with patch.object(at_server_startstop, "get_canonical_crossing_arrival_room", return_value=canonical_room):
            resolved = at_server_startstop._resolve_landing_arrival_room()

        self.assertIs(resolved, canonical_room)

    def test_resolver_falls_back_to_legacy_landing_rooms_when_map_rooms_are_missing(self):
        rooms = [
            _room(10, "The Landing", "The Landing", "The Strength Society"),
            _room(11, "The Landing", "The Landing", "Town Green NE"),
        ]

        with patch.object(at_server_startstop, "get_canonical_crossing_arrival_room", return_value=None), patch.object(
            at_server_startstop.ObjectDB.objects, "filter", return_value=rooms
        ):
            resolved = at_server_startstop._resolve_landing_arrival_room()

        self.assertIs(resolved, rooms[0])

    def test_tutorial_build_check_rejects_legacy_landing_exit_targets(self):
        rooms_by_key = {
            "Intake Chamber": _room(1, "New Player Onboarding", "Onboarding", "Intake Chamber"),
            "Training Hall": _room(2, "New Player Onboarding", "Onboarding", "Training Hall"),
            "Practice Yard": _room(3, "New Player Onboarding", "Onboarding", "Practice Yard"),
            "Outer Yard": _room(4, "Threshold Zone", "Threshold", "Outer Yard"),
            "Market Approach": _room(5, "Threshold Zone", "Threshold", "Market Approach"),
            "Side Passage": _room(6, "Threshold Zone", "Threshold", "Side Passage"),
        }
        legacy_destination = _room(7, "The Landing", "The Landing", "The Strength Society")
        legacy_exit = SimpleNamespace(destination=legacy_destination)

        def _fake_filter(**kwargs):
            return SimpleNamespace(first=lambda: rooms_by_key.get(kwargs.get("db_key__iexact")))

        with patch.object(at_server_startstop.ObjectDB.objects, "filter", side_effect=_fake_filter), patch.object(
            at_server_startstop, "_find_exit", return_value=legacy_exit
        ):
            built = at_server_startstop._new_player_tutorial_is_built()

        self.assertFalse(built)

    def test_tutorial_build_check_accepts_canonical_crossing_arrival_targets(self):
        rooms_by_key = {
            "Intake Chamber": _room(1, "New Player Onboarding", "Onboarding", "Intake Chamber"),
            "Training Hall": _room(2, "New Player Onboarding", "Onboarding", "Training Hall"),
            "Practice Yard": _room(3, "New Player Onboarding", "Onboarding", "Practice Yard"),
            "Outer Yard": _room(4, "Threshold Zone", "Threshold", "Outer Yard"),
            "Market Approach": _room(5, "Threshold Zone", "Threshold", "Market Approach"),
            "Side Passage": _room(6, "Threshold Zone", "Threshold", "Side Passage"),
        }
        canonical_destination = _room(7, "The Crossing", "The Crossing", "Town Green North")
        canonical_destination.db.is_canonical_crossing = True
        canonical_exit = SimpleNamespace(destination=canonical_destination)

        def _fake_filter(**kwargs):
            return SimpleNamespace(first=lambda: rooms_by_key.get(kwargs.get("db_key__iexact")))

        with patch.object(at_server_startstop.ObjectDB.objects, "filter", side_effect=_fake_filter), patch.object(
            at_server_startstop, "_find_exit", return_value=canonical_exit
        ):
            built = at_server_startstop._new_player_tutorial_is_built()

        self.assertTrue(built)


if __name__ == "__main__":
    unittest.main()