import unittest

from world.builder.schemas.generation_context_schema import load_zone_vocab, normalize_generation_context


class GenerationContextSchemaTests(unittest.TestCase):
    def test_load_zone_vocab_returns_expected_vocabularies(self):
        vocab = load_zone_vocab()

        self.assertIn("city", vocab["setting_types"])
        self.assertIn("medieval", vocab["eras"])
        self.assertIn("generic-fantasy", vocab["cultures"])
        self.assertIn("bustling", vocab["moods"])
        self.assertIn("temperate", vocab["climates"])

    def test_normalize_generation_context_returns_none_for_null_context(self):
        self.assertIsNone(normalize_generation_context(None))

    def test_normalize_generation_context_accepts_valid_payload(self):
        normalized = normalize_generation_context(
            {
                "setting_type": "city",
                "era_feel": "medieval",
                "culture": ["generic-fantasy", "multicultural", "generic-fantasy"],
                "mood": ["bustling", "tense"],
                "climate": "coastal",
                "voice": "Gritty and practical.",
                "banned_phrases": ["the air is thick", "the air is thick", "ancient stones"],
            }
        )

        self.assertEqual(
            normalized,
            {
                "setting_type": "city",
                "era_feel": "medieval",
                "culture": ["generic-fantasy", "multicultural"],
                "mood": ["bustling", "tense"],
                "climate": "coastal",
                "voice": "Gritty and practical.",
                "banned_phrases": ["the air is thick", "ancient stones"],
            },
        )

    def test_normalize_generation_context_rejects_unknown_vocab_values(self):
        with self.assertRaisesRegex(ValueError, "generation_context.setting_type must be one of"):
            normalize_generation_context({"setting_type": "space-station"})

        with self.assertRaisesRegex(ValueError, "generation_context.culture contains unsupported values"):
            normalize_generation_context({"culture": ["generic-fantasy", "voidborn"]})


if __name__ == "__main__":
    unittest.main()