from unittest import TestCase

from world.helpers.display_aggregation import aggregate_display_entries, format_stack_label, pluralize_label
from world.helpers.ordinals import parse_ordinal_value, split_ordinal_target
from world.helpers.target_resolver import format_item_matches, resolve_item_target, split_quantity_target


class OrdinalParsingTests(TestCase):
    def test_parses_numeric_ordinal(self):
        self.assertEqual(parse_ordinal_value("21st"), 21)

    def test_parses_english_ordinal_phrase(self):
        self.assertEqual(parse_ordinal_value("twenty first"), 21)
        self.assertEqual(parse_ordinal_value("one hundred third"), 103)

    def test_splits_numeric_positional_query(self):
        self.assertEqual(split_ordinal_target("2.leaf"), (2, "leaf"))

    def test_splits_english_ordinal_target(self):
        self.assertEqual(split_ordinal_target("third leaf"), (3, "leaf"))

    def test_preserves_plain_queries(self):
        self.assertEqual(split_ordinal_target("leaf"), (None, "leaf"))


class DisplayAggregationTests(TestCase):
    def test_pluralizes_irregular_leaf(self):
        self.assertEqual(pluralize_label("useful leaf", 2), "useful leaves")

    def test_formats_stack_label(self):
        self.assertEqual(format_stack_label("useful leaf", 4), "useful leaves (4)")

    def test_aggregates_matching_entries(self):
        aggregated = aggregate_display_entries(
            [
                {"label": "useful leaf", "aggregation_key": "leaf", "quantity": 3},
                {"label": "useful leaf", "aggregation_key": "leaf", "quantity": 2},
                {"label": "rough stick", "aggregation_key": "stick", "quantity": 1},
            ]
        )
        self.assertEqual(aggregated, ["useful leaves (5)", "rough stick"])

    def test_keeps_distinct_labels_separate(self):
        aggregated = aggregate_display_entries(
            [
                {"label": "useful leaf", "aggregation_key": "useful leaf", "quantity": 1},
                {"label": "rough leaf", "aggregation_key": "rough leaf", "quantity": 1},
            ]
        )
        self.assertEqual(aggregated, ["useful leaf", "rough leaf"])


class _DummyAliases:
    def __init__(self, values=None):
        self._values = list(values or [])

    def all(self):
        return list(self._values)


class _DummyItem:
    def __init__(self, key, arrived_at=0, aliases=None):
        self.key = key
        self.id = int(arrived_at or 0)
        self.db = type("DB", (), {"mt516_arrived_at": float(arrived_at)})()
        self.aliases = _DummyAliases(aliases)

    def get_display_name(self, looker=None, **kwargs):
        return self.key


class TargetResolverTests(TestCase):
    def test_prefers_newest_matching_item(self):
        older = _DummyItem("leaf", arrived_at=10)
        newer = _DummyItem("leaf", arrived_at=20)
        match, matches, base_query, index = resolve_item_target("leaf", [older, newer], default_first=True)
        self.assertIs(match, newer)
        self.assertEqual(matches, [newer, older])
        self.assertEqual(base_query, "leaf")
        self.assertIsNone(index)

    def test_supports_other_alias(self):
        older = _DummyItem("leaf", arrived_at=10)
        newer = _DummyItem("leaf", arrived_at=20)
        match, _matches, _base_query, index = resolve_item_target("other leaf", [older, newer], default_first=True)
        self.assertIs(match, older)
        self.assertEqual(index, 2)

    def test_formats_guidance_without_number_suffix(self):
        message = format_item_matches("leaf", [_DummyItem("leaf", 1), _DummyItem("leaf", 2)])
        self.assertIn("first leaf", message)
        self.assertIn("2.leaf", message)

    def test_splits_quantity_targets_without_touching_positional_form(self):
        self.assertEqual(split_quantity_target("5 leaves"), (5, "leaves"))
        self.assertEqual(split_quantity_target("2.leaf"), (None, "2.leaf"))