import unittest

from world.builder.schemas.room_tag_schema import load_atmosphere_vocab, load_room_vocab, normalize_room_tags


class RoomTagSchemaTests(unittest.TestCase):
    def test_load_room_vocab_returns_expected_vocabularies(self):
        vocab = load_room_vocab()

        self.assertIn("street", vocab["structure"])
        self.assertIn("tavern", vocab["specific_function"])
        self.assertIn("fountain", vocab["named_feature"])
        self.assertIn("crumbling", vocab["condition"])

    def test_load_atmosphere_vocab_returns_expected_vocabularies(self):
        vocab = load_atmosphere_vocab()

        self.assertIn("stone-walls", vocab["materials"])
        self.assertIn("working-class", vocab["social_character"])
        self.assertIn("market-nearby", vocab["surroundings"])
        self.assertIn("cooking-smell", vocab["sensory"])
        self.assertIn("lived-in", vocab["upkeep"])

    def test_normalize_room_tags_returns_empty_tags_for_null_payload(self):
        self.assertEqual(
            normalize_room_tags(None),
            {
                "structure": None,
                "specific_function": None,
                "named_feature": None,
                "condition": None,
                "custom": [],
                "atmosphere": {
                    "materials": [],
                    "social_character": [],
                    "surroundings": [],
                    "sensory": [],
                    "upkeep": None,
                },
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
                "atmosphere": {
                    "materials": ["stone-walls", "stone-walls", "cobbled-floor"],
                    "social_character": ["commercial", "mixed-class"],
                    "surroundings": ["shops-nearby", "market-nearby"],
                    "sensory": ["sounds-of-commerce", "dust-smell"],
                    "upkeep": "well-maintained",
                },
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
                "atmosphere": {
                    "materials": ["stone-walls", "cobbled-floor"],
                    "social_character": ["commercial", "mixed-class"],
                    "surroundings": ["shops-nearby", "market-nearby"],
                    "sensory": ["sounds-of-commerce", "dust-smell"],
                    "upkeep": "well-maintained",
                },
            },
        )

    def test_normalize_room_tags_accepts_empty_atmosphere_mapping(self):
        normalized = normalize_room_tags({"structure": "street", "atmosphere": {}})

        self.assertEqual(
            normalized["atmosphere"],
            {
                "materials": [],
                "social_character": [],
                "surroundings": [],
                "sensory": [],
                "upkeep": None,
            },
        )

    def test_normalize_room_tags_accepts_missing_atmosphere_for_legacy_rooms(self):
        normalized = normalize_room_tags({"structure": "street", "custom": ["old"]})

        self.assertEqual(
            normalized,
            {
                "structure": "street",
                "specific_function": None,
                "named_feature": None,
                "condition": None,
                "custom": ["old"],
                "atmosphere": {
                    "materials": [],
                    "social_character": [],
                    "surroundings": [],
                    "sensory": [],
                    "upkeep": None,
                },
            },
        )

    def test_normalize_room_tags_rejects_unknown_vocab_values(self):
        with self.assertRaisesRegex(ValueError, "room_tags.structure must be one of"):
            normalize_room_tags({"structure": "tunnel"})

        with self.assertRaisesRegex(ValueError, "room_tags.condition must be one of"):
            normalize_room_tags({"condition": "flooded"})

        with self.assertRaisesRegex(ValueError, "room_tags.atmosphere.materials must be one of"):
            normalize_room_tags({"atmosphere": {"materials": ["iron-walls"]}})

        with self.assertRaisesRegex(ValueError, "room_tags.atmosphere.upkeep must be one of"):
            normalize_room_tags({"atmosphere": {"upkeep": "restored"}})


if __name__ == "__main__":
    unittest.main()