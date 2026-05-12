import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from world.builder.orchestration.zone_orchestrator import ZoneOrchestrator


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mt600a_fixture_zone.yaml"


class ZoneOrchestratorTests(unittest.TestCase):
    def _fake_generation_result(self, room_context, applicable_groups, applicable_states):
        room = dict(room_context.get("room") or {})
        generation_context = dict(room_context.get("generation_context") or {})
        geographic_context = dict(generation_context.get("geographic_context") or {})
        state_context = dict(generation_context.get("state_context") or {})
        street = next((entry.get("name") for entry in geographic_context.get("streets") or [] if entry.get("name")), None)
        district = next((entry.get("name") for entry in geographic_context.get("districts") or [] if entry.get("name")), None)
        tone = str(generation_context.get("emotional_tone") or "grounded").strip()
        state = str(state_context.get("state") or "").strip()
        location_bits = [bit for bit in [street, district] if bit]
        location_clause = f" on {' in '.join(location_bits)}" if location_bits else ""
        state_clause = f" During {state}, the scene shifts noticeably." if state else ""
        description = f"{room['name']} holds a {tone} air{location_clause}.{state_clause}".strip()
        return {
            "pass_1": description,
            "pass_2": f"$state(clear, {description})",
            "input_tokens": 120,
            "output_tokens": 60,
            "elapsed_ms": 25,
            "approximate_cost_usd": 0.00126,
        }

    def _patch_generator(self, side_effect):
        generator = Mock()
        generator.generate.side_effect = side_effect
        return patch.object(ZoneOrchestrator, "_create_room_description_generator", return_value=generator), generator

    def test_phase_1_reads_zone_type_outdoor_city(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()

        result = orchestrator.run_phase_1_zone_type_setup()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.changes["zone_type"], "outdoor_city")

    def test_phase_1_validates_invalid_zone_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "bad_zone.yaml"
            zone_path.write_text(
                """
schema_version: v1
zone_id: bad_zone
name: Bad Zone
zone_type: sky_castle
generation_context: {}
rooms: []
placements:
  npcs: []
  items: []
""".strip(),
                encoding="utf-8",
            )
            orchestrator = ZoneOrchestrator(zone_path)
            orchestrator.load_zone()

            with self.assertRaises(ValueError):
                orchestrator.run_phase_1_zone_type_setup()

    def test_phase_1_handles_missing_emotional_tone_with_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "warning_zone.yaml"
            payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
            del payload["generation_context"]["emotional_tone"]
            zone_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            orchestrator = ZoneOrchestrator(zone_path)
            orchestrator.load_zone()

            result = orchestrator.run_phase_1_zone_type_setup()

            self.assertIn("emotional_tone", " ".join(result.warnings))

    def test_phase_2_validates_existing_geographic_structure(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()
        orchestrator.run_phase_1_zone_type_setup()

        result = orchestrator.run_phase_2_geographic_structure()

        self.assertEqual(result.status, "success")
        self.assertIn("streets", result.changes["validated_collections"])

    def test_phase_2_warns_on_missing_geographic_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "missing_geo.yaml"
            payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
            del payload["geographic_structure"]
            zone_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            orchestrator = ZoneOrchestrator(zone_path)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()

            result = orchestrator.run_phase_2_geographic_structure()

            self.assertEqual(result.status, "success")
            self.assertTrue(result.warnings)

    def test_phase_2_fails_on_dangling_room_reference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "dangling_geo.yaml"
            zone_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8").replace("- market_square\n", "- missing_room\n", 1), encoding="utf-8")
            orchestrator = ZoneOrchestrator(zone_path)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()

            with self.assertRaises(ValueError):
                orchestrator.run_phase_2_geographic_structure()

    def test_dry_run_lists_empty_descriptions_as_phase_3_work(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()
        orchestrator.run_phase_1_zone_type_setup()
        orchestrator.run_phase_2_geographic_structure()

        plan = orchestrator.dry_run_plan()
        phase_3 = next(item for item in plan if item.phase_number == 3)

        self.assertEqual(phase_3.status, "would_run")
        self.assertIn("market_square", phase_3.rooms_affected)
        self.assertGreater(phase_3.estimated_input_tokens, 0)
        self.assertTrue(phase_3.details)

    def test_dry_run_lists_phase_4_state_targets(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()
        orchestrator.run_phase_1_zone_type_setup()
        orchestrator.run_phase_2_geographic_structure()

        plan = orchestrator.dry_run_plan()
        phase_4 = next(item for item in plan if item.phase_number == 4)

        self.assertEqual(phase_4.status, "would_run")
        self.assertGreater(phase_4.estimated_actions, 0)
        self.assertTrue(phase_4.details)

    def test_phase_4_respects_climate_weather_compatibility(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()
        orchestrator.run_phase_1_zone_type_setup()

        targets = orchestrator._phase_4_target_states(orchestrator.working_state["rooms"][1])

        weather_states = {target["state"] for target in targets if target["group"] == "weather"}
        self.assertIn("storm", weather_states)
        self.assertIn("heavy_rain", weather_states)
        self.assertNotIn("blizzard", weather_states)

    def test_phase_4_skips_non_meaningful_states(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()
        orchestrator.run_phase_1_zone_type_setup()

        targets = orchestrator._phase_4_target_states(orchestrator.working_state["rooms"][1])

        states = {target["state"] for target in targets}
        self.assertNotIn("clear", states)
        self.assertNotIn("afternoon", states)

    def test_phase_4_skips_rooms_with_no_applicable_state_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "quiet_zone.yaml"
            payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
            room = payload["rooms"][0]
            room["environment"] = "unknown"
            room["tags"]["structure"] = None
            zone_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            orchestrator = ZoneOrchestrator(zone_path)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()

            targets = orchestrator._phase_4_target_states(orchestrator.working_state["rooms"][0])

        self.assertTrue(targets)

    def test_phase_4_uses_canonical_stateful_descs_shape(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        working_state = orchestrator.load_zone()
        room = next(item for item in working_state["rooms"] if item["id"] == "market_square")
        self.assertIsInstance(room.get("stateful_descs"), dict)

    def test_phase_3_generates_descriptions_for_empty_rooms(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()

            result = orchestrator.run_phase_3_room_descriptions()

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.rooms_succeeded), 3)
        self.assertFalse(result.rooms_failed)
        self.assertTrue(result.checkpoint_path)
        self.assertEqual(generator.generate.call_count, 3)

    def test_phase_4_generates_stateful_variants_for_applicable_states(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            working_state = orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            generator.generate.reset_mock()

            result = orchestrator.run_phase_4_stateful_descriptions()

        self.assertEqual(result.status, "success")
        self.assertGreater(len(result.states_succeeded), 0)
        room = next(item for item in working_state["rooms"] if item["id"] == "market_square")
        self.assertIn("weather_storm", room["stateful_descs"])
        self.assertIn("time_night", room["stateful_descs"])
        self.assertEqual(generator.generate.call_count, result.changes["variants_generated"])

    def test_phase_4_includes_state_context_in_prompt(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            generator.generate.reset_mock()

            orchestrator.run_phase_4_stateful_descriptions()

        first_call_args = generator.generate.call_args_list[0][0]
        room_context = first_call_args[0]
        generation_context = room_context["generation_context"]
        self.assertIn("state_context", generation_context)
        self.assertIn("group", generation_context["state_context"])
        self.assertIn("state", generation_context["state_context"])

    def test_phase_4_handles_per_state_failure_gracefully(self):
        failing_state_key = None

        def side_effect(room_context, applicable_groups, applicable_states):
            nonlocal failing_state_key
            state_key = room_context["generation_context"]["state_context"]["state_key"]
            if state_key == failing_state_key:
                raise RuntimeError("state timeout")
            return self._fake_generation_result(room_context, applicable_groups, applicable_states)

        patcher, _generator = self._patch_generator(side_effect)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            failing_state_key = orchestrator._phase_4_target_states(orchestrator.working_state["rooms"][0])[0]["state_key"]
            _generator.generate.reset_mock()

            result = orchestrator.run_phase_4_stateful_descriptions()

        self.assertEqual(result.status, "partial-success")
        self.assertTrue(any(item["state_key"] == failing_state_key for item in result.rooms_failed))

    def test_phase_4_persists_to_stateful_descs_field(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            working_state = orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            _generator.generate.reset_mock()
            orchestrator.run_phase_4_stateful_descriptions()

        room = next(item for item in working_state["rooms"] if item["id"] == "smith_lane")
        self.assertTrue(room["stateful_descs"])

    def test_phase_4_does_not_overwrite_existing_stateful_descs(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            working_state = orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            generator.generate.reset_mock()
            room = next(item for item in working_state["rooms"] if item["id"] == "market_square")
            room["stateful_descs"]["weather_storm"] = "Existing storm variant"

            orchestrator.run_phase_4_stateful_descriptions()

        self.assertEqual(room["stateful_descs"]["weather_storm"], "Existing storm variant")
        self.assertTrue(generator.generate.call_count > 0)

    def test_phase_4_writes_checkpoint(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with tempfile.TemporaryDirectory() as temp_dir:
            with patcher:
                orchestrator = ZoneOrchestrator(FIXTURE_PATH, checkpoint_dir=Path(temp_dir))
                orchestrator.load_zone()
                orchestrator.run_phase_1_zone_type_setup()
                orchestrator.run_phase_2_geographic_structure()
                orchestrator.run_phase_3_room_descriptions()
                _generator.generate.reset_mock()

                result = orchestrator.run_phase_4_stateful_descriptions()
                self.assertTrue(Path(result.checkpoint_path).exists())

    def test_phase_4_does_not_invoke_other_phase_generators(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            orchestrator.run_phase_3_room_descriptions()
            generator.generate.reset_mock()

            result = orchestrator.run_phase_4_stateful_descriptions()

        self.assertEqual(generator.generate.call_count, result.changes["variants_generated"])

    def test_phase_3_skips_rooms_with_existing_descriptions(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with tempfile.TemporaryDirectory() as temp_dir:
            zone_path = Path(temp_dir) / "described_zone.yaml"
            payload = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
            for room in payload["rooms"]:
                room["desc"] = room.get("desc") or f"Existing description for {room['name']}"
            zone_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
            with patcher:
                orchestrator = ZoneOrchestrator(zone_path)
                orchestrator.load_zone()
                orchestrator.run_phase_1_zone_type_setup()
                orchestrator.run_phase_2_geographic_structure()

                result = orchestrator.run_phase_3_room_descriptions()

        self.assertEqual(result.status, "success")
        self.assertEqual(result.changes["rooms_targeted"], 0)
        self.assertEqual(generator.generate.call_count, 0)

    def test_phase_3_includes_geographic_context_in_prompt(self):
        patcher, generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()

            orchestrator.run_phase_3_room_descriptions()

        first_call_args = generator.generate.call_args_list[0][0]
        room_context = first_call_args[0]
        generation_context = room_context["generation_context"]
        self.assertEqual(generation_context["emotional_tone"], "bustling and hopeful")
        self.assertEqual(generation_context["cultural_signature"], "human frontier port town")
        self.assertIn("streets", generation_context["geographic_context"])
        self.assertNotIn("neighbor_descriptions", generation_context)

    def test_phase_3_handles_per_room_failure_gracefully(self):
        def side_effect(room_context, applicable_groups, applicable_states):
            room_id = room_context["room"]["id"]
            if room_id == "market_square":
                raise RuntimeError("timeout")
            return self._fake_generation_result(room_context, applicable_groups, applicable_states)

        patcher, _generator = self._patch_generator(side_effect)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()

            result = orchestrator.run_phase_3_room_descriptions()

        self.assertEqual(result.status, "partial-success")
        self.assertEqual(len(result.rooms_failed), 1)
        self.assertEqual(result.rooms_failed[0]["room_id"], "market_square")
        self.assertIn("timeout", result.rooms_failed[0]["reason"])

    def test_phase_3_handles_total_failure(self):
        patcher, _generator = self._patch_generator(RuntimeError("api unavailable"))
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()

            result = orchestrator.run_phase_3_room_descriptions()

        self.assertEqual(result.status, "failure")
        self.assertEqual(len(result.rooms_failed), 3)

    def test_phase_3_persists_descriptions_to_working_state(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            working_state = orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()

            orchestrator.run_phase_3_room_descriptions()

        generated_rooms = [room for room in working_state["rooms"] if room["id"] in {"market_square", "smith_lane", "harbor_road"}]
        self.assertTrue(all(str(room.get("desc") or "").strip() for room in generated_rooms))

    def test_phase_3_does_not_modify_existing_descriptions(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with patcher:
            orchestrator = ZoneOrchestrator(FIXTURE_PATH)
            working_state = orchestrator.load_zone()
            orchestrator.run_phase_1_zone_type_setup()
            orchestrator.run_phase_2_geographic_structure()
            original_desc = next(room for room in working_state["rooms"] if room["id"] == "market_gate")["desc"]

            orchestrator.run_phase_3_room_descriptions()

        self.assertEqual(next(room for room in working_state["rooms"] if room["id"] == "market_gate")["desc"], original_desc)

    def test_score_wiring_reads_baseline(self):
        orchestrator = ZoneOrchestrator(FIXTURE_PATH)
        orchestrator.load_zone()

        score = orchestrator.get_baseline_score()

        self.assertEqual(score.label, "baseline")
        self.assertGreaterEqual(score.room_count, 1)

    def test_checkpoint_writes_after_phase_1_phase_2_and_phase_3(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with tempfile.TemporaryDirectory() as temp_dir:
            with patcher:
                orchestrator = ZoneOrchestrator(FIXTURE_PATH, checkpoint_dir=Path(temp_dir))
                result = orchestrator.run_all_implemented_phases()

            self.assertEqual(len(result.checkpoints), 4)
            for checkpoint in result.checkpoints:
                self.assertTrue(Path(checkpoint).exists())

    def test_orchestrator_runs_phase_1_2_and_3_on_fixture_zone(self):
        patcher, _generator = self._patch_generator(self._fake_generation_result)
        with tempfile.TemporaryDirectory() as temp_dir:
            with patcher:
                orchestrator = ZoneOrchestrator(FIXTURE_PATH, checkpoint_dir=Path(temp_dir))

                result = orchestrator.run_all_implemented_phases()

            self.assertEqual(result.zone_id, "mt600a_fixture")
            self.assertEqual(result.zone_type, "outdoor_city")
            self.assertEqual(result.phase_results[0].status, "success")
            self.assertEqual(result.phase_results[1].status, "success")
            self.assertEqual(result.phase_results[2].status, "success")
            self.assertEqual(result.phase_results[3].status, "success")
            self.assertIn("after_phase_3", [score.label for score in result.scores])
            self.assertIn("after_phase_4", [score.label for score in result.scores])
            self.assertTrue(result.plan)


if __name__ == "__main__":
    unittest.main()