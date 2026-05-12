import unittest

from world.builder.schemas.geographic_structure_schema import (
    empty_geographic_structure,
    validate_geographic_structure,
    validate_zone_type,
)
from world.builder.schemas.generation_context_schema import normalize_generation_context


class ZoneOrchestrationSchemaTests(unittest.TestCase):
    def test_generation_context_preserves_mt600_fields(self):
        normalized = normalize_generation_context(
            {
                "setting_type": "city",
                "era_feel": "medieval",
                "climate": "temperate",
                "culture": ["generic-fantasy"],
                "mood": ["bustling"],
                "voice": "grounded",
                "emotional_tone": "bustling and hopeful",
                "cultural_signature": "human frontier town",
            }
        )

        self.assertEqual(normalized["emotional_tone"], "bustling and hopeful")
        self.assertEqual(normalized["cultural_signature"], "human frontier town")

    def test_validate_zone_type_accepts_locked_values(self):
        self.assertEqual(validate_zone_type("outdoor_city"), "outdoor_city")
        self.assertEqual(validate_zone_type("interior_small"), "interior_small")

    def test_validate_zone_type_rejects_invalid_value(self):
        with self.assertRaises(ValueError):
            validate_zone_type("sky_castle")

    def test_outdoor_geography_validates_room_references(self):
        normalized = validate_geographic_structure(
            "outdoor_city",
            {
                "streets": [{"name": "Main Street", "rooms": ["room_1", "room_2"]}],
                "districts": [{"name": "Market District", "rooms": ["room_1"]}],
                "intersections": [{"name": "Market Square", "rooms": ["room_2"]}],
                "landmarks": [{"name": "Bell Tower", "visible_from_rooms": ["room_1"]}],
                "gates": [{"name": "North Gate", "room": "room_2"}],
                "doorway_rooms": [{"name": "Inn Door", "parent_room": "room_1", "rooms": ["room_1"]}],
            },
            ["room_1", "room_2"],
        )

        self.assertEqual(normalized["streets"][0]["rooms"], ["room_1", "room_2"])

    def test_dangling_room_reference_fails_validation(self):
        with self.assertRaises(ValueError):
            validate_geographic_structure(
                "wilderness",
                {"trails": [{"name": "Kings Road", "rooms": ["room_404"]}]},
                ["room_1", "room_2"],
            )

    def test_small_interior_minimal_geography_validates(self):
        normalized = validate_geographic_structure(
            "interior_small",
            {"exits_to_parent": [{"parent_zone": "crossing", "parent_room": "room_1", "child_room": "room_1", "rooms": ["room_1"]}]},
            ["room_1"],
        )

        self.assertEqual(normalized["exits_to_parent"][0]["rooms"], ["room_1"])

    def test_empty_geographic_structure_matches_zone_type(self):
        normalized = empty_geographic_structure("interior_medium")

        self.assertIn("halls", normalized)
        self.assertIn("wings", normalized)


if __name__ == "__main__":
    unittest.main()