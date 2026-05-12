# Zone Orchestration

## Overview

MT-600a introduced the first concrete orchestration layer for AI zone generation. MT-600c extends that surface with the first real content-producing phase: Phase 3 room description generation. The orchestrator now loads a working zone artifact, validates Phase 1 (`zone_type` plus generation-context seed fields), validates Phase 2 (human-authored geographic structure), generates Phase 3 room descriptions for rooms whose `desc` field is empty, captures ZoneScore baselines, emits a dry-run plan for later phases, and writes checkpoints between implemented phases.

Phase 3 uses the canonical DireBuilder two-pass generator but persists pass-1 plain prose to the room `desc` field. This keeps state-markup augmentation from becoming authoritative before MT-600d handles stateful descriptions explicitly.

## API

Public entrypoint: `world.builder.orchestration.zone_orchestrator.ZoneOrchestrator`

Implemented methods:

- `load_zone()`
- `run_phase_1_zone_type_setup()`
- `run_phase_2_geographic_structure()`
- `run_phase_3_room_descriptions()`
- `get_baseline_score(label="baseline")`
- `dry_run_plan()`
- `checkpoint(phase_name)`
- `run_all_implemented_phases()`

Structured outputs:

- `PhaseResult`
- `PhasePlan`
- `ScoreSnapshot`
- `OrchestrationResult`

## Working State Model

The working state is a YAML-serializable dict matching the canonical zone artifact shape. MT-600a preserves the existing top-level fields and adds support for:

- `zone_type`
- `generation_context.emotional_tone`
- `generation_context.cultural_signature`
- `geographic_structure`

Checkpoint files write the full working state back to YAML so subsequent phases can resume from a persisted intermediate artifact later.

## Phase 1: Zone-Type Setup

Phase 1 reads and validates:

- `zone_type`
- `generation_context.emotional_tone`
- `generation_context.cultural_signature`

`zone_type` is required and must be one of the six locked values. The two generation-context fields are recommended but not required in MT-600a; missing values produce warnings instead of hard failure.

## Phase 2: Geographic Structure

Phase 2 is validation-only in MT-600a.

The orchestrator validates human-authored geographic structure against the room list for the zone. It does not invent street names, district layouts, or hallway structures. This keeps the authoritative geographic layer human-authored and prevents fabricated geography from entering the pipeline before prose generation starts.

Supported zone-type structures:

- `outdoor_city`: streets, intersections, districts, landmarks, gates, doorway rooms
- `wilderness`: trails, rivers, named areas, ranges, landmarks, doorway rooms
- `interior_medium` / `interior_large`: halls, wings, floors, named chambers, exits to parent
- `interior_small`: exits to parent only
- `transit`: routes, waypoints, doorway rooms

All local room references are validated against the actual zone room ids.

## Phase 3: Room Descriptions

Phase 3 is the first phase that invokes the canonical AI generation path.

The orchestrator iterates over rooms whose `desc` field is empty, builds a per-room generation context, and calls `world.builder.services.anthropic_client.RoomDescriptionGenerator.generate(...)`. Each per-room context includes:

- zone-level `generation_context`
- `emotional_tone`
- `cultural_signature`
- `geographic_context` derived from the Phase 2 geographic structure

The prompt-rendering extension is intentionally minimal. `build_room_description_user_message(...)` now renders the additional context when present and remains a no-op for callers that do not supply it.

Geographic context is added as explicit constraint text rather than as soft suggestion. For example, if a room belongs to `Market Street` in the `Market District` with `Old Bell Tower` visible, the prompt tells the generator to reference those names exactly when relevant and not invent new ones.

The orchestrator does not feed neighboring room descriptions into prompt assembly. Phase 3 remains room-local by design.

### Geographic Structure Consumption Pattern

The orchestrator derives room-local geographic context from the Phase 2 validated structure according to zone type:

- `outdoor_city`: streets, districts, visible landmarks, gates, doorway rooms
- `wilderness`: trails, rivers, named areas, ranges, visible landmarks, doorway rooms
- `interior_medium` / `interior_large`: halls, wings, floors, named chambers, exits to parent
- `interior_small`: exits to parent
- `transit`: routes, waypoints, doorway rooms

These lookups are read-only. Phase 3 does not mutate the geographic structure.

### Pass-1 vs Pass-2

The canonical DireBuilder client still runs both passes internally. MT-600c persists pass-1 prose into `room.desc` and treats pass-2 state-markup output as non-authoritative telemetry. This keeps Phase 3 aligned with the dispatch boundary while avoiding client changes.

### Failure Handling

Per-room generation failures are non-fatal. The orchestrator records the room id and failure reason, leaves the room `desc` empty, and moves on. If every target room fails, Phase 3 reports overall failure while allowing later scoring and dry-run inspection to continue.

## Phases 4-10

MT-600c implements Phase 3 only. Dry-run reporting continues to expose the future work surface for the remaining phases:

- Phase 4: stateful descriptions
- Phase 5: identity tags
- Phase 6: NPC rosters
- Phase 7: item placements
- Phase 8: quest hook stubs
- Phase 9: doorway coordination
- Phase 10: score-driven repair

## Checkpoint Persistence

`checkpoint(phase_name)` writes the full working state to:

- default: `artifacts/zone_orchestration_checkpoints/`
- custom: caller-supplied checkpoint directory

Filename shape:

- `{zone_id}_{phase_name}_{timestamp}.yaml`

Resume is not implemented in MT-600a. That remains a follow-up concern.

## Dry-Run Mode

`dry_run_plan()` inspects the current working state and reports what later phases would do without invoking any generators.

Current dry-run signals include:

- rooms missing base descriptions
- per-room geographic context summaries for Phase 3 targets
- estimated Phase 3 prompt token counts and input-only cost
- rooms with applicable state groups but no `stateful_descs`
- rooms missing identity-tag coverage
- rooms without NPC coverage
- rooms without item coverage
- rooms without quest hooks
- doorway relationships needing coordination
- rooms currently flagged by ZoneScore as needing repair

This is the main inspection surface for MT-600a. It proves the orchestrator can reason over the zone artifact before any AI-backed generation is enabled.

## Live Verification Execution Pattern

Multi-call live verification should run through a terminal-invoked Python harness rather than through Pylance snippet execution.

Reason:

- Pylance snippet execution is suitable for short bounded checks but becomes fragile for orchestrator phases that make many real model calls.
- The practical failure modes are timeout ceilings, lost progress visibility, and agent-loop interruption during long-running verification.

Canonical invocation:

```powershell
c:/Users/gary/dragonsire/.venv/Scripts/python.exe tools/orchestrator_live_verify.py --fixture tests/fixtures/mt600a_fixture_zone.yaml --phase 4 --cost-ceiling 2.00 --output exports/
```

Harness behavior:

- bootstraps Django with `DJANGO_SETTINGS_MODULE=server.conf.settings` and `django.setup()`
- runs the requested phase against the requested fixture using the existing orchestrator API
- enforces a pre-flight cost ceiling before real generation starts
- writes a markdown report to `exports/orchestrator_live_verify_phase_<n>_<timestamp>.md`
- exits with stable status codes

Exit code semantics:

- `0`: success
- `1`: partial-success
- `2`: failure
- `3`: cost-ceiling abort

When to use what:

- Mocked tests: every code change, always via `pytest`
- Live verification: once per phase before ship, through `tools/orchestrator_live_verify.py`

This keeps mocked validation fast and deterministic while moving real multi-call verification onto the same terminal execution model used for normal production-style Python runs.