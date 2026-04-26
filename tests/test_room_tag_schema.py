import unittest

from world.builder.schemas.room_tag_schema import load_room_vocab, normalize_room_tags


class RoomTagSchemaTests(unittest.TestCase):
    def test_load_room_vocab_returns_expected_vocabularies(self):
        vocab = load_room_vocab()

        self.assertIn("street", vocab["structure"])
        self.assertIn("tavern", vocab["specific_function"])
        self.assertIn("fountain", vocab["named_feature"])
        self.assertIn("crumbling", vocab["condition"])

    def test_normalize_room_tags_returns_empty_tags_for_null_payload(self):
        self.assertEqual(
            normalize_room_tags(None),
            {
                "structure": None,
                "specific_function": None,
                "named_feature": None,
                "condition": None,
                "custom": [],
            },
        )

    def test_normalize_room_tags_accepts_valid_payload(self):
        normalized = normalize_room_tags(
            {
                "structure": "street",
                "specific_function": "shop",
                "named_feature": "fountain",
                "condition": "worn",
                "custom": ["awning", "merchant quarter", "awning"],
            }
        )

        self.assertEqual(
            normalized,
            {
                "structure": "street",
                "specific_function": "shop",
                "named_feature": "fountain",
                "condition": "worn",
                "custom": ["awning", "merchant quarter"],
            },
        )

    def test_normalize_room_tags_rejects_unknown_vocab_values(self):
        with self.assertRaisesRegex(ValueError, "room_tags.structure must be one of"):
            normalize_room_tags({"structure": "tunnel"})

        with self.assertRaisesRegex(ValueError, "room_tags.condition must be one of"):
            normalize_room_tags({"condition": "flooded"})


if __name__ == "__main__":
    unittest.main()