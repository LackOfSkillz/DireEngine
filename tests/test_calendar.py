import os
import datetime
import unittest
from unittest import mock

import django
from django.test import override_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses.rooms_extended import ExtendedDireRoom
from world import calendar


class TimeOfDayMappingTests(unittest.TestCase):
    def test_night_boundary_low(self):
        self.assertEqual(calendar._time_of_day_for_hour(0), "night")

    def test_night_boundary_high(self):
        self.assertEqual(calendar._time_of_day_for_hour(5), "night")

    def test_morning_boundary_low(self):
        self.assertEqual(calendar._time_of_day_for_hour(6), "morning")

    def test_morning_boundary_high(self):
        self.assertEqual(calendar._time_of_day_for_hour(11), "morning")

    def test_afternoon(self):
        self.assertEqual(calendar._time_of_day_for_hour(12), "afternoon")
        self.assertEqual(calendar._time_of_day_for_hour(17), "afternoon")

    def test_evening(self):
        self.assertEqual(calendar._time_of_day_for_hour(18), "evening")
        self.assertEqual(calendar._time_of_day_for_hour(23), "evening")


class SeasonMappingTests(unittest.TestCase):
    def test_winter_months(self):
        self.assertEqual(calendar._season_for_month(12), "winter")
        self.assertEqual(calendar._season_for_month(1), "winter")
        self.assertEqual(calendar._season_for_month(2), "winter")

    def test_spring_months(self):
        for month in (3, 4, 5):
            self.assertEqual(calendar._season_for_month(month), "spring")

    def test_summer_months(self):
        for month in (6, 7, 8):
            self.assertEqual(calendar._season_for_month(month), "summer")

    def test_autumn_months(self):
        for month in (9, 10, 11):
            self.assertEqual(calendar._season_for_month(month), "autumn")


class GetCurrentSeasonTests(unittest.TestCase):
    @override_settings(CALENDAR_TIMEZONE="America/New_York")
    def test_returns_one_of_known_seasons(self):
        self.assertIn(calendar.get_current_season(), calendar.SEASONS)

    @override_settings(CALENDAR_TIMEZONE="UTC")
    def test_with_utc_timezone(self):
        self.assertIn(calendar.get_current_season(), calendar.SEASONS)


class GetCurrentTimeOfDayTests(unittest.TestCase):
    @mock.patch("world.calendar.gametime")
    def test_returns_one_of_known_times(self, mock_gametime):
        mock_gametime.gametime.return_value = 1_717_171_717
        self.assertIn(calendar.get_current_time_of_day(), calendar.TIMES_OF_DAY)

    @mock.patch("world.calendar.gametime")
    def test_mocked_morning(self, mock_gametime):
        target = datetime.datetime(2026, 6, 15, 9, 0, 0, tzinfo=datetime.timezone.utc)
        mock_gametime.gametime.return_value = target.timestamp()
        self.assertEqual(calendar.get_current_time_of_day(), "morning")

    @mock.patch("world.calendar.gametime")
    def test_mocked_night(self, mock_gametime):
        target = datetime.datetime(2026, 6, 15, 2, 0, 0, tzinfo=datetime.timezone.utc)
        mock_gametime.gametime.return_value = target.timestamp()
        self.assertEqual(calendar.get_current_time_of_day(), "night")


class GetCalendarStateTests(unittest.TestCase):
    @override_settings(
        CALENDAR_TIMEZONE="America/New_York",
        TIME_FACTOR=4.0,
        TIME_IGNORE_DOWNTIMES=False,
    )
    @mock.patch("world.calendar.gametime")
    def test_state_shape(self, mock_gametime):
        mock_gametime.gametime.side_effect = [
            datetime.datetime(2026, 6, 15, 9, 0, 0, tzinfo=datetime.timezone.utc).timestamp(),
            176_580,
        ]
        state = calendar.get_calendar_state()
        self.assertIn("real_world", state)
        self.assertIn("game_time", state)
        self.assertIn("configuration", state)
        self.assertIn(state["real_world"]["season"], calendar.SEASONS)
        self.assertIn(state["game_time"]["time_of_day"], calendar.TIMES_OF_DAY)
        self.assertEqual(state["configuration"]["time_factor"], 4.0)
        self.assertEqual(state["configuration"]["ignore_downtimes"], False)


class ExtendedDireRoomCalendarIntegrationTests(unittest.TestCase):
    def test_get_season_delegates_to_calendar_module(self):
        room = ExtendedDireRoom.__new__(ExtendedDireRoom)
        with mock.patch("world.calendar.get_current_season", return_value="winter"):
            self.assertEqual(room.get_season(), "winter")

    def test_get_time_of_day_delegates_to_calendar_module(self):
        room = ExtendedDireRoom.__new__(ExtendedDireRoom)
        with mock.patch("world.calendar.get_current_time_of_day", return_value="morning"):
            self.assertEqual(room.get_time_of_day(), "morning")

    def test_get_stateful_desc_returns_seasonal_description(self):
        class StubRoom(ExtendedDireRoom):
            @property
            def room_states(self):
                return []

            def all_desc(self):
                return {None: "base desc", "winter": "winter desc"}

        room = StubRoom.__new__(StubRoom)
        with mock.patch("world.calendar.get_current_season", return_value="winter"):
            self.assertEqual(room.get_stateful_desc(), "winter desc")


if __name__ == "__main__":
    unittest.main()