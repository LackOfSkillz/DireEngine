import os
import random
import unittest
from types import SimpleNamespace
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.builder.prompting.room_description_prompt import _STATE_GROUP_VOCABULARY
from world import weather


class _AttrStore:
    def __init__(self):
        self._store = {}

    def add(self, key, value):
        self._store[key] = value

    def get(self, key, default=None):
        return self._store.get(key, default)


class _AttrQuery:
    def __init__(self, key, value):
        self.key = key
        self.value = value


class _AttrBackend:
    def __init__(self, store):
        self._store = store

    def filter(self, db_key__startswith=None):
        prefix = str(db_key__startswith or "")
        rows = [_AttrQuery(key, value) for key, value in self._store.items() if key.startswith(prefix)]
        return _AttrOrder(rows)


class _AttrOrder(list):
    def order_by(self, _field):
        return sorted(self, key=lambda row: row.key)


class _StubScript:
    def __init__(self):
        self.attributes = _AttrStore()
        self.db_attributes = _AttrBackend(self.attributes._store)
        self.db = SimpleNamespace(last_tick_iso=None)

    def time_until_next_repeat(self):
        return 10.0

    def start(self):
        return None


class _StubRoom:
    def __init__(self, name, structure=None, environment_type="urban"):
        self.key = name
        self.messages = []
        self.db = SimpleNamespace(
            room_tags={
                "structure": structure,
                "specific_function": None,
                "named_feature": None,
                "condition": None,
                "custom": [],
                "atmosphere": {
                    "materials": [],
                    "social_character": [],
                    "surroundings": [],
                    "sensory": [],
                    "upkeep": None,
                },
            },
            desc="",
            terrain_type="urban",
            environment_type=environment_type,
            world_id=name.lower().replace(" ", "_"),
        )

    def msg_contents(self, message):
        self.messages.append(message)


class WeatherLogicTests(unittest.TestCase):
    def test_resolve_climate_keywords(self):
        self.assertEqual(weather.resolve_climate("river-valley"), "coastal")
        self.assertEqual(weather.resolve_climate("arctic coast"), "subarctic")
        self.assertEqual(weather.resolve_climate("highland lake"), "alpine")

    @mock.patch("world.weather.logger")
    def test_resolve_climate_falls_back_with_warning(self, mock_logger):
        self.assertEqual(weather.resolve_climate("mystery climate"), "temperate")
        mock_logger.log_warn.assert_called()

    def test_weather_plausibility(self):
        self.assertTrue(weather.is_weather_plausible_for_climate("storm", "tropical"))
        self.assertFalse(weather.is_weather_plausible_for_climate("sandstorm", "temperate"))

    def test_transition_matrices_load(self):
        self.assertEqual(len(weather._TRANSITION_MATRICES), 32)
        self.assertIn("temperate__spring", weather._TRANSITION_MATRICES)

    def test_normalized_transition_row_filters_implausible_targets(self):
        matrix = {"clear": {"clear": 50, "sandstorm": 50}}
        row = weather._normalized_transition_row(matrix, "clear", "temperate")
        self.assertEqual(row, {"clear": 1.0})

    def test_pick_next_state_is_deterministic_with_seed(self):
        first = weather._pick_next_state("clear", "temperate", "spring", rng=random.Random(9))
        second = weather._pick_next_state("clear", "temperate", "spring", rng=random.Random(9))
        self.assertEqual(first, second)


class WeatherScriptedTests(unittest.TestCase):
    def setUp(self):
        self.script = _StubScript()
        self.zone_payloads = [
            {"zone_id": "crossingV2", "name": "The Crossing", "generation_context": {"climate": "river-valley", "setting_type": "city"}},
            {"zone_id": "new_landing", "name": "New Landing", "generation_context": {"climate": None, "setting_type": "city"}},
        ]

    def test_default_weather_is_clear(self):
        with mock.patch("world.weather._get_weather_script", return_value=self.script):
            self.assertEqual(weather.get_current_weather("crossingV2"), "clear")

    def test_set_current_weather_persists_in_script_store(self):
        with mock.patch("world.weather._get_weather_script", return_value=self.script):
            weather.set_current_weather("crossingV2", "heavy_rain")
            self.assertEqual(weather.get_current_weather("crossingV2"), "heavy_rain")

    def test_tick_weather_evaluates_all_known_zones(self):
        with (
            mock.patch("world.weather._get_weather_script", return_value=self.script),
            mock.patch("world.weather._iter_zone_payloads", return_value=self.zone_payloads),
            mock.patch("world.weather._pick_next_state", side_effect=["cloudy", "clear"]),
        ):
            transitions = weather.tick_weather()
        self.assertIn("crossingV2", transitions)
        self.assertNotIn("new_landing", transitions)

    def test_tick_weather_returns_changed_zones(self):
        with (
            mock.patch("world.weather._get_weather_script", return_value=self.script),
            mock.patch("world.weather._iter_zone_payloads", return_value=self.zone_payloads),
            mock.patch("world.weather._pick_next_state", side_effect=["cloudy", "fog"]),
        ):
            transitions = weather.tick_weather()
        self.assertEqual(transitions["crossingV2"], ("clear", "cloudy"))
        self.assertEqual(transitions["new_landing"], ("clear", "fog"))

    def test_multiple_ticks_keep_cloudy_transitions_reasonable(self):
        script = _StubScript()
        zone_payloads = [{"zone_id": "crossingV2", "name": "The Crossing", "generation_context": {"climate": "temperate", "setting_type": "city"}}]
        cloudy_count = 0
        with (
            mock.patch("world.weather._get_weather_script", return_value=script),
            mock.patch("world.weather._iter_zone_payloads", return_value=zone_payloads),
        ):
            for _ in range(100):
                transitions = weather.tick_weather()
                if weather.get_current_weather("crossingV2") == "cloudy" or transitions.get("crossingV2") == ("clear", "cloudy"):
                    cloudy_count += 1
                weather.set_current_weather("crossingV2", "clear", source="test")
        self.assertGreater(cloudy_count, 5)
        self.assertLess(cloudy_count, 60)


class WeatherMessagingTests(unittest.TestCase):
    def test_run_weather_cycle_broadcasts_tick_side_effects(self):
        rng = mock.Mock()
        rng.random.return_value = 0.0
        with (
            mock.patch("world.weather.tick_weather", return_value={"crossingV2": ("clear", "cloudy")}),
            mock.patch("world.weather.get_weather_state", return_value={"zones": [{"zone_id": "crossingV2", "weather": "storm"}, {"zone_id": "new_landing", "weather": "clear"}]}),
            mock.patch("world.weather._broadcast_weather_transition") as mock_transition,
            mock.patch("world.weather._broadcast_storm_lightning") as mock_lightning,
        ):
            transitions = weather.run_weather_cycle(rng=rng)

        self.assertEqual(transitions, {"crossingV2": ("clear", "cloudy")})
        mock_transition.assert_called_once_with("crossingV2", "clear", "cloudy")
        mock_lightning.assert_called_once_with("crossingV2", rng=rng)

    def test_transition_broadcast_hits_outdoor_not_interior(self):
        outdoor = _StubRoom("Square", structure="street")
        interior = _StubRoom("Hall", structure="hallway")
        with (
            mock.patch("world.weather._rooms_for_zone", return_value=[outdoor, interior]),
            mock.patch("world.weather._get_zone_payload", return_value={"zone_id": "crossingV2", "generation_context": {"setting_type": "city"}}),
        ):
            weather._broadcast_weather_transition("crossingV2", "clear", "cloudy")
        self.assertTrue(outdoor.messages)
        self.assertFalse(interior.messages)

    def test_threshold_rooms_get_softened_messages(self):
        threshold = _StubRoom("Gate", structure="threshold")
        with (
            mock.patch("world.weather._rooms_for_zone", return_value=[threshold]),
            mock.patch("world.weather._get_zone_payload", return_value={"zone_id": "crossingV2", "generation_context": {"setting_type": "city"}}),
        ):
            weather._broadcast_weather_transition("crossingV2", "clear", "cloudy")
        self.assertEqual(threshold.messages, ["The light outside dims as clouds gather."])

    def test_lightning_fires_in_storm(self):
        room = _StubRoom("Square", structure="street")
        script = _StubScript()
        with (
            mock.patch("world.weather._get_weather_script", return_value=script),
            mock.patch("world.weather._rooms_for_zone", return_value=[room]),
            mock.patch("world.weather._get_zone_payload", return_value={"zone_id": "crossingV2", "generation_context": {"setting_type": "city"}}),
        ):
            weather.set_current_weather("crossingV2", "storm")
            self.assertTrue(weather._broadcast_storm_lightning("crossingV2", rng=random.Random(1)))
        self.assertTrue(room.messages)

    def test_no_lightning_in_non_storm(self):
        room = _StubRoom("Square", structure="street")
        script = _StubScript()
        with (
            mock.patch("world.weather._get_weather_script", return_value=script),
            mock.patch("world.weather._rooms_for_zone", return_value=[room]),
            mock.patch("world.weather._get_zone_payload", return_value={"zone_id": "crossingV2", "generation_context": {"setting_type": "city"}}),
        ):
            weather.set_current_weather("crossingV2", "clear")
            self.assertFalse(weather._broadcast_storm_lightning("crossingV2", rng=random.Random(1)))
        self.assertFalse(room.messages)


class WeatherVocabularyTests(unittest.TestCase):
    def test_prompt_weather_vocab_contains_all_states(self):
        self.assertEqual(
            _STATE_GROUP_VOCABULARY["weather"],
            (
                "clear",
                "cloudy",
                "light_rain",
                "heavy_rain",
                "storm",
                "fog",
                "light_snow",
                "heavy_snow",
                "blizzard",
                "sandstorm",
            ),
        )


if __name__ == "__main__":
    unittest.main()