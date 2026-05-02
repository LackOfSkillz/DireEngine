import unittest

from world.helpers.ordinals import parse_ordinal_value, split_ordinal_target


class OrdinalParsingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()