import unittest
from unittest.mock import patch

from server.systems.loot import loot_resolver


class StubRng:
    def __init__(self, random_values, randint_values):
        self._random_values = list(random_values)
        self._randint_values = list(randint_values)

    def random(self):
        return self._random_values.pop(0)

    def randint(self, _min_value, _max_value):
        return self._randint_values.pop(0)


class LootResolverTests(unittest.TestCase):
    def test_roll_loot_returns_weighted_entries(self):
        with patch.object(
            loot_resolver,
            "loot_registry",
            {
                "test_loot": {
                    "id": "test_loot",
                    "drops": [
                        {"item": "chain_greaves", "chance": 0.5, "min": 1, "max": 1},
                        {"item": "black_wool_shorts", "chance": 1.0, "min": 2, "max": 4},
                    ],
                }
            },
        ), patch("server.systems.loot.loot_resolver.ensure_loot_tables_loaded"):
            drops = loot_resolver.roll_loot("test_loot", rng=StubRng([0.4, 0.2], [1, 3]))

        self.assertEqual(drops, [{"item_id": "chain_greaves", "count": 1}, {"item_id": "black_wool_shorts", "count": 3}])

    def test_roll_loot_rejects_unknown_table(self):
        with patch.object(loot_resolver, "loot_registry", {}), patch("server.systems.loot.loot_resolver.ensure_loot_tables_loaded"):
            with self.assertRaisesRegex(ValueError, "Unknown loot table"):
                loot_resolver.roll_loot("missing")