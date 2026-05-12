import unittest

from engine.bundles.stat_registry import (
    FALLBACK_STAT_DEFINITIONS,
    StatRegistry,
    get_default_stat_values,
    is_known_stat,
    populate_stat_registry_fallback,
    populate_stat_registry_from_canon,
)


class DummyConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self

    def execute(self, _sql):
        return None

    def fetchall(self):
        return list(self.rows)


class StatRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = StatRegistry("stat_registry")

    def test_populates_from_canon(self):
        rows = [
            {
                "id": 21,
                "name": "Strength",
                "abbreviation": "STR",
                "gsl_dispatch_id": 1,
                "description": "Strength desc",
                "source_entity_id": 1,
                "confidence": 0.95,
            },
            {
                "id": 22,
                "name": "Reflex",
                "abbreviation": "REF",
                "gsl_dispatch_id": 2,
                "description": "Reflex desc",
                "source_entity_id": 2,
                "confidence": 0.95,
            },
        ]
        source = populate_stat_registry_from_canon(registry=self.registry, connection_factory=lambda: DummyConnection(rows), log=None)
        self.assertEqual(source, "canon")
        self.assertEqual(self.registry.list_keys(), ["reflex", "strength"])
        self.assertEqual(self.registry.require("strength")["abbreviation"], "STR")

    def test_falls_back_when_canon_unreachable(self):
        def failing_connection():
            raise RuntimeError("db unavailable")

        source = populate_stat_registry_from_canon(registry=self.registry, connection_factory=failing_connection, log=None)
        self.assertEqual(source, "fallback")
        self.assertEqual(set(self.registry.list_keys()), set(FALLBACK_STAT_DEFINITIONS.keys()))

    def test_default_stat_values_follow_registry(self):
        populate_stat_registry_fallback(registry=self.registry)
        defaults = get_default_stat_values(registry=self.registry)
        self.assertEqual(defaults["strength"], 10)
        self.assertIn("aura", defaults)

    def test_known_stat_checks_registry(self):
        populate_stat_registry_fallback(registry=self.registry)
        self.assertTrue(is_known_stat("strength", registry=self.registry))
        self.assertFalse(is_known_stat("magic_resistance", registry=self.registry))


if __name__ == "__main__":
    unittest.main()