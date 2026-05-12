# MT-600a validation

Status: SHIPPED

## Phase A — Infrastructure confirmed

- Existing zone artifact loading is permissive in the runtime import path.
- DireBuilder normalization was dropping unknown top-level fields, so MT-600a extended that boundary to preserve `zone_type` and `geographic_structure`.
- `score_zone(...)` already accepts raw zone dicts and returns the score shape the orchestrator needs.

## Phase B — Orchestrator module

- File location: `world/builder/orchestration/zone_orchestrator.py`
- Public API: `ZoneOrchestrator`, `PhaseResult`, `PhasePlan`, `ScoreSnapshot`, `OrchestrationResult`
- Package export added at `world/builder/orchestration/__init__.py`

## Phase C — Phase 1: Zone-type setup

- `zone_type` validation implemented for all six locked values.
- `generation_context.emotional_tone` and `generation_context.cultural_signature` are now preserved by schema normalization.
- Missing tone/signature produce warnings rather than hard failure, matching the dispatch.

## Phase D — Geographic structure data model

- New schema/validator at `world/builder/schemas/geographic_structure_schema.py`
- Supports all six locked zone types.
- Validates local room references across streets, districts, landmarks, doorway rooms, trails, halls, wings, floors, and exits-to-parent.

## Phase E — Phase 2: Geographic structure (validation-only)

- MT-600a validates human-authored geographic structure only.
- Missing structure initializes an empty typed placeholder and emits warnings.
- Dangling room references hard-fail the phase.

## Phase F — Dry-run plan

- Reports future work for phases 3-10 without invoking any generator.
- Current dry-run signals include missing descriptions, missing stateful descriptions, missing identity tags, NPC/item/quest coverage gaps, doorway coordination, and score-driven repair targets.

## Phase G — Score wiring

- Baseline score snapshots are captured from `score_zone(...)`.
- Current labels emitted by the orchestrator run: `load`, `after_phase_1`, `after_phase_2`, `dry_run`.

## Phase H — Checkpoint persistence

- Checkpoint files write after each implemented phase.
- Format is full zone YAML.
- Resume is not implemented in MT-600a.

## Phase I — Tests

Focused validation run:

- `tests/test_builder_zone_list.py`
- `tests/test_zone_orchestration_schema.py`
- `tests/test_zone_orchestrator.py`

Result:

- `19 passed in 4.35s`

## Phase J — Live verification

Fixture used:

- `tests/fixtures/mt600a_fixture_zone.yaml`

Live verification run patched both AI generation entrypoints to raise if called:

- `world.builder.services.anthropic_client.RoomDescriptionGenerator.generate`
- `world.builder.services.llm_client.LocalLLMClient.generate`

Verbatim result summary:

```python
{
	'zone_id': 'mt600a_fixture',
	'zone_type': 'outdoor_city',
	'phase_statuses': [
		{
			'phase': 'phase_1_zone_type_setup',
			'status': 'success',
			'warnings': [],
			'checkpoint': 'C:\\Users\\gary\\AppData\\Local\\Temp\\tmpsr4_9ugs\\mt600a_fixture_phase_1_zone_type_setup_20260502T141907Z.yaml'
		},
		{
			'phase': 'phase_2_geographic_structure',
			'status': 'success',
			'warnings': [],
			'checkpoint': 'C:\\Users\\gary\\AppData\\Local\\Temp\\tmpsr4_9ugs\\mt600a_fixture_phase_2_geographic_structure_20260502T141907Z.yaml'
		}
	],
	'score_labels': ['load', 'after_phase_1', 'after_phase_2', 'dry_run'],
	'plan': [
		{'phase': 3, 'status': 'would_run', 'actions': 3},
		{'phase': 4, 'status': 'would_run', 'actions': 5},
		{'phase': 5, 'status': 'would_skip', 'actions': 0},
		{'phase': 6, 'status': 'would_run', 'actions': 4},
		{'phase': 7, 'status': 'would_run', 'actions': 4},
		{'phase': 8, 'status': 'would_run', 'actions': 4},
		{'phase': 9, 'status': 'would_run', 'actions': 1},
		{'phase': 10, 'status': 'would_run', 'actions': 5}
	],
	'checkpoints': [
		'C:\\Users\\gary\\AppData\\Local\\Temp\\tmpsr4_9ugs\\mt600a_fixture_phase_1_zone_type_setup_20260502T141907Z.yaml',
		'C:\\Users\\gary\\AppData\\Local\\Temp\\tmpsr4_9ugs\\mt600a_fixture_phase_2_geographic_structure_20260502T141907Z.yaml'
	],
	'ai_calls': {'anthropic': 0, 'local_llm': 0}
}
```

This confirms:

- Phase 1 and Phase 2 run end-to-end on a real fixture zone.
- Dry-run plan generation works.
- Checkpoints are written.
- No AI generators were invoked.

## Phase K — Documentation

- `docs/architecture/zone_orchestration.md` added.

## Final state

MT-600a shipped. Orchestrator skeleton in place. Phase 1 (zone-type setup) and Phase 2 (geographic structure validation) implemented. Dry-run mode reports what subsequent phases would do. Checkpoint persistence between phases. Score baseline read. No AI generators invoked. Ready for MT-600c and beyond.