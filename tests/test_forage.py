import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from typeclasses import abilities_survival as survival
from commands.cmd_forage import CmdForage


class _DummyRoom:
    def __init__(
        self,
        *,
        zone_id="test_zone",
        terrain_primary=None,
        terrain_secondary=None,
        terrain_type=None,
        environment_type="wilderness",
        room_tags=None,
        forage_difficulty=35,
    ):
        self.key = "Test Room"
        self.db = SimpleNamespace(
            zone_id=zone_id,
            terrain_primary=terrain_primary,
            terrain_secondary=terrain_secondary,
            terrain_type=terrain_type,
            environment_type=environment_type,
            room_tags=room_tags,
            forage_difficulty=forage_difficulty,
            desc="",
        )

    def get_environment_type(self):
        return self.db.environment_type

    def get_terrain_type(self):
        return self.db.terrain_type


class _DummyUser:
    def __init__(self, room, *, rank=0, wisdom=10, intelligence=10, profession=None):
        self.location = room
        self.db = SimpleNamespace(forage_uses=0)
        self._rank = rank
        self._wisdom = wisdom
        self._intelligence = intelligence
        self._profession = profession
        self.messages = []
        self.skill_uses = []

    def get_skill(self, key):
        if key == "outdoorsmanship":
            return self._rank
        return 0

    def get_stat(self, key):
        if key == "wisdom":
            return self._wisdom
        if key == "intelligence":
            return self._intelligence
        return 0

    def is_profession(self, key):
        return str(self._profession or "").strip().lower() == str(key or "").strip().lower()

    def use_skill(self, skill, **kwargs):
        self.skill_uses.append((skill, kwargs))

    def msg(self, text):
        self.messages.append(str(text))


def _entry(slug, *, terrain, indoor=False, skill_ranks=0, seasonal=None, time_of_day=None, category="flora"):
    return {
        "group": "test",
        "slug": slug,
        "display_name": slug.replace("_", " "),
        "terrain": list(terrain),
        "indoor": indoor,
        "skill_ranks": skill_ranks,
        "seasonal": list(seasonal or ["all"]),
        "time_of_day": list(time_of_day or ["all"]),
        "category": category,
    }


class ForageBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.default_catalog = (
            _entry("forest_branch", terrain=["forest"]),
            _entry("coastal_shell", terrain=["coastal"]),
            _entry("urban_scrap", terrain=["urban"], indoor=True),
            _entry("night_bloom", terrain=["forest"], time_of_day=["night"]),
            _entry("day_bloom", terrain=["forest"], time_of_day=["day"]),
            _entry("summer_berry", terrain=["forest"], seasonal=["summer"]),
            _entry("rare_herb", terrain=["forest"], skill_ranks=25, category="healing_herb"),
            _entry("grass", terrain=["outdoor"], category="flora"),
            _entry("stick", terrain=["outdoor"], category="wood"),
        )
        self.catalog_by_slug = {entry["slug"]: entry for entry in self.default_catalog}
        patchers = [
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=self.default_catalog),
            mock.patch("typeclasses.abilities_survival.get_current_season", return_value="summer"),
            mock.patch("typeclasses.abilities_survival.get_current_time_of_day", return_value="afternoon"),
            mock.patch("typeclasses.abilities_survival.get_current_weather", return_value="clear"),
            mock.patch("typeclasses.abilities_survival.get_current_invasion", return_value="none"),
        ]
        self._patchers = patchers
        for patcher in self._patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        for patcher in reversed(self._patchers):
            patcher.stop()

    def test_terrain_filters_pool(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="afternoon", effective_rank=100)
        slugs = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertIn("forest_branch", slugs)
        self.assertNotIn("coastal_shell", slugs)

    def test_gather_alias_routes_to_forage_command(self):
        self.assertIn("gather", CmdForage.aliases)

    def test_forage_ability_has_no_rank_gate(self):
        ability = survival.ForageAbility()
        self.assertEqual(ability.required, {})
        self.assertEqual(ability.visible_if, {})

    def test_secondary_terrain_blends(self):
        room = _DummyRoom(terrain_primary="forest", terrain_secondary="coastal", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="afternoon", effective_rank=100)
        weights = {entry["entry"]["slug"]: entry["terrain_weight"] for entry in filtered["pre_skill_entries"]}
        self.assertEqual(weights["forest_branch"], survival.PRIMARY_TERRAIN_WEIGHT)
        self.assertEqual(weights["coastal_shell"], survival.SECONDARY_TERRAIN_WEIGHT)

    def test_no_terrain_falls_back(self):
        room = _DummyRoom(terrain_primary=None, terrain_secondary=None, terrain_type=None)
        user = _DummyUser(room, rank=20, profession="ranger")
        with mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "success"}):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertTrue(result["used_legacy"])
        self.assertEqual(result["status"], "success")

    def test_season_filter_active(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="winter", time_of_day="afternoon", effective_rank=100)
        slugs = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertNotIn("summer_berry", slugs)

    def test_time_of_day_filter_day_includes_evening(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="evening", effective_rank=100)
        slugs = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertIn("day_bloom", slugs)

    def test_time_of_day_filter_night_excludes_evening(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="evening", effective_rank=100)
        slugs = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertNotIn("night_bloom", slugs)

    def test_indoor_outdoor_filter(self):
        room = _DummyRoom(
            terrain_primary="urban",
            terrain_type="urban",
            environment_type="urban",
            room_tags={"structure": "building-interior"},
        )
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="afternoon", effective_rank=100)
        slugs = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertEqual(slugs, {"urban_scrap"})

    def test_skill_threshold_filter(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        filtered = survival._filter_catalog_entries(room, season="summer", time_of_day="afternoon", effective_rank=10)
        slugs = {entry["entry"]["slug"] for entry in filtered["pre_skill_entries"]}
        allowed = {entry["entry"]["slug"] for entry in filtered["entries"]}
        self.assertIn("rare_herb", slugs)
        self.assertNotIn("rare_herb", allowed)

    def test_clear_weather_baseline(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            clear = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(clear["status"], "success")
        self.assertEqual(clear["yield_amount"], 5)

    def test_storm_severe_yield_penalty(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival.get_current_weather", return_value="storm"),
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            storm = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(storm["status"], "success")
        self.assertLess(storm["yield_amount"], 5)

    def test_storm_does_not_hard_block(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival.get_current_weather", return_value="storm"),
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["yield_amount"], 1)

    def test_invasion_yield_modifier(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            baseline = survival.forage_attempt(user, room, create_items=False)
        with (
            mock.patch("typeclasses.abilities_survival.get_current_invasion", return_value="goblin_raid"),
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            invaded = survival.forage_attempt(user, room, create_items=False)
        self.assertLess(invaded["yield_amount"], baseline["yield_amount"])

    def test_no_invasion_no_modifier(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["invasion_state"], "none")

    def test_ranger_gets_skill_bonus(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        non_ranger = _DummyUser(room, rank=10)
        ranger = _DummyUser(room, rank=10, profession="ranger")
        gated_catalog = (_entry("rare_herb", terrain=["forest"], skill_ranks=25, category="healing_herb"),)
        with (
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=gated_catalog),
            mock.patch("engine.services.skill_service.SkillService.award_xp"),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "success"}),
        ):
            baseline = survival.forage_attempt(non_ranger, room, create_items=False)
            boosted = survival.forage_attempt(ranger, room, create_items=False)
        self.assertEqual(baseline["status"], "skill_failure")
        self.assertEqual(boosted["status"], "success")

    def test_ranger_gets_quality_bonus(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        non_ranger = _DummyUser(room, rank=80)
        ranger = _DummyUser(room, rank=80, profession="ranger")
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "success"}),
        ):
            baseline = survival.forage_attempt(non_ranger, room, create_items=False)
            boosted = survival.forage_attempt(ranger, room, create_items=False)
        self.assertEqual(baseline["quality"], "useful")
        self.assertEqual(boosted["quality"], "high-quality")

    def test_ranger_gets_quantity_bonus(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        non_ranger = _DummyUser(room, rank=80)
        ranger = _DummyUser(room, rank=80, profession="ranger")
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "success"}),
        ):
            baseline = survival.forage_attempt(non_ranger, room, create_items=False)
            boosted = survival.forage_attempt(ranger, room, create_items=False)
        self.assertGreater(boosted["yield_amount"], baseline["yield_amount"])

    def test_non_ranger_baseline(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "success"}),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["quality"], "useful")
        self.assertEqual(result["yield_amount"], 4)

    def test_skill_too_low_message(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=0)
        gated_catalog = (_entry("rare_herb", terrain=["forest"], skill_ranks=25, category="healing_herb"),)
        with (
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=gated_catalog),
            mock.patch("engine.services.skill_service.SkillService.award_xp"),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["status"], "skill_failure")
        self.assertEqual(result["failure_reason"], "skill_too_low")
        self.assertIn("within your skill", result["message"])

    def test_rank_zero_character_can_attempt_forage(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=0)
        gated_catalog = (_entry("rare_herb", terrain=["forest"], skill_ranks=25, category="healing_herb"),)
        with (
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=gated_catalog),
            mock.patch("engine.services.skill_service.SkillService.award_xp"),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "skill_failure")

    def test_skill_too_low_failure_awards_quarter_learning(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=0)
        gated_catalog = (_entry("rare_herb", terrain=["forest"], skill_ranks=25, category="healing_herb"),)
        with (
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=gated_catalog),
            mock.patch("engine.services.skill_service.SkillService.award_xp") as award_xp,
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["status"], "skill_failure")
        award_xp.assert_called_once()
        _, args, kwargs = award_xp.mock_calls[0]
        self.assertEqual(args[:3], (user, "outdoorsmanship", 25))
        self.assertEqual(kwargs["source"], {"mode": "difficulty"})
        self.assertFalse(kwargs["success"])
        self.assertEqual(kwargs["outcome"], "failure")
        self.assertEqual(kwargs["event_key"], "forage")
        self.assertEqual(kwargs["context_multiplier"], survival.FORAGE_FAILURE_XP_MULTIPLIER)

    def test_weather_blocked_message(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=0)
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.get_current_weather", return_value="storm"),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "fail"}),
        ):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["status"], "weather_failure")
        self.assertEqual(result["failure_reason"], "weather_blocked")
        self.assertIn("storm", result["message"])
        self.assertEqual(user.skill_uses, [])

    def test_generic_failure_message(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80)
        with mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "fail"}):
            result = survival.forage_attempt(user, room, create_items=False)
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["failure_reason"], "generic_no_result")
        self.assertIn("nothing of value", result["message"])
        self.assertEqual(user.skill_uses, [])

    def test_forage_attempt_completes_within_bounded_time(self):
        room = _DummyRoom(terrain_primary="forest", terrain_type="forest")
        user = _DummyUser(room, rank=80, profession="ranger")
        with (
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=self.catalog_by_slug["forest_branch"]),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            survival.forage_attempt(user, room, create_items=False)
            started = time.monotonic()
            survival.forage_attempt(user, room, create_items=False)
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.100, f"forage_attempt() took {elapsed:.3f}s, expected < 0.100s")