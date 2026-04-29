import unittest

from world.builder.prompting.room_description_prompt import (
    assemble_room_description_prompt,
    determine_applicable_state_groups,
    determine_applicable_states,
    load_room_description_system_prompt,
)


CONTEXT_LICENSE_CLAUSE = (
    "When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support."
)
CRAFT_BLOCK_LINE = "Write each description with these craft principles:"
EXAMPLE_BLOCK_LINE = "Examples of the craft level expected:"
REINFORCEMENT_CLAUSE = "Stay within the licensed truth set: structural tags, exit data, zone context, and atmospheric tags when present."
STYLE_CONTRACT_START = "Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences."
STYLE_CONTRACT_END = "If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only."
STATEFUL_BLOCK_LINE = "STATEFUL FRAGMENTS"
class RoomDescriptionPromptTests(unittest.TestCase):
    def _assert_not_form_shaped(self, prompt_text: str) -> None:
        for forbidden in (
            "=== ZONE CONTEXT ===",
            "=== VOICE ===",
            "=== THIS ROOM ===",
            "=== ATMOSPHERE ===",
            "=== REQUIRED ROOM FACTS ===",
            "=== ALLOWED BUT NOT REQUIRED DETAILS ===",
            "=== SOFT ROOM CONTEXT ===",
            "=== SOFT AREA CONTEXT ===",
            "=== SOFT ZONE CONTEXT ===",
            "=== FORBIDDEN FEATURES ===",
            "=== ALLOWED EXITS ===",
            "=== INTERACTIVE OBJECTS ===",
            "Room Data:",
            "Atmospheric Tags:",
            "Description:",
            "Structure:",
            "Materials:",
            "Tags:",
        ):
            self.assertNotIn(forbidden, prompt_text)

    def _style_contract_block(self, prompt_text: str) -> str:
        start_index = prompt_text.index(STYLE_CONTRACT_START)
        end_index = prompt_text.index(STYLE_CONTRACT_END) + len(STYLE_CONTRACT_END)
        block = prompt_text[start_index:end_index]
        return block.replace("–", "-").replace("—", "-")

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

        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("It is in Harbor Ward.", prompt.prompt)
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
        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("The room is named Market Square.", prompt.prompt)
        self.assertIn("It is in Harbor Ward.", prompt.prompt)
        self.assertIn("The broader environment is city.", prompt.prompt)
        self.assertIn("The era feel is late-medieval.", prompt.prompt)
        self.assertIn("Cultural cues include Multicultural.", prompt.prompt)
        self.assertIn("Mood cues include Bustling and Tense.", prompt.prompt)
        self.assertIn("The climate is coastal.", prompt.prompt)
        self.assertIn("Voice guidance is Plainspoken and salt-worn.", prompt.prompt)
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

        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("It is in Harbor Ward.", prompt.prompt)
        self.assertIn("Mood cues include Bustling.", prompt.prompt)
        self.assertNotIn("The broader environment is", prompt.prompt)
        self.assertNotIn("The era feel is", prompt.prompt)
        self.assertNotIn("The climate is", prompt.prompt)
        self.assertIn("Voice guidance is Gritty, pragmatic.", prompt.prompt)

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

        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("This space takes the form of a bridge.", prompt.prompt)
        self.assertIn("This space serves as a tavern.", prompt.prompt)
        self.assertIn("A public well stands here.", prompt.prompt)
        self.assertIn("The stonework is crumbling, clearly long past its prime.", prompt.prompt)
        self.assertIn("Additional custom cues include river crossing and stone span.", prompt.prompt)

    def test_prompt_includes_atmosphere_section_when_present(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "river_bridge",
                "name": "River Bridge",
                "tags": {
                    "structure": "bridge",
                    "specific_function": None,
                    "named_feature": "signpost",
                    "condition": "worn",
                    "custom": [],
                    "atmosphere": {
                        "materials": ["stone-walls", "cobbled-floor"],
                        "social_character": ["commercial", "mixed-class"],
                        "surroundings": ["shops-nearby", "market-nearby"],
                        "sensory": ["sounds-of-commerce", "dust-smell"],
                        "upkeep": "well-maintained",
                    },
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

        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("Allowed materials include stone walls and cobbled floor.", prompt.prompt)
        self.assertIn("Allowed social character cues include commercial and mixed class.", prompt.prompt)
        self.assertIn("Allowed surrounding cues include shops nearby and market nearby.", prompt.prompt)
        self.assertIn("Allowed sensory cues include sounds of commerce and dust smell.", prompt.prompt)
        self.assertIn("Allowed upkeep cues include well maintained.", prompt.prompt)

    def test_prompt_includes_tightened_atmosphere_gate_clause(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "market_square",
                "name": "Market Square",
                "tags": {
                    "structure": "intersection",
                    "specific_function": None,
                    "named_feature": "signpost",
                    "condition": "worn",
                    "custom": [],
                    "atmosphere": {
                        "materials": ["cobbled-floor"],
                        "social_character": ["commercial"],
                        "surroundings": ["market-nearby"],
                        "sensory": ["sounds-of-commerce"],
                        "upkeep": "well-maintained",
                    },
                },
                "exits": {
                    "north": {"target": "north_lane"},
                    "south": {"target": "south_lane"},
                    "west": {"target": "west_lane"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "crossingV2",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertIn(CONTEXT_LICENSE_CLAUSE, prompt.prompt)
        self.assertIn("Atmospheric tags do NOT authorize structural or architectural changes.", prompt.prompt)
        self.assertIn("Banned nouns from the constraint block remain forbidden regardless of atmospheric context.", prompt.prompt)
        self.assertIn(CRAFT_BLOCK_LINE, prompt.prompt)
        self.assertIn("- Engage at least two senses.", prompt.prompt)
        self.assertIn("- Never use \"you\" or address the reader.", prompt.prompt)
        self.assertIn("- Do not list or describe exits in prose.", prompt.prompt)
        self.assertIn(EXAMPLE_BLOCK_LINE, prompt.prompt)
        self.assertIn("URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior", prompt.prompt)
        self.assertIn("WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage", prompt.prompt)
        self.assertIn(REINFORCEMENT_CLAUSE, prompt.prompt)
        self.assertIn("Do not include exits in prose.", prompt.prompt)
        self.assertIn("Apply the craft principles consistently.", prompt.prompt)

    def test_prompt_includes_production_style_contract_in_focused_style_block(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "market_square",
                "name": "Market Square",
                "exits": {
                    "north": {"target": "north_lane"},
                    "south": {"target": "south_lane"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {"setting_type": "city"},
            },
        )

        style_block = self._style_contract_block(prompt.prompt)

        self.assertIn("Write 3-5 plain, concrete sentences.", style_block)
        self.assertIn("Target 45-90 words.", style_block)
        self.assertIn("Use only grounded facts.", style_block)
        self.assertIn("Too short looks unfinished.", style_block)
        self.assertIn("Too long will not be read.", style_block)
        self.assertIn(
            "If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.",
            style_block,
        )
        self.assertIn("Return only the final room description paragraph.", style_block)
        self.assertIn("Your entire response must be one plain paragraph of room description prose.", style_block)
        self.assertIn("Start immediately with the first sentence of the room description.", style_block)
        self.assertIn("The first character must be a normal sentence character, not #, *, -, [, {, or a label.", style_block)
        self.assertIn("Do not include headings, labels, markdown, bullets, field names, analysis, notes, or blank lines.", style_block)
        self.assertIn("Do not write sections.", style_block)
        self.assertIn("Do not echo or transform the input fields.", style_block)
        self.assertIn("Do not mention the prompt, allowed facts, metadata, tags, YAML, or generation rules.", style_block)
        self.assertIn(
            "Do not invent props, light sources, furniture, ceiling details, wall materials, weather, smells, sounds, or atmosphere unless they are present in the allowed facts.",
            style_block,
        )
        self.assertIn("If you cannot produce a compliant paragraph, produce the best grounded 3-5 sentence paragraph anyway.", style_block)
        self.assertIn(
            "If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only.",
            style_block,
        )
        self.assertIn("Do not echo field names, form labels, or section titles from the input packet.", style_block)
        self.assertIn("Do not transform the input into a completed template or metadata block.", style_block)

        for expected in (
            "3",
            "5",
            "45",
            "90",
            "plain",
            "concrete",
            "grounded facts",
            "Too short",
            "Too long",
            "facts are sparse",
            "room shape",
            "exits",
            "surfaces",
            "boundaries",
            "inventing props",
            "Return only the final room description paragraph",
            "entire response",
            "one plain paragraph",
            "Start immediately",
            "first character",
            "normal sentence character",
            "not #, *, -, [, {, or a label",
            "headings",
            "labels",
            "markdown",
            "bullets",
            "blank lines",
            "Do not write sections",
            "Do not echo or transform the input fields",
            "metadata",
            "tags",
            "YAML",
            "generation rules",
            "props",
            "light sources",
            "furniture",
            "ceiling details",
            "wall materials",
            "weather",
            "smells",
            "sounds",
            "atmosphere unless they are present in the allowed facts",
            "If you cannot produce a compliant paragraph",
            "echo field names",
            "form labels",
            "section titles",
            "completed template",
            "metadata block",
        ):
            self.assertIn(expected, style_block)

    def test_prompt_omits_atmosphere_section_when_atmosphere_is_empty(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "quiet_lane",
                "tags": {
                    "structure": "street",
                    "specific_function": None,
                    "named_feature": None,
                    "condition": None,
                    "custom": [],
                    "atmosphere": {},
                },
                "exits": {
                    "south": {"target": "market_square"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "crossingV2",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertNotIn("Allowed materials include", prompt.prompt)

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

    def test_prompt_includes_typed_generation_sections_with_hard_soft_and_forbidden_separation(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "hedge_walk",
                "name": "Hedge-Lined Walk",
                "generation_input": {
                    "required_room_facts": ["cobblestone path", "trimmed shrubs"],
                    "allowed_but_not_required": ["sage incense"],
                    "soft_room_context": ["ordered calm"],
                    "forbidden_features": ["door", "stairs"],
                    "allowed_exits": [
                        {"direction": "north", "description": "cobblestone path"},
                        {"direction": "east", "description": "arched walkway"},
                    ],
                    "interactive_objects": ["bronze plaque"],
                },
                "exits": {
                    "north": {"target": "quad_north"},
                    "east": {"target": "lecture_hall"},
                },
            },
            {
                "zone_id": "crossingv2",
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
                },
                "area": {
                    "name": "Scholar's District",
                    "generation_input": {
                        "soft_area_context": ["academic quiet", "ink and vellum"],
                    },
                },
            },
        )

        self._assert_not_form_shaped(prompt.prompt)
        self.assertIn("Required room facts include cobblestone path and trimmed shrubs.", prompt.prompt)
        self.assertIn("Allowed but optional details include sage incense.", prompt.prompt)
        self.assertIn("Soft room context includes ordered calm.", prompt.prompt)
        self.assertIn("The area is Scholar's District.", prompt.prompt)
        self.assertIn("Area context includes academic quiet and ink and vellum.", prompt.prompt)
        self.assertIn("Zone context includes trade wealth.", prompt.prompt)
        self.assertIn("Forbidden features include door and stairs.", prompt.prompt)
        self.assertIn("If exits are mentioned, only north via cobblestone path and east via arched walkway may appear.", prompt.prompt)
        self.assertIn("Only these objects may receive look text: bronze plaque.", prompt.prompt)

    def test_prompt_required_facts_remain_the_only_hard_facts_when_inherited_context_exists(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "hedge_walk",
                "generation_input": {
                    "required_room_facts": ["cobblestone path", "trimmed shrubs"],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {
                    "setting_type": "city",
                    "era_feel": "medieval",
                    "culture": ["generic-fantasy"],
                    "mood": ["bustling"],
                    "climate": "temperate",
                    "voice": "Plainspoken and practical.",
                },
                "generation_input": {"soft_zone_context": ["trade wealth"]},
                "area": {
                    "name": "Scholar's District",
                    "generation_input": {"soft_area_context": ["academic quiet"]},
                },
            },
        )

        self.assertIn("Required room facts include cobblestone path and trimmed shrubs.", prompt.prompt)
        self.assertIn("The area is Scholar's District.", prompt.prompt)
        self.assertIn("Area context includes academic quiet.", prompt.prompt)
        self.assertIn("Zone context includes trade wealth.", prompt.prompt)
        self.assertNotIn("Required room facts include cobblestone path and trimmed shrubs, Scholar's District", prompt.prompt)
        self.assertNotIn("Required room facts include cobblestone path and trimmed shrubs, trade wealth", prompt.prompt)

    def test_prompt_forbidden_features_remain_isolated_from_required_and_soft_sections(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "archive_entry",
                "generation_input": {
                    "required_room_facts": ["stone threshold"],
                    "soft_room_context": ["ordered quiet"],
                    "forbidden_features": ["door", "stairs"],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("Required room facts include stone threshold.", prompt.prompt)
        self.assertIn("Soft room context includes ordered quiet.", prompt.prompt)
        self.assertIn("Forbidden features include door and stairs.", prompt.prompt)

    def test_prompt_no_flattening_regression_checks_section_boundaries(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "hedge_walk",
                "generation_input": {
                    "required_room_facts": ["cobblestone path"],
                    "soft_room_context": ["ordered calm"],
                    "forbidden_features": ["door"],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("Required room facts include cobblestone path.", prompt.prompt)
        self.assertIn("Soft room context includes ordered calm.", prompt.prompt)
        self.assertIn("Forbidden features include door.", prompt.prompt)

    def test_prompt_renders_zero_allowed_exits_cleanly(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "sealed_cellar",
                "name": "Sealed Cellar",
                "generation_input": {
                    "required_room_facts": ["sealed stone chamber"],
                    "allowed_exits": [],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("No exits may be mentioned in the description.", prompt.prompt)

    def test_prompt_renders_single_allowed_exit_without_label(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "north_walk",
                "generation_input": {
                    "allowed_exits": [{"direction": "north"}],
                },
                "exits": {"north": {"target": "north_square"}},
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("If exits are mentioned, only north may appear.", prompt.prompt)

    def test_prompt_renders_multiple_allowed_exits_with_labels_when_supplied(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "hedge_walk",
                "generation_input": {
                    "allowed_exits": [
                        {"direction": "north", "description": "cobblestone path"},
                        {"direction": "east", "description": "arched walkway"},
                        {"direction": "south", "target": "scholar_gate"},
                    ],
                },
                "exits": {
                    "north": {"target": "quad_north"},
                    "east": {"target": "lecture_hall"},
                    "south": {"target": "scholar_gate"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn(
            "If exits are mentioned, only north via cobblestone path, east via arched walkway, and south via scholar_gate may appear.",
            prompt.prompt,
        )

    def test_prompt_hard_prohibits_object_look_targets_when_interactive_objects_are_empty(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "quiet_lane",
                "generation_input": {
                    "required_room_facts": ["quiet lane"],
                    "interactive_objects": [],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("No object look targets may be generated.", prompt.prompt)

    def test_prompt_renders_only_listed_interactive_objects_under_interactive_objects_section(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "archive_entry",
                "generation_input": {
                    "interactive_objects": ["heavy timber door", "narrow stairway"],
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": None,
            },
        )

        self.assertIn("Only these objects may receive look text: heavy timber door and narrow stairway.", prompt.prompt)

    def test_prompt_includes_stateful_fragment_guidance(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "market_square",
                "name": "Market Square",
                "exits": {
                    "north": {"target": "north_lane"},
                    "south": {"target": "south_lane"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertIn(STATEFUL_BLOCK_LINE, prompt.prompt)
        self.assertIn("Only use states from this room's applicable_states list", prompt.prompt)
        self.assertIn("$state(name, content)", prompt.prompt)
        self.assertIn("Only use these state names when writing stateful fragments:", prompt.prompt)
        self.assertIn("include at least one $state fragment for each listed group", prompt.prompt)
        self.assertIn("Complete example (urban street, applicable state groups: season, time, weather):", prompt.prompt)
        self.assertIn("Do not write meta-commentary about state variability", prompt.prompt)

    def test_state_mapping_uses_urban_city_fallback_for_untyped_exterior_room(self):
        groups = determine_applicable_state_groups(
            {
                "id": "crossingV2_192_132",
                "exits": {"west": {"target": "crossingV2_178_132"}},
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertEqual(groups, ["season", "time", "weather", "invasion"])
        self.assertEqual(
            determine_applicable_states(
                {
                    "id": "crossingV2_192_132",
                    "exits": {"west": {"target": "crossingV2_178_132"}},
                },
                {
                    "zone_id": "crossingv2",
                    "name": "The Crossing",
                    "generation_context": {"setting_type": "city"},
                },
            ),
            ["spring", "summer", "autumn", "winter", "morning", "midday", "evening", "night", "rain", "snow", "fog", "invasion"],
        )

    def test_state_mapping_uses_room_tags_for_interior_room(self):
        groups = determine_applicable_state_groups(
            {
                "id": "crossingV2_178_132",
                "tags": {
                    "structure": "hallway",
                    "specific_function": "tavern",
                    "named_feature": "hearth",
                    "condition": "worn",
                    "custom": [],
                    "atmosphere": {},
                },
                "exits": {
                    "east": {"target": "crossingV2_192_132"},
                    "south": {"target": "crossingV2_178_154"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertEqual(groups, ["season", "time", "invasion"])

    def test_state_mapping_uses_legacy_underground_fallback_for_cro_rooms(self):
        groups = determine_applicable_state_groups(
            {
                "id": "CRO_500_100",
                "exits": {
                    "west": {"target": "CRO_450_100"},
                    "down": {"target": "CRO_500_150"},
                },
            },
            {"zone_id": "demo1", "name": "demo1", "generation_context": None},
        )

        self.assertEqual(groups, ["season"])

    def test_prompt_includes_applicable_states_list_for_room(self):
        prompt = assemble_room_description_prompt(
            {
                "id": "crossingV2_178_132",
                "tags": {
                    "structure": "hallway",
                    "specific_function": "tavern",
                    "named_feature": "hearth",
                    "condition": "worn",
                    "custom": [],
                    "atmosphere": {},
                },
                "exits": {
                    "east": {"target": "crossingV2_192_132"},
                    "south": {"target": "crossingV2_178_154"},
                },
            },
            {
                "zone_id": "crossingv2",
                "name": "The Crossing",
                "generation_context": {"setting_type": "city"},
            },
        )

        self.assertIn("Applicable state groups for this room are season, time, and invasion.", prompt.prompt)
        self.assertIn(
            "The applicable_states list for this room is spring, summer, autumn, winter, morning, midday, evening, night, and invasion.",
            prompt.prompt,
        )


if __name__ == "__main__":
    unittest.main()