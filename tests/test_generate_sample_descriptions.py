from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.generate_sample_descriptions import (
    SampleDescription,
    build_llm_client,
    build_evaluation_counts,
    classify_sentence_count_bucket,
    classify_word_count_bucket,
    collect_repeated_phrases,
    default_export_path,
    format_export,
    format_stdout_sample,
    generate_samples,
    iter_sample_targets,
    prepare_zone_yaml_for_generation,
    resolve_zone_id,
    sample_is_safe,
    sample_is_useful,
)


class GenerateSampleDescriptionsTests(unittest.IsolatedAsyncioTestCase):
    def test_iter_sample_targets_applies_global_limit(self):
        zones = [
            {"zone_id": "harbor", "rooms": [{"id": "dock_01"}, {"id": "dock_02"}]},
            {"zone_id": "temple", "rooms": [{"id": "sanctum_01"}]},
        ]

        targets = iter_sample_targets(zones, 2)

        self.assertEqual(
            [(zone["zone_id"], room["id"]) for zone, room in targets],
            [("harbor", "dock_01"), ("harbor", "dock_02")],
        )

    async def test_generate_samples_uses_existing_generation_service_contract(self):
        zone_map = {
            "harbor": {
                "zone_id": "harbor",
                "name": "Harbor District",
                "generation_context": {"mood": ["brisk"]},
                "rooms": [
                    {"id": "dock_12", "name": "Dock 12", "desc": "", "details": {}, "exits": {}},
                ],
            }
        }

        async def fake_generator(room, zone, *, client, llm_config, max_tokens):
            self.assertEqual(max_tokens, 180)
            self.assertEqual(room["id"], "dock_12")
            self.assertEqual(zone["generation_context"], {"mood": ["brisk"]})
            self.assertEqual(client, {"client": "ok"})
            self.assertEqual(llm_config.model_name, "fake-model")
            return SimpleNamespace(
                text="Salt wind slides along the pilings.",
                error=None,
                provenance={"source": "llm", "model": "fake-model"},
            )

        samples, zones = await generate_samples(
            ["harbor"],
            limit=1,
            max_tokens=180,
            zone_loader=lambda zone_id: zone_map[zone_id],
            config_loader=lambda: SimpleNamespace(model_name="fake-model"),
            client_factory=lambda config: {"client": "ok"},
            generator=fake_generator,
        )

        self.assertEqual(len(samples), 1)
        self.assertEqual(len(zones), 1)
        self.assertEqual(samples[0].zone_name, "Harbor District")
        self.assertEqual(samples[0].room_id, "dock_12")
        self.assertEqual(samples[0].text, "Salt wind slides along the pilings.")


class GenerateSampleDescriptionsFormattingTests(unittest.TestCase):
    def _sample(self, text: str) -> SampleDescription:
        return SampleDescription(
            zone_id="harbor",
            zone_name="Harbor District",
            room_id="dock_12",
            room_name="Dock 12",
            text=text,
            error=None,
            provenance={},
        )

    def test_prepare_zone_yaml_for_generation_defaults_missing_placements(self):
        normalized = prepare_zone_yaml_for_generation({"zone_id": "demo1", "name": "demo1", "rooms": []})

        self.assertEqual(normalized["placements"], {"npcs": [], "items": []})
        self.assertEqual(normalized["zone_id"], "demo1")

    def test_resolve_zone_id_prefers_yaml_zone_id(self):
        self.assertEqual(resolve_zone_id("crossingV2", {"zone_id": "crossingv2"}), "crossingv2")
        self.assertEqual(resolve_zone_id("demo1", {}), "demo1")

    def test_build_llm_client_maps_config_fields(self):
        config = SimpleNamespace(llm_base_url="http://llm.example", llm_model="builder-model")
        calls = []

        def fake_client_class(*, base_url, model):
            calls.append((base_url, model))
            return "client"

        client = build_llm_client(config, client_class=fake_client_class)

        self.assertEqual(client, "client")
        self.assertEqual(calls, [("http://llm.example", "builder-model")])

    def test_collect_repeated_phrases_reports_cross_output_ngrams(self):
        repeated = collect_repeated_phrases(
            [
                "The air is thick with salt and tar.",
                "The air is thick with incense and smoke.",
                "The air is thick with river fog.",
            ],
            min_words=3,
            max_words=5,
            min_count=2,
            limit=5,
        )

        self.assertIn(("the air is thick with", 3), repeated)
        self.assertIn(("the air is thick", 3), repeated)

    def test_formatters_match_review_friendly_output(self):
        samples = [
            SampleDescription(
                zone_id="harbor",
                zone_name="Harbor District",
                room_id="dock_12",
                room_name="Dock 12",
                text="The scent of brine hangs over the pilings.",
                error=None,
                provenance={"source": "llm"},
            ),
            SampleDescription(
                zone_id="harbor",
                zone_name="Harbor District",
                room_id="alley_03",
                room_name="Alley 03",
                text=None,
                error="Local LLM generation is unavailable.",
                provenance={"source": "disabled"},
            ),
        ]

        stdout_text = format_stdout_sample(samples[0])
        export_text = format_export(samples, [("the air is thick", 2)])

        self.assertIn("[Zone: Harbor District | Room: dock_12]", stdout_text)
        self.assertIn("=== Zone: Harbor District ===", export_text)
        self.assertIn("[Room: dock_12]", export_text)
        self.assertIn("[ERROR] Local LLM generation is unavailable.", export_text)
        self.assertIn('- "the air is thick" (2)', export_text)

    def test_build_evaluation_counts_reports_second_person_and_assumption_violations(self):
        samples = [
            SampleDescription(
                zone_id="harbor",
                zone_name="Harbor District",
                room_id="dock_12",
                room_name="Dock 12",
                text="You notice the salt stink first. As you walk, your boots scrape the planks.",
                error=None,
                provenance={},
            )
        ]

        counts = build_evaluation_counts(samples)

        self.assertEqual(counts["second_person_violations"], 3)
        self.assertEqual(counts["player_assumption_violations"], 2)

    def test_classify_word_count_bucket_reports_expected_ranges(self):
        self.assertEqual(classify_word_count_bucket("one two three"), "under_45_words")
        self.assertEqual(classify_word_count_bucket(" ".join(f"word{i}" for i in range(45))), "45_to_90_words")
        self.assertEqual(classify_word_count_bucket(" ".join(f"word{i}" for i in range(91))), "over_90_words")

    def test_classify_sentence_count_bucket_reports_expected_ranges(self):
        self.assertEqual(classify_sentence_count_bucket("One sentence."), "under_3_sentences")
        self.assertEqual(classify_sentence_count_bucket("One. Two. Three."), "3_to_5_sentences")
        self.assertEqual(classify_sentence_count_bucket("One. Two. Three. Four. Five. Six."), "over_5_sentences")

    def test_sample_is_safe_but_not_useful_when_under_target_length(self):
        text = (
            "Rough boards line the dock. Salt wind drifts between the posts. "
            "Dark water knocks softly below."
        )

        self.assertTrue(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_useful_when_safe_and_within_word_and_sentence_targets(self):
        text = (
            "Weathered planks stretch between thick pilings above the harbor water. "
            "Salt wind moves through the gaps, carrying tar, rope, and the dull slap of waves against wood. "
            "The dock stays narrow and practical, with rough rails, damp boards, and open water pressing close along its edge."
        )

        self.assertTrue(sample_is_safe(text))
        self.assertTrue(sample_is_useful(text))

    def test_sample_is_unsafe_due_to_poetic_filler(self):
        text = (
            "In the heart of the harbor, weathered planks stretch above black water. "
            "Salt wind moves through the gaps between the boards. "
            "The dock remains narrow and damp beneath a gray sky."
        )

        self.assertFalse(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_unsafe_due_to_fabrication_watchlist_hit(self):
        text = (
            "Weathered planks stretch between thick pilings above the harbor water. "
            "A lantern swings from a post beside the walkway. "
            "Salt wind and tar cling to the damp boards."
        )

        self.assertFalse(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_unsafe_due_to_wrapper_label(self):
        text = (
            "Room Description:\n\n"
            "Weathered planks stretch between thick pilings above the harbor water. "
            "Salt wind moves through the gaps, carrying tar and rope. "
            "The dock stays narrow and practical along the water's edge."
        )

        self.assertFalse(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_unsafe_due_to_markdown_heading_and_bullets(self):
        text = (
            "**Room Data:**\n"
            "- Structure: dock\n"
            "- Exits: north, east\n\n"
            "Weathered planks stretch between thick pilings above the harbor water. "
            "Salt wind moves through the gaps, carrying tar and rope. "
            "The dock stays narrow and practical along the water's edge."
        )

        self.assertFalse(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_unsafe_due_to_echoed_field_labels(self):
        text = (
            "**Description:**\n"
            "**Structure:** dock\n"
            "**Exits:** north, east\n"
            "**Materials:** weathered planks\n\n"
            "Weathered planks stretch between thick pilings above the harbor water. "
            "Salt wind moves through the gaps, carrying tar and rope. "
            "The dock stays narrow and practical along the water's edge."
        )

        self.assertFalse(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_sample_is_not_useful_due_to_stub_phrase(self):
        text = (
            "The corridor stays plain and unadorned through the ruin. "
            "A narrow passage leads forward with bare stone on either side. "
            "A narrow passage offers no detail beyond the close walls."
        )

        self.assertTrue(sample_is_safe(text))
        self.assertFalse(sample_is_useful(text))

    def test_build_evaluation_counts_reports_safe_and_useful_sample_buckets(self):
        useful_text = (
            "Weathered planks stretch between thick pilings above the harbor water. "
            "Salt wind moves through the gaps, carrying tar, rope, and the dull slap of waves against wood. "
            "The dock stays narrow and practical, with rough rails, damp boards, and open water pressing close along its edge."
        )
        safe_not_useful_text = (
            "Rough boards line the dock. Salt wind drifts between the posts. "
            "Dark water knocks softly below."
        )
        unsafe_text = (
            "In the heart of the harbor, weathered planks stretch above black water. "
            "Salt wind moves through the gaps between the boards. "
            "The dock remains narrow and damp beneath a gray sky."
        )
        stub_text = (
            "Stone walls press close around the route through the old ruin. "
            "A narrow passage runs ahead between damp surfaces and a low boundary wall. "
            "Cold air lingers here, and the floor stays rough beneath steady footsteps while old mortar flakes from the seams and gathers in the corners."
        )
        samples = [
            self._sample(useful_text),
            self._sample(safe_not_useful_text),
            self._sample(unsafe_text),
            self._sample(stub_text),
        ]

        counts = build_evaluation_counts(samples)

        self.assertEqual(counts["safe_samples"], 3)
        self.assertEqual(counts["useful_samples"], 1)
        self.assertEqual(counts["useful_acceptance_rate"], 25.0)
        self.assertEqual(counts["under_45_words"], 2)
        self.assertEqual(counts["45_to_90_words"], 2)
        self.assertEqual(counts["over_90_words"], 0)
        self.assertEqual(counts["under_3_sentences"], 0)
        self.assertEqual(counts["3_to_5_sentences"], 4)
        self.assertEqual(counts["over_5_sentences"], 0)
        self.assertEqual(counts["poetic_filler_counts"]["in the heart of"], 1)
        self.assertEqual(counts["stub_phrase_counts"]["a narrow passage"], 1)

    def test_format_export_includes_new_violation_counts(self):
        samples = [
            SampleDescription(
                zone_id="harbor",
                zone_name="Harbor District",
                room_id="dock_12",
                room_name="Dock 12",
                text="You feel the boards shift.",
                error=None,
                provenance={},
            )
        ]

        export_text = format_export(samples, [])

        self.assertIn("Second-person violations:", export_text)
        self.assertIn("Player-assumption violations:", export_text)

    def test_format_export_includes_safe_and_useful_summary_lines(self):
        samples = [
            self._sample(
                "Weathered planks stretch between thick pilings above the harbor water. "
                "Salt wind moves through the gaps, carrying tar, rope, and the dull slap of waves against wood. "
                "The dock stays narrow and practical, with rough rails, damp boards, and open water pressing close along its edge."
            ),
            self._sample("Rough boards line the dock. Salt wind drifts between the posts. Dark water knocks softly below."),
        ]

        export_text = format_export(samples, [])

        self.assertIn("Safe samples: 2/2", export_text)
        self.assertIn("Useful samples: 1/2", export_text)
        self.assertIn("Useful acceptance rate: 50.0%", export_text)
        self.assertIn("Under 45 words:", export_text)
        self.assertIn("45 to 90 words:", export_text)
        self.assertIn("Over 90 words:", export_text)
        self.assertIn("Under 3 sentences:", export_text)
        self.assertIn("3 to 5 sentences:", export_text)
        self.assertIn("Over 5 sentences:", export_text)
        self.assertIn("Poetic filler counts:", export_text)
        self.assertIn("Fabrication watchlist counts:", export_text)
        self.assertIn("Stub phrase counts:", export_text)

    def test_default_export_path_uses_expected_filename(self):
        path = default_export_path()

        self.assertEqual(path.parent.name, "exports")
        self.assertTrue(path.name.startswith("sample_descriptions_"))
        self.assertTrue(path.name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()