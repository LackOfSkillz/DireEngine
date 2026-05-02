import unittest

from world.helpers.display_aggregation import aggregate_display_entries, format_stack_label, pluralize_label


class DisplayAggregationTests(unittest.TestCase):
    def test_pluralizes_irregular_leaf(self):
        self.assertEqual(pluralize_label("useful leaf", 2), "useful leaves")

    def test_preserves_already_plural_berries_label(self):
        self.assertEqual(pluralize_label("useful berries", 2), "useful berries")

    def test_formats_stack_label(self):
        self.assertEqual(format_stack_label("useful leaf", 4), "useful leaves (4)")

    def test_formats_stack_label_for_existing_plural_berries(self):
        self.assertEqual(format_stack_label("useful berries", 2), "useful berries (2)")

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


if __name__ == "__main__":
    unittest.main()