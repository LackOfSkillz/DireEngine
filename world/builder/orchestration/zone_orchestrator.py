from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml
from world.builder.prompting.room_description_prompt import (
    build_room_description_user_message,
    determine_applicable_state_groups,
    determine_applicable_states,
)
from world.builder.scoring.zone_scorer import score_zone
from world.builder.schemas.geographic_structure_schema import (
    empty_geographic_structure,
    validate_geographic_structure,
    validate_zone_type,
)
from world.builder.schemas.generation_context_schema import normalize_generation_context


PHASE_3_CHECKPOINT_BATCH_SIZE = 10
ROOM_DESCRIPTION_INPUT_COST_PER_MILLION = 3.0
STATEFUL_VARIANT_ALLOWLIST = {
    "weather": {
        "storm": "heavy rain, wind, lightning, exposed surfaces, reduced visibility, and the strain of bad weather",
        "heavy_rain": "steady rain, runoff, soaked surfaces, dripping eaves, and muffled street noise",
    },
    "time": {
        "night": "low light, lamplight, hush, long shadows, and quieter movement after dark",
        "evening": "waning daylight, lamps being lit, lengthening shadows, and trade settling toward dusk",
    },
    "season": {
        "winter": "cold air, biting wind, frost, hardened ground, and winter wear on exposed materials",
    },
    "invasion": {
        "invasion": "visible threat, alarm, damage, urgency, and people reacting to an active incursion",
    },
}


FUTURE_PHASES = {
    3: "room descriptions",
    4: "stateful descriptions",
    5: "identity tags",
    6: "npc rosters",
    7: "item placements",
    8: "quest hook stubs",
    9: "doorway coordination",
    10: "score-driven repair",
}


@dataclass
class PhaseResult:
    phase_name: str
    status: str
    changes: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rooms_succeeded: list[str] = field(default_factory=list)
    rooms_failed: list[dict[str, str]] = field(default_factory=list)
    states_succeeded: list[dict[str, str]] = field(default_factory=list)
    duration_ms: int = 0
    checkpoint_path: str | None = None


@dataclass
class PhasePlan:
    phase_number: int
    phase_name: str
    status: str
    rooms_affected: list[str] = field(default_factory=list)
    surfaces_affected: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    details: list[dict[str, Any]] = field(default_factory=list)
    estimated_actions: int = 0
    estimated_input_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class ScoreSnapshot:
    label: str
    composite: int
    tier: str
    completeness: int
    depth: int
    engagement: int
    room_count: int
    rooms_needing_attention: list[dict[str, Any]] = field(default_factory=list)
    computed_at: str = ""


@dataclass
class OrchestrationResult:
    zone_id: str
    zone_type: str | None
    phase_results: list[PhaseResult] = field(default_factory=list)
    scores: list[ScoreSnapshot] = field(default_factory=list)
    plan: list[PhasePlan] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ZoneOrchestrator:
    def __init__(self, zone_path: Path, checkpoint_dir: Path | None = None):
        self.zone_path = Path(zone_path)
        repo_root = Path(__file__).resolve().parents[3]
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else repo_root / "artifacts" / "zone_orchestration_checkpoints"
        self.working_state: dict[str, Any] | None = None
        self.phase_results: list[PhaseResult] = []
        self.score_history: list[ScoreSnapshot] = []
        self.checkpoints: list[str] = []

    def load_zone(self) -> dict[str, Any]:
        with self.zone_path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            raise ValueError("Zone YAML must load to a mapping.")
        if not str(payload.get("zone_id") or "").strip():
            raise ValueError("Zone YAML must include zone_id.")
        if not isinstance(payload.get("rooms"), list):
            raise ValueError("Zone YAML must include rooms as a list.")
        if not isinstance(payload.get("placements") or {}, dict):
            raise ValueError("Zone YAML must include placements as a mapping.")

        working_state = dict(payload)
        working_state["schema_version"] = str(working_state.get("schema_version") or "v1")
        working_state["zone_id"] = str(working_state.get("zone_id") or "").strip()
        working_state["name"] = str(working_state.get("name") or working_state["zone_id"]).strip()
        working_state["zone_type"] = str(working_state.get("zone_type") or "").strip() or None
        working_state["generation_context"] = normalize_generation_context(working_state.get("generation_context")) or {}
        working_state["geographic_structure"] = dict(working_state.get("geographic_structure") or {})
        working_state["placements"] = {
            "npcs": list(dict(working_state.get("placements") or {}).get("npcs") or []),
            "items": list(dict(working_state.get("placements") or {}).get("items") or []),
        }
        self.working_state = working_state
        return working_state

    def run_phase_1_zone_type_setup(self) -> PhaseResult:
        state = self._require_working_state()
        started = perf_counter()
        warnings: list[str] = []
        generation_context = dict(state.get("generation_context") or {})
        zone_type = validate_zone_type(state.get("zone_type"))

        emotional_tone = str(generation_context.get("emotional_tone") or "").strip()
        cultural_signature = str(generation_context.get("cultural_signature") or "").strip()
        if not emotional_tone:
            warnings.append("generation_context.emotional_tone is recommended but missing.")
        if not cultural_signature:
            warnings.append("generation_context.cultural_signature is recommended but missing.")

        state["zone_type"] = zone_type
        state["generation_context"] = generation_context
        result = PhaseResult(
            phase_name="phase_1_zone_type_setup",
            status="success",
            changes={
                "zone_type": zone_type,
                "generation_context_fields": sorted(generation_context.keys()),
            },
            warnings=warnings,
            duration_ms=int((perf_counter() - started) * 1000),
        )
        self.phase_results.append(result)
        return result

    def run_phase_2_geographic_structure(self) -> PhaseResult:
        state = self._require_working_state()
        started = perf_counter()
        zone_type = validate_zone_type(state.get("zone_type"))
        room_ids = [str((room or {}).get("id") or "").strip() for room in list(state.get("rooms") or []) if str((room or {}).get("id") or "").strip()]
        payload = dict(state.get("geographic_structure") or {})
        if not payload:
            empty_payload = empty_geographic_structure(zone_type)
            state["geographic_structure"] = empty_payload
            result = PhaseResult(
                phase_name="phase_2_geographic_structure",
                status="success",
                changes={"geographic_structure": "initialized_empty"},
                warnings=[f"geographic_structure is missing for zone_type={zone_type}. Validation skipped with empty structure placeholder."],
                duration_ms=int((perf_counter() - started) * 1000),
            )
            self.phase_results.append(result)
            return result

        normalized = validate_geographic_structure(zone_type, payload, room_ids)
        state["geographic_structure"] = normalized
        result = PhaseResult(
            phase_name="phase_2_geographic_structure",
            status="success",
            changes={"validated_collections": sorted(normalized.keys())},
            duration_ms=int((perf_counter() - started) * 1000),
        )
        self.phase_results.append(result)
        return result

    def run_phase_3_room_descriptions(self) -> PhaseResult:
        state = self._require_working_state()
        started = perf_counter()
        rooms = [room for room in list(state.get("rooms") or []) if isinstance(room, dict)]
        target_rooms = [room for room in rooms if not str(room.get("desc") or "").strip()]
        warnings: list[str] = []
        successful_rooms: list[str] = []
        failed_rooms: list[dict[str, str]] = []
        prompt_contexts: list[dict[str, Any]] = []
        generated_outputs: list[dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_estimated_prompt_tokens = 0
        total_cost_usd = 0.0
        checkpoint_path: Path | None = None
        generator = self._create_room_description_generator()
        batch_count = 0

        for index, room in enumerate(target_rooms, start=1):
            room_id = self._room_id(room)
            generation_context = self._build_phase_3_generation_context(room)
            applicable_groups = determine_applicable_state_groups(room, state, generation_context)
            applicable_states = determine_applicable_states(applicable_groups)
            prompt_preview = build_room_description_user_message(room, generation_context)
            estimated_prompt_tokens = self._estimate_prompt_tokens(prompt_preview)
            total_estimated_prompt_tokens += estimated_prompt_tokens
            geographic_context = dict(generation_context.get("geographic_context") or {})
            prompt_contexts.append(
                {
                    "room_id": room_id,
                    "geographic_context": geographic_context,
                    "geographic_summary": self._summarize_geographic_context(geographic_context),
                    "estimated_prompt_tokens": estimated_prompt_tokens,
                }
            )

            try:
                result = generator.generate(
                    {
                        "room": room,
                        "zone": state,
                        "generation_context": generation_context,
                    },
                    applicable_groups,
                    applicable_states,
                )
                generated_description = str(result.get("pass_1") or "").strip()
                if not generated_description:
                    raise ValueError("Generator returned an empty pass_1 description.")
                room["desc"] = generated_description
                successful_rooms.append(room_id)
                input_tokens = int(result.get("input_tokens", 0) or 0)
                output_tokens = int(result.get("output_tokens", 0) or 0)
                elapsed_ms = int(result.get("elapsed_ms", 0) or 0)
                approximate_cost = float(result.get("approximate_cost_usd", 0.0) or 0.0)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                total_cost_usd += approximate_cost
                generated_outputs.append(
                    {
                        "room_id": room_id,
                        "description": generated_description,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "elapsed_ms": elapsed_ms,
                        "approximate_cost_usd": approximate_cost,
                    }
                )
            except Exception as error:
                reason = str(error).strip() or error.__class__.__name__
                failed_rooms.append({"room_id": room_id, "reason": reason})
                warnings.append(f"room {room_id} generation failed: {reason}")

            batch_count += 1
            if batch_count >= PHASE_3_CHECKPOINT_BATCH_SIZE:
                checkpoint_path = self.checkpoint(f"phase_3_room_descriptions_batch_{index}")
                batch_count = 0

        if target_rooms:
            checkpoint_path = self.checkpoint("phase_3_room_descriptions")
        else:
            checkpoint_path = self.checkpoint("phase_3_room_descriptions")

        if target_rooms and not successful_rooms:
            status = "failure"
        elif failed_rooms:
            status = "partial-success"
        else:
            status = "success"

        result = PhaseResult(
            phase_name="phase_3_room_descriptions",
            status=status,
            changes={
                "rooms_targeted": len(target_rooms),
                "rooms_generated": len(successful_rooms),
                "rooms_failed": len(failed_rooms),
                "estimated_prompt_tokens": total_estimated_prompt_tokens,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "approximate_cost_usd": round(total_cost_usd, 6),
                "checkpoint_batch_size": PHASE_3_CHECKPOINT_BATCH_SIZE,
                "prompt_contexts": prompt_contexts,
                "generated_outputs": generated_outputs,
            },
            warnings=warnings,
            notes=[
                "Descriptions are persisted from pass_1 plain prose to avoid injecting state markup before MT-600d.",
                "Prompt token estimate is derived from the canonical pass-1 user message length.",
            ],
            rooms_succeeded=successful_rooms,
            rooms_failed=failed_rooms,
            duration_ms=int((perf_counter() - started) * 1000),
            checkpoint_path=str(checkpoint_path) if checkpoint_path else None,
        )
        self.phase_results.append(result)
        return result

    def run_phase_4_stateful_descriptions(self) -> PhaseResult:
        state = self._require_working_state()
        started = perf_counter()
        rooms = [room for room in list(state.get("rooms") or []) if isinstance(room, dict)]
        warnings: list[str] = []
        successful_rooms: list[str] = []
        failed_states: list[dict[str, str]] = []
        successful_states: list[dict[str, str]] = []
        prompt_contexts: list[dict[str, Any]] = []
        generated_outputs: list[dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_estimated_prompt_tokens = 0
        total_cost_usd = 0.0
        variants_targeted = 0
        rooms_targeted = 0
        generator = self._create_room_description_generator()

        for room in rooms:
            room_id = self._room_id(room)
            if not str(room.get("desc") or "").strip():
                continue

            stateful_descs = dict(room.get("stateful_descs") or {})
            target_states = self._phase_4_target_states(room)
            if not target_states:
                continue
            rooms_targeted += 1
            room_successes = 0
            room_failures = 0

            for target in target_states:
                state_key = target["state_key"]
                if str(stateful_descs.get(state_key) or "").strip():
                    continue

                variants_targeted += 1
                generation_context = self._build_phase_4_generation_context(room, target)
                prompt_preview = build_room_description_user_message(room, generation_context)
                estimated_prompt_tokens = self._estimate_prompt_tokens(prompt_preview)
                total_estimated_prompt_tokens += estimated_prompt_tokens
                prompt_contexts.append(
                    {
                        "room_id": room_id,
                        "state_key": state_key,
                        "state_context": dict(generation_context.get("state_context") or {}),
                        "geographic_summary": self._summarize_geographic_context(dict(generation_context.get("geographic_context") or {})),
                        "estimated_prompt_tokens": estimated_prompt_tokens,
                    }
                )

                try:
                    result = generator.generate(
                        {
                            "room": room,
                            "zone": state,
                            "generation_context": generation_context,
                        },
                        target["applicable_groups"],
                        target["applicable_states"],
                    )
                    generated_description = str(result.get("pass_1") or "").strip()
                    if not generated_description:
                        raise ValueError("Generator returned an empty pass_1 description.")
                    stateful_descs[state_key] = generated_description
                    room["stateful_descs"] = stateful_descs
                    room_successes += 1
                    successful_states.append({"room_id": room_id, "state_key": state_key})

                    input_tokens = int(result.get("input_tokens", 0) or 0)
                    output_tokens = int(result.get("output_tokens", 0) or 0)
                    elapsed_ms = int(result.get("elapsed_ms", 0) or 0)
                    approximate_cost = float(result.get("approximate_cost_usd", 0.0) or 0.0)
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    total_cost_usd += approximate_cost
                    generated_outputs.append(
                        {
                            "room_id": room_id,
                            "state_key": state_key,
                            "description": generated_description,
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "elapsed_ms": elapsed_ms,
                            "approximate_cost_usd": approximate_cost,
                        }
                    )
                except Exception as error:
                    room_failures += 1
                    reason = str(error).strip() or error.__class__.__name__
                    failed_states.append({"room_id": room_id, "state_key": state_key, "reason": reason})
                    warnings.append(f"room {room_id} stateful generation failed for {state_key}: {reason}")

            if room_successes and room_id not in successful_rooms:
                successful_rooms.append(room_id)
            if room_failures and room_successes == 0:
                failed_states.append({"room_id": room_id, "state_key": "__room__", "reason": "all target states failed"})

        checkpoint_path = self.checkpoint("phase_4_stateful_descriptions")

        if variants_targeted and not successful_states:
            status = "failure"
        elif failed_states:
            status = "partial-success"
        else:
            status = "success"

        result = PhaseResult(
            phase_name="phase_4_stateful_descriptions",
            status=status,
            changes={
                "rooms_targeted": rooms_targeted,
                "variants_targeted": variants_targeted,
                "variants_generated": len(successful_states),
                "variants_failed": len([item for item in failed_states if item.get("state_key") != "__room__"]),
                "estimated_prompt_tokens": total_estimated_prompt_tokens,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "approximate_cost_usd": round(total_cost_usd, 6),
                "prompt_contexts": prompt_contexts,
                "generated_outputs": generated_outputs,
            },
            warnings=warnings,
            notes=[
                "Phase 4 generates per-state variants only; it does not generate combinatorial state products.",
                "Variants persist as stateful_descs[state_key] plain prose entries using the canonical builder schema.",
            ],
            rooms_succeeded=successful_rooms,
            rooms_failed=failed_states,
            states_succeeded=successful_states,
            duration_ms=int((perf_counter() - started) * 1000),
            checkpoint_path=str(checkpoint_path),
        )
        self.phase_results.append(result)
        return result

    def get_baseline_score(self, label: str = "baseline") -> ScoreSnapshot:
        state = self._require_working_state()
        payload = score_zone(state)
        snapshot = ScoreSnapshot(
            label=label,
            composite=int(payload.get("composite", 0) or 0),
            tier=str(payload.get("tier") or ""),
            completeness=int(dict(payload.get("completeness") or {}).get("score", 0) or 0),
            depth=int(dict(payload.get("depth") or {}).get("score", 0) or 0),
            engagement=int(dict(payload.get("engagement") or {}).get("score", 0) or 0),
            room_count=int(payload.get("room_count", 0) or 0),
            rooms_needing_attention=list(payload.get("rooms_needing_attention") or []),
            computed_at=str(payload.get("computed_at") or ""),
        )
        self.score_history.append(snapshot)
        return snapshot

    def dry_run_plan(self) -> list[PhasePlan]:
        state = self._require_working_state()
        rooms = [dict(room) for room in list(state.get("rooms") or []) if isinstance(room, dict)]
        score_snapshot = self.get_baseline_score(label="dry_run")

        empty_desc_rooms = [self._room_id(room) for room in rooms if not str(room.get("desc") or "").strip()]
        phase_3_details = []
        phase_3_estimated_input_tokens = 0
        phase_3_estimated_cost_usd = 0.0
        for room in rooms:
            if str(room.get("desc") or "").strip():
                continue
            room_generation_context = self._build_phase_3_generation_context(room)
            prompt_preview = build_room_description_user_message(room, room_generation_context)
            estimated_prompt_tokens = self._estimate_prompt_tokens(prompt_preview)
            phase_3_estimated_input_tokens += estimated_prompt_tokens
            phase_3_estimated_cost_usd += (estimated_prompt_tokens / 1_000_000) * ROOM_DESCRIPTION_INPUT_COST_PER_MILLION
            phase_3_details.append(
                {
                    "room_id": self._room_id(room),
                    "geographic_summary": self._summarize_geographic_context(dict(room_generation_context.get("geographic_context") or {})),
                    "estimated_prompt_tokens": estimated_prompt_tokens,
                }
            )
        phase_4_rooms = []
        phase_4_estimated_input_tokens = 0
        phase_4_estimated_cost_usd = 0.0
        phase_4_variant_count = 0
        for room in rooms:
            if not str(room.get("desc") or "").strip():
                continue
            room_state_targets = self._phase_4_target_states(room)
            room_stateful_descs = dict(room.get("stateful_descs") or {})
            pending_targets = [target for target in room_state_targets if not str(room_stateful_descs.get(target["state_key"]) or "").strip()]
            if not pending_targets:
                continue
            room_details = []
            for target in pending_targets:
                generation_context = self._build_phase_4_generation_context(room, target)
                prompt_preview = build_room_description_user_message(room, generation_context)
                estimated_prompt_tokens = self._estimate_prompt_tokens(prompt_preview)
                phase_4_estimated_input_tokens += estimated_prompt_tokens
                phase_4_estimated_cost_usd += (estimated_prompt_tokens / 1_000_000) * ROOM_DESCRIPTION_INPUT_COST_PER_MILLION
                phase_4_variant_count += 1
                room_details.append(
                    {
                        "state_key": target["state_key"],
                        "group": target["group"],
                        "state": target["state"],
                        "narrative_hint": target["narrative_hint"],
                        "estimated_prompt_tokens": estimated_prompt_tokens,
                    }
                )
            phase_4_rooms.append(
                {
                    "room_id": self._room_id(room),
                    "applicable_groups": sorted({target["group"] for target in pending_targets}),
                    "targets": room_details,
                }
            )
        missing_stateful_rooms = [
            self._room_id(room)
            for room in rooms
            if determine_applicable_state_groups(room, state, dict(state.get("generation_context") or {}))
            and not dict(room.get("stateful_descs") or {})
        ]
        missing_identity_tag_rooms = [
            self._room_id(room)
            for room in rooms
            if not self._has_identity_tags(room)
        ]
        npc_gap_rooms = [self._room_id(room) for room in rooms if self._room_npc_count(room) == 0]
        item_gap_rooms = [self._room_id(room) for room in rooms if self._room_item_count(room) == 0]
        quest_gap_rooms = [self._room_id(room) for room in rooms if not list(room.get("quest_hooks") or [])]
        doorway_rooms = self._doorway_room_ids()
        score_gap_rooms = [str(room.get("room_id") or "").strip() for room in score_snapshot.rooms_needing_attention if str(room.get("room_id") or "").strip()]

        plans = [
            PhasePlan(
                3,
                FUTURE_PHASES[3],
                "would_run" if empty_desc_rooms else "would_skip",
                empty_desc_rooms,
                ["descriptions"],
                [
                    f"{len(empty_desc_rooms)} rooms missing base descriptions.",
                    f"Estimated input prompt tokens: {phase_3_estimated_input_tokens}.",
                    f"Estimated input-only cost: ${round(phase_3_estimated_cost_usd, 6):.6f}.",
                ],
                phase_3_details,
                len(empty_desc_rooms),
                phase_3_estimated_input_tokens,
                round(phase_3_estimated_cost_usd, 6),
            ),
            PhasePlan(
                4,
                FUTURE_PHASES[4],
                "would_run" if phase_4_variant_count else "would_skip",
                [item["room_id"] for item in phase_4_rooms],
                ["stateful_descs"],
                [
                    f"{len(phase_4_rooms)} rooms have pending stateful variants.",
                    f"{phase_4_variant_count} meaningful state variants would generate.",
                    f"Estimated input prompt tokens: {phase_4_estimated_input_tokens}.",
                    f"Estimated input-only cost: ${round(phase_4_estimated_cost_usd, 6):.6f}.",
                ],
                phase_4_rooms,
                phase_4_variant_count,
                phase_4_estimated_input_tokens,
                round(phase_4_estimated_cost_usd, 6),
            ),
            PhasePlan(5, FUTURE_PHASES[5], "would_run" if missing_identity_tag_rooms else "would_skip", missing_identity_tag_rooms, ["identity_tags"], [f"{len(missing_identity_tag_rooms)} rooms are missing identity-tag structure."], len(missing_identity_tag_rooms)),
            PhasePlan(6, FUTURE_PHASES[6], "would_run" if npc_gap_rooms else "would_skip", npc_gap_rooms, ["npcs"], [f"{len(npc_gap_rooms)} rooms currently have no NPC coverage."], len(npc_gap_rooms)),
            PhasePlan(7, FUTURE_PHASES[7], "would_run" if item_gap_rooms else "would_skip", item_gap_rooms, ["items"], [f"{len(item_gap_rooms)} rooms currently have no item coverage."], len(item_gap_rooms)),
            PhasePlan(8, FUTURE_PHASES[8], "would_run" if quest_gap_rooms else "would_skip", quest_gap_rooms, ["quest_hooks"], [f"{len(quest_gap_rooms)} rooms currently have no quest hook stubs."], len(quest_gap_rooms)),
            PhasePlan(9, FUTURE_PHASES[9], "would_run" if doorway_rooms else "would_skip", doorway_rooms, ["doorway_rooms"], [f"{len(doorway_rooms)} doorway relationships would need parent/child coordination."], len(doorway_rooms)),
            PhasePlan(10, FUTURE_PHASES[10], "would_run" if score_gap_rooms else "would_skip", score_gap_rooms, ["repair"], [f"{len(score_gap_rooms)} rooms currently need score-driven repair."], len(score_gap_rooms)),
        ]
        return plans

    def checkpoint(self, phase_name: str) -> Path:
        state = self._require_working_state()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_name = f"{state['zone_id']}_{phase_name}_{timestamp}.yaml"
        path = self.checkpoint_dir / file_name
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(state, handle, sort_keys=False)
        self.checkpoints.append(str(path))
        return path

    def run_all_implemented_phases(self) -> OrchestrationResult:
        self.load_zone()
        self.get_baseline_score(label="load")
        phase_1 = self.run_phase_1_zone_type_setup()
        phase_1_checkpoint = self.checkpoint("phase_1_zone_type_setup")
        phase_1.checkpoint_path = str(phase_1_checkpoint)
        self.get_baseline_score(label="after_phase_1")

        phase_2 = self.run_phase_2_geographic_structure()
        phase_2_checkpoint = self.checkpoint("phase_2_geographic_structure")
        phase_2.checkpoint_path = str(phase_2_checkpoint)
        self.get_baseline_score(label="after_phase_2")

        self.run_phase_3_room_descriptions()
        self.get_baseline_score(label="after_phase_3")

        self.run_phase_4_stateful_descriptions()
        self.get_baseline_score(label="after_phase_4")

        plan = self.dry_run_plan()
        state = self._require_working_state()
        warnings = [warning for result in self.phase_results for warning in result.warnings]
        return OrchestrationResult(
            zone_id=state["zone_id"],
            zone_type=state.get("zone_type"),
            phase_results=list(self.phase_results),
            scores=list(self.score_history),
            plan=plan,
            checkpoints=list(self.checkpoints),
            warnings=warnings,
        )

    def _require_working_state(self) -> dict[str, Any]:
        if self.working_state is None:
            raise RuntimeError("Zone must be loaded before orchestration can run.")
        return self.working_state

    def _room_id(self, room: dict[str, Any]) -> str:
        return str(room.get("id") or room.get("name") or "").strip()

    def _has_identity_tags(self, room: dict[str, Any]) -> bool:
        tags = dict(room.get("tags") or {})
        return bool(
            str(tags.get("structure") or "").strip()
            or str(tags.get("specific_function") or "").strip()
            or str(tags.get("named_feature") or "").strip()
            or str(tags.get("condition") or "").strip()
            or list(tags.get("custom") or [])
        )

    def _room_npc_count(self, room: dict[str, Any]) -> int:
        room_id = self._room_id(room)
        placements = list(dict(self._require_working_state().get("placements") or {}).get("npcs") or [])
        placement_count = sum(1 for placement in placements if str(placement.get("room") or "").strip() == room_id)
        return placement_count + len(list(room.get("npcs") or []))

    def _room_item_count(self, room: dict[str, Any]) -> int:
        room_id = self._room_id(room)
        placements = list(dict(self._require_working_state().get("placements") or {}).get("items") or [])
        placement_count = sum(1 for placement in placements if str(placement.get("room") or "").strip() == room_id)
        return placement_count + len(list(room.get("items") or []))

    def _doorway_room_ids(self) -> list[str]:
        state = self._require_working_state()
        payload = dict(state.get("geographic_structure") or {})
        doorway_room_ids: list[str] = []
        for key in ("doorway_rooms", "exits_to_parent"):
            for entry in list(payload.get(key) or []):
                if not isinstance(entry, dict):
                    continue
                for field in ("parent_room", "child_room", "room"):
                    room_id = str(entry.get(field) or "").strip()
                    if room_id and room_id not in doorway_room_ids:
                        doorway_room_ids.append(room_id)
        return doorway_room_ids

    def _build_phase_3_generation_context(self, room: dict[str, Any]) -> dict[str, Any]:
        state = self._require_working_state()
        generation_context = dict(state.get("generation_context") or {})
        generation_context["geographic_context"] = self._build_room_geographic_context(self._room_id(room))
        return generation_context

    def _build_phase_4_generation_context(self, room: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
        generation_context = self._build_phase_3_generation_context(room)
        generation_context["state_context"] = {
            "group": target["group"],
            "state": target["state"],
            "state_key": target["state_key"],
            "narrative_hint": target["narrative_hint"],
        }
        return generation_context

    def _build_room_geographic_context(self, room_id: str) -> dict[str, Any]:
        state = self._require_working_state()
        zone_type = str(state.get("zone_type") or "").strip()
        structure = dict(state.get("geographic_structure") or {})
        context: dict[str, Any] = {"zone_type": zone_type}

        if zone_type == "outdoor_city":
            context["streets"] = self._matching_entries(structure.get("streets"), room_id, room_lists=("rooms",))
            context["districts"] = self._matching_entries(structure.get("districts"), room_id, room_lists=("rooms",))
            context["visible_landmarks"] = self._matching_entries(structure.get("landmarks"), room_id, room_lists=("visible_from_rooms", "rooms"))
            context["gates"] = self._matching_entries(structure.get("gates"), room_id, room_fields=("room",))
            context["doorway_rooms"] = self._matching_entries(structure.get("doorway_rooms"), room_id, room_fields=("parent_room",), room_lists=("rooms",))
        elif zone_type == "wilderness":
            context["trails"] = self._matching_entries(structure.get("trails"), room_id, room_lists=("rooms",))
            context["rivers"] = self._matching_entries(structure.get("rivers"), room_id, room_lists=("rooms",))
            context["named_areas"] = self._matching_entries(structure.get("named_areas"), room_id, room_lists=("rooms",))
            context["ranges"] = self._matching_entries(structure.get("ranges"), room_id, room_lists=("rooms",))
            context["visible_landmarks"] = self._matching_entries(structure.get("landmarks"), room_id, room_lists=("visible_from_rooms", "rooms"))
            context["doorway_rooms"] = self._matching_entries(structure.get("doorway_rooms"), room_id, room_fields=("parent_room",), room_lists=("rooms",))
        elif zone_type in {"interior_medium", "interior_large"}:
            context["halls"] = self._matching_entries(structure.get("halls"), room_id, room_lists=("rooms",))
            context["wings"] = self._matching_entries(structure.get("wings"), room_id, room_lists=("rooms",))
            context["floors"] = self._matching_entries(structure.get("floors"), room_id, room_lists=("rooms",))
            context["named_chambers"] = self._matching_entries(structure.get("named_chambers"), room_id, room_fields=("room",))
            context["exits_to_parent"] = self._matching_entries(structure.get("exits_to_parent"), room_id, room_fields=("child_room",))
        elif zone_type == "interior_small":
            context["exits_to_parent"] = self._matching_entries(structure.get("exits_to_parent"), room_id, room_fields=("child_room",))
        elif zone_type == "transit":
            context["routes"] = self._matching_entries(structure.get("routes"), room_id, room_lists=("rooms",))
            context["waypoints"] = self._matching_entries(structure.get("waypoints"), room_id, room_fields=("room",), room_lists=("rooms",))
            context["doorway_rooms"] = self._matching_entries(structure.get("doorway_rooms"), room_id, room_fields=("parent_room",), room_lists=("rooms",))
        return context

    def _matching_entries(
        self,
        entries: object,
        room_id: str,
        *,
        room_fields: tuple[str, ...] = (),
        room_lists: tuple[str, ...] = (),
    ) -> list[dict[str, str]]:
        matches: list[dict[str, str]] = []
        for entry in list(entries or []):
            if not isinstance(entry, dict):
                continue
            matched = any(str(entry.get(field) or "").strip() == room_id for field in room_fields)
            if not matched:
                for room_list in room_lists:
                    values = [str(value or "").strip() for value in list(entry.get(room_list) or []) if str(value or "").strip()]
                    if room_id in values:
                        matched = True
                        break
            if matched:
                matches.append(
                    {
                        key: str(value or "").strip()
                        for key, value in entry.items()
                        if key not in {"rooms", "visible_from_rooms", "room", "parent_room", "child_room"}
                        and str(value or "").strip()
                    }
                )
        return matches

    def _summarize_geographic_context(self, geographic_context: dict[str, Any]) -> str:
        summaries: list[str] = []
        labels = {
            "streets": "street",
            "districts": "district",
            "visible_landmarks": "landmark",
            "trails": "trail",
            "rivers": "river",
            "named_areas": "named area",
            "ranges": "range",
            "halls": "hall",
            "wings": "wing",
            "floors": "floor",
            "named_chambers": "named chamber",
            "routes": "route",
            "waypoints": "waypoint",
            "gates": "gate",
        }
        for key, label in labels.items():
            names = [str(entry.get("name") or "").strip() for entry in list(geographic_context.get(key) or []) if isinstance(entry, dict) and str(entry.get("name") or "").strip()]
            if names:
                summaries.append(f"{label}: {', '.join(names)}")
        if not summaries and str(geographic_context.get("zone_type") or "") == "outdoor_city":
            summaries.append("not on a named street")
        return "; ".join(summaries) or "no named geographic assignment"

    def _estimate_prompt_tokens(self, prompt_text: str) -> int:
        return max(1, len(str(prompt_text or "")) // 4)

    def _phase_4_target_states(self, room: dict[str, Any]) -> list[dict[str, Any]]:
        state = self._require_working_state()
        generation_context = dict(state.get("generation_context") or {})
        applicable_groups = determine_applicable_state_groups(room, state, generation_context)
        applicable_state_values = determine_applicable_states(applicable_groups)
        applicable_state_set = {str(value or "").strip() for value in applicable_state_values if str(value or "").strip()}
        climate = str(generation_context.get("climate") or "").strip().lower()
        compatible_weather = set(self._compatible_weather_states(climate)) if climate else set()
        targets: list[dict[str, Any]] = []

        for group in applicable_groups:
            allowed_states = dict(STATEFUL_VARIANT_ALLOWLIST.get(group) or {})
            if not allowed_states:
                continue
            for state_name, narrative_hint in allowed_states.items():
                if state_name not in applicable_state_set:
                    continue
                if group == "weather" and compatible_weather and state_name not in compatible_weather:
                    continue
                state_key = f"{group}_{state_name}"
                targets.append(
                    {
                        "group": group,
                        "state": state_name,
                        "state_key": state_key,
                        "narrative_hint": narrative_hint,
                        "applicable_groups": applicable_groups,
                        "applicable_states": applicable_state_values,
                    }
                )
        return targets

    def _compatible_weather_states(self, climate: str) -> list[str]:
        climate_key = str(climate or "").strip().lower()
        if not climate_key:
            return []
        compatibility = self._load_climate_weather_compatibility()
        return [str(value or "").strip() for value in list(compatibility.get(climate_key) or []) if str(value or "").strip()]

    def _load_climate_weather_compatibility(self) -> dict[str, list[str]]:
        repo_root = Path(__file__).resolve().parents[3]
        path = repo_root / "world" / "content" / "climate_weather_compatibility.yaml"
        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(key or "").strip().lower(): [str(value or "").strip() for value in list(values or []) if str(value or "").strip()]
            for key, values in payload.items()
            if str(key or "").strip()
        }

    def _create_room_description_generator(self):
        from world.builder.services.anthropic_client import RoomDescriptionGenerator

        return RoomDescriptionGenerator()