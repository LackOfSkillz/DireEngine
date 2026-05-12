import unittest

from engine.bundles.builtin_skills import FALLBACK_SKILLS, normalize_skill_registry_key, populate_skill_registry_fallback, populate_skill_registry_from_canon
from engine.bundles.skill_registry import SkillRegistry


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


class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry("skill_registry")

    def test_populates_from_canon(self):
        rows = [
            {
                "id": 31,
                "gsl_id": 44,
                "name": "Primary Magic",
                "skillset": "magic",
                "description": None,
                "source_entity_id": None,
                "confidence": 0.9,
            },
            {
                "id": 38,
                "gsl_id": 59,
                "name": "Perception",
                "skillset": None,
                "description": None,
                "source_entity_id": None,
                "confidence": 0.9,
            },
        ]
        source = populate_skill_registry_from_canon(registry=self.registry, connection_factory=lambda: DummyConnection(rows), log=None)
        self.assertEqual(source, "canon")
        self.assertEqual(self.registry.list_keys(), ["perception", "primary_magic"])
        self.assertEqual(self.registry.require("primary_magic")["group"], "magic")
        self.assertEqual(self.registry.require("perception")["pulse_group"], 120)

    def test_falls_back_when_canon_unreachable(self):
        def failing_connection():
            raise RuntimeError("db unavailable")

        source = populate_skill_registry_from_canon(registry=self.registry, connection_factory=failing_connection, log=None)
        self.assertEqual(source, "fallback")
        self.assertEqual(set(self.registry.list_keys()), set(FALLBACK_SKILLS.keys()))

    def test_fallback_registers_expected_subset(self):
        source = populate_skill_registry_fallback(registry=self.registry, log=None)
        self.assertEqual(source, "fallback")
        self.assertEqual(self.registry.require("targeted_magic")["group"], "magic")
        self.assertEqual(self.registry.require("scholarship")["pulse_group"], 180)

    def test_normalize_skill_registry_key(self):
        self.assertEqual(normalize_skill_registry_key("Primary Magic"), "primary_magic")


if __name__ == "__main__":
    unittest.main()