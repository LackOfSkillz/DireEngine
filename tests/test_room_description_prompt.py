import unittest

from world.builder.prompting.room_description_prompt import assemble_room_description_prompt, load_room_description_system_prompt


CONTEXT_LICENSE_CLAUSE = (
    "You may use zone context to inform tone, voice, and atmospheric vocabulary, but you may not invent "
    "specific physical objects, materials, weather, or sensory details based on zone context alone."
)


class RoomDescriptionPromptTests(unittest.TestCase):
    def test_prompt_omits_zone_context_section_when_generation_context_is_empty(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "market_square",
                "name": "Market Square",
                "exits": {
                    "north": {"target": "guildhall"},
                },
            },
            {
                "zone_id": "harbor_ward",
                "name": "Harbor Ward",
                "generation_context": None,
            },
        )

        self.assertNotIn("=== ZONE CONTEXT ===", prompt.prompt)
        self.assertNotIn("=== VOICE ===", prompt.prompt)
        self.assertIn("Zone: Harbor Ward", prompt.prompt)
        self.assertFalse(prompt.trimmed)

    def test_prompt_includes_fully_populated_zone_context_in_model_prompt(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "market_square",
                "name": "Market Square",
                "environment": "city",
                "short_desc": "A crowded market square",
                "desc": "Old draft text",
                "details": {"stalls": "Merchant stalls", "fountain": "A stone fountain"},
                "exits": {
                    "north": {"target": "guildhall"},
                    "east": {"target": "docks"},
                },
            },
            {
                "zone_id": "harbor_ward",
                "name": "Harbor Ward",
                "generation_context": {
                    "setting_type": "city",
                    "era_feel": "late-medieval",
                    "culture": ["multicultural"],
                    "mood": ["bustling", "tense"],
                    "climate": "coastal",
                    "voice": "Plainspoken and salt-worn.",
                    "banned_phrases": ["the air is thick"],
                },
            },
        )

        self.assertIn("Room name: Market Square", prompt.user_prompt)
        self.assertIn("Zone: Harbor Ward", prompt.user_prompt)
        self.assertIn("Setting type: city", prompt.user_prompt)
        self.assertIn("Mood cues: Bustling, Tense", prompt.user_prompt)
        self.assertIn("- north: guildhall", prompt.user_prompt)
        self.assertIn("- fountain", prompt.user_prompt)
        self.assertIn("Avoid these phrases: the air is thick", prompt.user_prompt)
        self.assertIn(load_room_description_system_prompt(), prompt.prompt)
        self.assertIn("=== ZONE CONTEXT ===", prompt.prompt)
        self.assertIn("You are in Harbor Ward.", prompt.prompt)
        self.assertIn("Setting type: city.", prompt.prompt)
        self.assertIn("Era feel: late-medieval.", prompt.prompt)
        self.assertIn("Cultural style: Multicultural.", prompt.prompt)
        self.assertIn("Mood: Bustling, Tense.", prompt.prompt)
        self.assertIn("Climate: coastal.", prompt.prompt)
        self.assertIn("=== VOICE ===", prompt.prompt)
        self.assertIn("Plainspoken and salt-worn.", prompt.prompt)
        self.assertIn(CONTEXT_LICENSE_CLAUSE, prompt.prompt)
        self.assertFalse(prompt.trimmed)

    def test_prompt_includes_only_populated_partial_zone_context_fields(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "quay_turn",
                "exits": {
                    "south": {"target": "docks"},
                    "west": {"target": "market_square"},
                },
            },
            {
                "zone_id": "harbor_ward",
                "name": "Harbor Ward",
                "generation_context": {
                    "mood": ["bustling"],
                    "voice": "Gritty, pragmatic.",
                },
            },
        )

        self.assertIn("=== ZONE CONTEXT ===", prompt.prompt)
        self.assertIn("You are in Harbor Ward.", prompt.prompt)
        self.assertIn("Mood: Bustling.", prompt.prompt)
        self.assertNotIn("Setting type:", prompt.prompt)
        self.assertNotIn("Era feel:", prompt.prompt)
        self.assertNotIn("Climate:", prompt.prompt)
        self.assertIn("=== VOICE ===", prompt.prompt)
        self.assertIn("Gritty, pragmatic.", prompt.prompt)

    def test_prompt_includes_room_tags_in_this_room_section(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "river_bridge",
                "name": "River Bridge",
                "tags": {
                    "structure": "bridge",
                    "specific_function": "tavern",
                    "named_feature": "well",
                    "condition": "crumbling",
                    "custom": ["river crossing", "stone span"],
                },
                "exits": {
                    "east": {"target": "market_square"},
                    "west": {"target": "gate_road"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "crossingV2",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertIn("=== THIS ROOM ===", prompt.prompt)
        self.assertIn("Structure: Bridge.", prompt.prompt)
        self.assertIn("Function: Tavern.", prompt.prompt)
        self.assertIn("Feature: Well.", prompt.prompt)
        self.assertIn("Condition: Crumbling.", prompt.prompt)
        self.assertIn("Custom: river crossing, stone span.", prompt.prompt)
        self.assertIn("This space takes the form of a bridge.", prompt.prompt)
        self.assertIn("This space serves as a tavern.", prompt.prompt)
        self.assertIn("A public well stands here.", prompt.prompt)
        self.assertIn("The stonework is crumbling, clearly long past its prime.", prompt.prompt)
        self.assertIn("Also: river crossing, stone span.", prompt.prompt)

    def test_prompt_trims_excess_context_when_budget_is_small(self):
        room = {
            "id": "overstuffed_room",
            "name": "Overstuffed Room",
            "environment": "city",
            "details": {f"detail_{index}": "x" for index in range(20)},
            "exits": {f"dir_{index}": {"target": f"room_{index}"} for index in range(20)},
        }
        zone = {
            "zone_id": "dense_quarter",
            "name": "Dense Quarter",
            "generation_context": {
                "setting_type": "city",
                "mood": ["tense"],
            },
        }

        prompt = assemble_room_description_prompt(room, zone, max_prompt_chars=550)

        self.assertTrue(prompt.trimmed)
        self.assertLessEqual(len(prompt.prompt), 550)
        self.assertIn("Room name: Overstuffed Room", prompt.user_prompt)
        self.assertNotIn("- dir_19: room_19", prompt.user_prompt)


if __name__ == "__main__":
    unittest.main()