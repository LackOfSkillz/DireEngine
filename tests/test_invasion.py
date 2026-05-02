import os
import unittest
from types import SimpleNamespace
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world import invasion


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
        self.db = SimpleNamespace(last_started_iso=None)
        self.is_active = True

    def start(self):
        return None


class InvasionStateTests(unittest.TestCase):
    def setUp(self):
        self.script = _StubScript()
        self.zone_payloads = [
            {"zone_id": "crossingV2", "name": "The Crossing"},
            {"zone_id": "new_landing", "name": "New Landing"},
        ]

    def test_default_invasion_is_none(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            self.assertEqual(invasion.get_current_invasion("crossingV2"), "none")

    def test_set_and_get_invasion(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            invasion.set_current_invasion("crossingV2", "siege")
            self.assertEqual(invasion.get_current_invasion("crossingV2"), "siege")

    def test_invalid_invasion_type_raises(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            with self.assertRaises(ValueError):
                invasion.set_current_invasion("crossingV2", "not_a_real_type")

    def test_is_zone_invaded(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            self.assertFalse(invasion.is_zone_invaded("crossingV2"))
            invasion.set_current_invasion("crossingV2", "goblin_raid")
            self.assertTrue(invasion.is_zone_invaded("crossingV2"))

    def test_clear_invasion_with_none(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            invasion.set_current_invasion("crossingV2", "goblin_raid")
            invasion.set_current_invasion("crossingV2", "none")
            self.assertEqual(invasion.get_current_invasion("crossingV2"), "none")

    def test_get_invasion_state_lists_known_zones(self):
        with (
            mock.patch("world.invasion._get_invasion_script", return_value=self.script),
            mock.patch("world.invasion._iter_zone_payloads", return_value=self.zone_payloads),
        ):
            invasion.set_current_invasion("crossingV2", "siege")
            state = invasion.get_invasion_state()
        self.assertEqual(state["zones"][0]["zone_id"], "crossingV2")
        self.assertEqual(state["counts"]["none"], 1)
        self.assertEqual(state["counts"]["siege"], 1)


class InvasionCacheTests(unittest.TestCase):
    def setUp(self):
        self.script = _StubScript()

    def test_cache_populated_after_first_read(self):
        self.script.attributes.add(invasion._state_key("zone_a"), "goblin_raid")
        invasion._ensure_state_cache_loaded(self.script)
        self.assertEqual(self.script._invasion_state_cache["zone_a"], "goblin_raid")

    def test_cache_survives_subsequent_reads(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            invasion.set_current_invasion("zone_a", "goblin_raid")
            self.assertEqual(len(self.script._invasion_state_cache), 1)
            for _ in range(10):
                invasion.get_current_invasion("zone_a")
            self.assertEqual(len(self.script._invasion_state_cache), 1)

    def test_cache_invalidated_on_at_start(self):
        script = _StubScript()
        invasion._reset_state_cache(script)
        script._invasion_state_cache["zone_a"] = "siege"
        script._invasion_meta_cache["zone_a"] = {"source": "test"}
        script._invasion_state_cache_loaded = True
        with mock.patch("world.invasion.invalidate_zone_caches"):
            invasion.InvasionScript.at_start(script)
        self.assertEqual(script._invasion_state_cache, {})
        self.assertEqual(script._invasion_meta_cache, {})
        self.assertFalse(script._invasion_state_cache_loaded)

    def test_writes_persist_to_db_attributes(self):
        with mock.patch("world.invasion._get_invasion_script", return_value=self.script):
            invasion.set_current_invasion("zone_a", "siege")
        self.assertEqual(self.script.attributes.get(invasion._state_key("zone_a")), "siege")
        self.assertEqual(self.script.attributes.get(invasion._meta_key("zone_a"))["source"], "admin")


class InvasionPerformanceTests(unittest.TestCase):
    def setUp(self):
        invasion.invalidate_zone_caches()

    def test_zone_payload_cache_reuses_loaded_yaml_until_invalidated(self):
        fake_path = SimpleNamespace(name="crossingV2.yaml", stem="crossingV2")
        payload = {"zone_id": "crossingV2", "name": "The Crossing"}
        fake_zone_dir = SimpleNamespace(glob=mock.Mock(return_value=[fake_path]))

        with (
            mock.patch("world.invasion._ZONE_DIR", fake_zone_dir),
            mock.patch("world.invasion._load_yaml", return_value=payload) as mock_load_yaml,
        ):
            first = invasion._iter_zone_payloads()
            second = invasion._iter_zone_payloads()
            invasion.invalidate_zone_caches("crossingV2")
            third = invasion._iter_zone_payloads()

        self.assertEqual(first[0]["zone_id"], "crossingV2")
        self.assertEqual(second[0]["zone_id"], "crossingV2")
        self.assertEqual(third[0]["zone_id"], "crossingV2")
        self.assertEqual(mock_load_yaml.call_count, 2)

    def test_get_invasion_state_under_threshold(self):
        import time

        script = _StubScript()
        payloads = [
            {"zone_id": f"zone_{index}", "name": f"Zone {index}"}
            for index in range(50)
        ]
        with (
            mock.patch("world.invasion._get_invasion_script", return_value=script),
            mock.patch("world.invasion._iter_zone_payloads", return_value=payloads),
        ):
            invasion.set_current_invasion("zone_1", "siege")
            invasion.get_invasion_state()
            start = time.monotonic()
            invasion.get_invasion_state()
            elapsed = time.monotonic() - start

        self.assertLess(
            elapsed,
            1.0,
            f"get_invasion_state() took {elapsed:.3f}s, expected < 1.0s",
        )