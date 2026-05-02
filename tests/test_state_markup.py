import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from engine.render import state_markup
from typeclasses.rooms_extended import ExtendedDireRoom


class StateMarkupParserTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()

    def test_parse_plain_text(self):
        result = state_markup.parse_state_markup("Plain text only.")
        self.assertEqual(result.errors, ())
        self.assertEqual(result.ast, (state_markup.TextNode("Plain text only."),))

    def test_parse_single_fragment(self):
        result = state_markup.parse_state_markup("Start $state(weather:storm, rain) end")
        self.assertEqual(
            result.ast,
            (
                state_markup.TextNode("Start "),
                state_markup.StateNode(group="weather", values=("storm",), content=" rain"),
                state_markup.TextNode(" end"),
            ),
        )

    def test_parse_multiple_fragments(self):
        result = state_markup.parse_state_markup(
            "A$state(weather:storm, rain)B$state(invasion:goblin_raid, danger)C"
        )
        self.assertEqual(len(result.ast), 5)
        self.assertEqual(result.ast[1].group, "weather")
        self.assertEqual(result.ast[3].group, "invasion")

    def test_parse_multi_value_fragment(self):
        result = state_markup.parse_state_markup("$state(weather:storm|heavy_rain, rain)")
        self.assertEqual(result.ast[0].values, ("storm", "heavy_rain"))

    def test_parse_unbalanced_parens(self):
        result = state_markup.parse_state_markup("Before $state(weather:storm, rain")
        self.assertEqual(result.ast, (state_markup.TextNode("Before "),))
        self.assertEqual(len(result.errors), 1)

    def test_parse_missing_colon(self):
        result = state_markup.parse_state_markup("Before $state(weather, rain) after")
        self.assertEqual(
            result.ast,
            (
                state_markup.TextNode("Before "),
                state_markup.TextNode(" after"),
            ),
        )
        self.assertEqual(len(result.errors), 1)

    def test_parse_empty_description(self):
        result = state_markup.parse_state_markup("")
        self.assertEqual(result.ast, ())
        self.assertEqual(result.errors, ())

    def test_parse_literal_dollar_state(self):
        result = state_markup.parse_state_markup("$states are interesting")
        self.assertEqual(result.ast, (state_markup.TextNode("$states are interesting"),))


class StateMarkupRegistryTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()
        self.context = state_markup.RenderContext(room=SimpleNamespace(key="Test Room", id=7), zone_id="fixture_zone")

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="storm")
    def test_registry_resolves_weather(self, _mock_weather):
        rendered = state_markup.render_state_markup(
            "A $state(weather:storm, rain)",
            self.context,
        )
        self.assertEqual(rendered, "A  rain")

    @mock.patch("engine.render.state_markup.get_current_invasion", return_value="goblin_raid")
    def test_registry_resolves_invasion(self, _mock_invasion):
        rendered = state_markup.render_state_markup("$state(invasion:goblin_raid, danger)", self.context)
        self.assertEqual(rendered, " danger")

    @mock.patch("engine.render.state_markup.get_current_season", return_value="winter")
    def test_registry_resolves_season(self, _mock_season):
        rendered = state_markup.render_state_markup("$state(season:winter, frost)", self.context)
        self.assertEqual(rendered, " frost")

    @mock.patch("engine.render.state_markup.get_current_time_of_day", return_value="night")
    def test_registry_resolves_time(self, _mock_time):
        rendered = state_markup.render_state_markup("$state(time:night, dark)", self.context)
        self.assertEqual(rendered, " dark")

    @mock.patch("engine.render.state_markup.logger")
    def test_registry_unknown_group_logs_warning(self, mock_logger):
        rendered = state_markup.render_state_markup("A$state(terrain:urban, x)B", self.context)
        self.assertEqual(rendered, "AB")
        mock_logger.log_warn.assert_called()

    @mock.patch("engine.render.state_markup.logger")
    def test_registry_query_error_logs_warning(self, mock_logger):
        with mock.patch.dict(state_markup.STATE_GROUPS, {"weather": mock.Mock(side_effect=RuntimeError("boom"))}):
            rendered = state_markup.render_state_markup("A$state(weather:storm, x)B", self.context)
        self.assertEqual(rendered, "AB")
        mock_logger.log_warn.assert_called()


class StateMarkupRendererTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()
        self.context = state_markup.RenderContext(room=SimpleNamespace(key="Test Room", id=8), zone_id="fixture_zone")

    def test_render_no_fragments_returns_text(self):
        self.assertEqual(state_markup.render_state_markup("No markup.", self.context), "No markup.")

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="storm")
    def test_render_matching_fragment_includes_content(self, _mock_weather):
        rendered = state_markup.render_state_markup("A$state(weather:storm, rain)B", self.context)
        self.assertEqual(rendered, "A rainB")

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="clear")
    def test_render_non_matching_fragment_empty(self, _mock_weather):
        rendered = state_markup.render_state_markup("A$state(weather:storm, rain)B", self.context)
        self.assertEqual(rendered, "AB")

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="heavy_rain")
    def test_render_multi_value_matches_any(self, _mock_weather):
        rendered = state_markup.render_state_markup("A$state(weather:storm|heavy_rain, rain)B", self.context)
        self.assertEqual(rendered, "A rainB")

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="storm")
    @mock.patch("engine.render.state_markup.get_current_invasion", return_value="none")
    def test_render_mixed_matches(self, _mock_invasion, _mock_weather):
        rendered = state_markup.render_state_markup(
            "A$state(weather:storm, rain)$state(invasion:goblin_raid, danger)B",
            self.context,
        )
        self.assertEqual(rendered, "A rainB")

    @mock.patch("engine.render.state_markup.get_current_weather", side_effect=["clear", "storm"])
    def test_render_state_change_changes_output(self, _mock_weather):
        text = "A$state(weather:storm, rain)B"
        self.assertEqual(state_markup.render_state_markup(text, self.context), "AB")
        self.assertEqual(state_markup.render_state_markup(text, self.context), "A rainB")


class StateMarkupCachingTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()

    def test_ast_cached_for_same_description(self):
        first = state_markup.get_cached_parse_result("A$state(weather:storm, rain)B")
        second = state_markup.get_cached_parse_result("A$state(weather:storm, rain)B")
        self.assertIs(first, second)

    def test_ast_recomputed_for_changed_description(self):
        first = state_markup.get_cached_parse_result("A$state(weather:storm, rain)B")
        second = state_markup.get_cached_parse_result("A$state(weather:clear, calm)B")
        self.assertIsNot(first, second)

    @mock.patch("engine.render.state_markup.get_current_weather", side_effect=["storm", "clear"])
    def test_cache_does_not_leak_across_rooms(self, _mock_weather):
        room_one = SimpleNamespace(key="One", id=1)
        room_two = SimpleNamespace(key="Two", id=2)
        description = "A$state(weather:storm, rain)B"
        rendered_one = state_markup.render_state_markup(description, state_markup.RenderContext(room=room_one, zone_id="zone_one"))
        rendered_two = state_markup.render_state_markup(description, state_markup.RenderContext(room=room_two, zone_id="zone_two"))
        self.assertEqual(rendered_one, "A rainB")
        self.assertEqual(rendered_two, "AB")


class StateMarkupIntegrationTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()

    @staticmethod
    def _build_room(*, room_states=None, descriptions=None, zone_id="fixture_zone"):
        class StubRoom:
            fallback_desc = "You see nothing special."

            def __init__(self):
                self.key = "Stub Room"
                self.id = 99
                self.db = SimpleNamespace(zone_id=zone_id)

            @property
            def room_states(self):
                return list(room_states or [])

            def all_desc(self):
                return dict(descriptions or {})

            def get_season(self):
                return ExtendedDireRoom.get_season(self)

            def _select_stateful_desc(self):
                return ExtendedDireRoom._select_stateful_desc(self)

        return StubRoom()

    def test_get_stateful_desc_renders_markup(self):
        room = self._build_room(room_states=[], descriptions={None: "A$state(weather:storm, rain)B"})
        with mock.patch("engine.render.state_markup.get_current_weather", return_value="storm"):
            self.assertEqual(ExtendedDireRoom.get_stateful_desc(room), "A rainB")

    def test_desc_state_variant_with_markup(self):
        room = self._build_room(
            room_states=["storm"],
            descriptions={
                None: "base",
                "storm": "Storm room.$state(invasion:goblin_raid, Goblin tracks.)",
            },
        )
        room.id = 100
        with mock.patch("engine.render.state_markup.get_current_invasion", return_value="goblin_raid"):
            self.assertEqual(ExtendedDireRoom.get_stateful_desc(room), "Storm room. Goblin tracks.")

    def test_no_markup_no_change_in_behavior(self):
        room = self._build_room(room_states=[], descriptions={None: "base desc", "winter": "winter desc"})
        room.id = 101
        with mock.patch("world.calendar.get_current_season", return_value="winter"):
            self.assertEqual(ExtendedDireRoom.get_stateful_desc(room), "winter desc")


class StateMarkupErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()
        self.context = state_markup.RenderContext(room=SimpleNamespace(key="Test Room", id=9), zone_id="fixture_zone")

    @mock.patch("engine.render.state_markup.logger")
    def test_malformed_fragment_is_stripped_and_logged(self, mock_logger):
        rendered = state_markup.render_state_markup("Before $state(weather, rain) after", self.context)
        self.assertEqual(rendered, "Before  after")
        mock_logger.log_warn.assert_called()


class StateMarkupPerformanceTests(unittest.TestCase):
    def setUp(self):
        state_markup.clear_parse_cache()

    @mock.patch("engine.render.state_markup.get_current_weather", return_value="storm")
    def test_render_completes_within_bounded_time(self, _mock_weather):
        context = state_markup.RenderContext(room=SimpleNamespace(key="Test Room", id=10), zone_id="fixture_zone")
        text = (
            "A small clearing. $state(weather:storm|heavy_rain, Rain pelts the ground.) "
            "$state(invasion:goblin_raid, A goblin's footprints are scattered nearby.) The trees sway gently."
        )
        state_markup.render_state_markup(text, context)
        start = time.perf_counter()
        for _ in range(500):
            state_markup.render_state_markup(text, context)
        average = (time.perf_counter() - start) / 500
        self.assertLess(average, 0.005)


if __name__ == "__main__":
    unittest.main()