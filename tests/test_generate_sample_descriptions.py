from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.generate_sample_descriptions import (
    SampleDescription,
    build_llm_client,
    collect_repeated_phrases,
    default_export_path,
    format_export,
    format_stdout_sample,
    generate_samples,
    iter_sample_targets,
    prepare_zone_yaml_for_generation,
    resolve_zone_id,
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

    def test_default_export_path_uses_expected_filename(self):
        path = default_export_path()

        self.assertEqual(path.parent.name, "exports")
        self.assertTrue(path.name.startswith("sample_descriptions_"))
        self.assertTrue(path.name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()