import unittest

from world.builder.schemas.typed_generation_input_schema import (
    empty_typed_generation_input,
    normalize_typed_generation_input,
    resolve_typed_generation_input,
)


class TypedGenerationInputSchemaTests(unittest.TestCase):
    def test_empty_typed_generation_input_returns_expected_defaults(self):
        self.assertEqual(
            empty_typed_generation_input(),
            {
                "required_room_facts": [],
                "allowed_but_not_required": [],
                "soft_zone_context": [],
                "soft_area_context": [],
                "soft_room_context": [],
                "forbidden_features": [],
                "allowed_exits": [],
                "interactive_objects": [],
            },
        )

    def test_normalize_typed_generation_input_accepts_all_new_fields(self):
        normalized = normalize_typed_generation_input(
            {
                "required_room_facts": ["cobblestone path", "cobblestone path", "trimmed shrubs"],
                "allowed_but_not_required": ["sage incense"],
                "soft_zone_context": ["The Crossing", "dense maritime republic"],
                "soft_area_context": ["Scholar's District"],
                "soft_room_context": ["ordered calm"],
                "forbidden_features": ["door", "rain"],
                "allowed_exits": [
                    {"direction": "north", "target": "quad_north"},
                    "south",
                ],
                "interactive_objects": ["heavy timber door"],
            }
        )

        self.assertEqual(
            normalized,
            {
                "required_room_facts": ["cobblestone path", "trimmed shrubs"],
                "allowed_but_not_required": ["sage incense"],
                "soft_zone_context": ["The Crossing", "dense maritime republic"],
                "soft_area_context": ["Scholar's District"],
                "soft_room_context": ["ordered calm"],
                "forbidden_features": ["door", "rain"],
                "allowed_exits": [
                    {"direction": "north", "target": "quad_north", "type": "", "description": ""},
                    {"direction": "south", "target": "", "type": "", "description": ""},
                ],
                "interactive_objects": ["heavy timber door"],
            },
        )

    def test_normalize_typed_generation_input_rejects_invalid_allowed_exits(self):
        with self.assertRaisesRegex(ValueError, "generation_input.allowed_exits\[0\] must include a direction"):
            normalize_typed_generation_input({"allowed_exits": [{}]})

    def test_resolve_typed_generation_input_adapts_legacy_room_tags(self):
        resolved = resolve_typed_generation_input(
            {
                "name": "Hedge-Lined Walk",
                "tags": {
                    "structure": "street",
                    "named_feature": "fountain",
                    "condition": "worn",
                    "custom": ["trimmed shrubs"],
                    "atmosphere": {
                        "materials": ["cobbled-floor"],
                        "sensory": ["dust-smell"],
                        "upkeep": "well-maintained",
                    },
                },
                "exits": {
                    "north": {"target": "north_room"},
                    "south": {"target": "south_room"},
                },
            }
        )

        self.assertEqual(resolved["required_room_facts"], ["street", "fountain"])
        self.assertEqual(resolved["allowed_but_not_required"], ["worn", "cobbled floor", "dust smell", "well maintained"])
        self.assertEqual(resolved["soft_room_context"], ["trimmed shrubs"])
        self.assertEqual(
            resolved["allowed_exits"],
            [
                {"direction": "north", "target": "north_room", "type": "", "description": ""},
                {"direction": "south", "target": "south_room", "type": "", "description": ""},
            ],
        )

    def test_resolve_typed_generation_input_merges_zone_area_and_room_priorities(self):
        resolved = resolve_typed_generation_input(
            {
                "name": "Hedge-Lined Walk",
                "generation_input": {
                    "required_room_facts": ["cobblestone path", "low hedges"],
                    "forbidden_features": ["door", "stairs"],
                    "interactive_objects": ["bronze plaque"],
                },
                "tags": {"structure": "street"},
                "exits": {"north": {"target": "quad_north"}},
            },
            {
                "name": "The Crossing",
                "generation_context": {
                    "setting_type": "city",
                    "era_feel": "medieval",
                    "culture": ["generic-fantasy"],
                    "mood": ["bustling"],
                    "climate": "temperate",
                    "voice": "Plainspoken and practical.",
                },
                "generation_input": {
                    "soft_zone_context": ["trade wealth"],
                    "forbidden_features": ["rain", "sunlight"],
                },
            },
            {
                "name": "Scholar's District",
                "generation_input": {
                    "soft_area_context": ["academic quiet", "sage incense"],
                    "forbidden_features": ["gate"],
                },
            },
        )

        self.assertEqual(resolved["required_room_facts"], ["street", "cobblestone path", "low hedges"])
        self.assertEqual(
            resolved["soft_zone_context"],
            ["The Crossing", "city", "medieval", "temperate", "plainspoken and practical.", "generic fantasy", "bustling", "trade wealth"],
        )
        self.assertEqual(resolved["soft_area_context"], ["Scholar's District", "academic quiet", "sage incense"])
        self.assertEqual(resolved["forbidden_features"], ["rain", "sunlight", "gate", "door", "stairs"])
        self.assertEqual(resolved["interactive_objects"], ["bronze plaque"])
        self.assertEqual(
            resolved["allowed_exits"],
            [{"direction": "north", "target": "quad_north", "type": "", "description": ""}],
        )


if __name__ == "__main__":
    unittest.main()