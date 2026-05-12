# MT-600c validation

Status: SHIPPED

Ship time:

- `2026-05-02 10:46:15 -04:00`
- Equivalent UTC ship mark: `2026-05-02 14:46:15Z`

## Phase A — DireBuilder API confirmed

- Canonical generator: `world.builder.services.anthropic_client.RoomDescriptionGenerator`
- Public method: `generate(room_context: dict, applicable_groups: list[str], applicable_states: list[str]) -> dict`
- Execution model: sync
- Returned shape:
  - `pass_1`
  - `pass_2`
  - `input_tokens`
  - `output_tokens`
  - `elapsed_ms`
  - `approximate_cost_usd`
- Error modes surfaced through the existing web path and generator call surface include validation failure, authentication failure, permission failure, bad request, generic API failure, timeout, and unexpected runtime exceptions.

Notes:

- The generator is service-level and does not require a Django request context.
- For standalone live verification, `DJANGO_SETTINGS_MODULE=server.conf.settings` and `django.setup()` were required before importing the orchestrator path that lazy-loads the generator. This did not require a running Evennia game session, but it is a real bootstrap detail worth preserving.

## Phase B — Geographic context integration

Minimal approved extension shipped in `world/builder/prompting/room_description_prompt.py`.

`build_room_description_user_message(...)` now renders these optional `generation_context` fields when present:

- `geographic_context`
- `emotional_tone`
- `cultural_signature`

No-op behavior remains intact when those fields are absent.

Per-room geographic context is derived from Phase 2 validated structure and passed through `generation_context.geographic_context`. The final prompt wording used for the successful live pass enforced:

- named street mention when a street assignment exists
- named district mention when a district assignment exists
- exact-name usage for listed geographic features
- no invention of new street, district, landmark, trail, hall, wing, chamber, route, or area names
- emotional tone must be legible in at least one sentence rather than merely implied

## Phase C — Phase 3 implementation

Primary file:

- `world/builder/orchestration/zone_orchestrator.py`

Shipped changes:

- `run_phase_3_room_descriptions()` implemented
- per-room generation context assembly added
- geographic context lookup by zone type added
- per-room failure capture added
- pass-1 prose persisted to room `desc`
- batch checkpointing added for Phase 3
- dry-run Phase 3 reporting now includes:
  - rooms needing descriptions
  - per-room geographic summaries
  - estimated prompt tokens
  - estimated input-only cost

Checkpointing approach:

- Phase 3 uses a batch checkpoint policy
- Current batch size: `10`
- On the live fixture run with 3 target rooms, one Phase 3 checkpoint was written at the end of the batch

Pass handling:

- The canonical client still runs both passes internally
- MT-600c persists `pass_1` plain prose into `room.desc`
- `pass_2` is treated as non-authoritative telemetry for now

## Phase D — Failure handling

Per-room generation failures are non-fatal.

Behavior:

- failed room remains with empty `desc`
- failure recorded in `PhaseResult.rooms_failed`
- warning message recorded
- orchestrator continues to the next room

Overall Phase 3 status rules:

- `success`: all targeted rooms generated
- `partial-success`: at least one room generated and at least one failed
- `failure`: target rooms existed but none generated

No retry loop shipped. This matches the dispatch.

## Phase E — Dry-run plan updated

Phase 3 dry-run output is now concrete rather than only a room count.

Current Phase 3 dry-run surfaces:

- target room ids
- per-room geographic summary
- estimated prompt tokens per room
- total estimated input prompt tokens
- total estimated input-only cost

Other phases remain rough estimates, which is still within scope.

## Phase F — Tests

Focused regression run:

- `tests/test_builder_zone_list.py`
- `tests/test_zone_orchestration_schema.py`
- `tests/test_room_description_prompt.py`
- `tests/test_zone_orchestrator.py`

Result:

- `51 passed in 3.73s`

Mock discipline:

- All automated Phase 3 tests used mocked generation
- No test consumed real API tokens

Key coverage added:

- prompt builder backward compatibility when new fields are absent
- prompt builder rendering of geographic context, emotional tone, and cultural signature
- Phase 3 generation for empty rooms only
- existing descriptions are preserved
- geographic context is passed per-room
- per-room failure handling
- total failure handling
- checkpoint writing
- Phase 3 participation in `run_all_implemented_phases()`

## Phase G — Live verification

Fixture used:

- `tests/fixtures/mt600a_fixture_zone.yaml`

Fixture shape relevant to Phase 3:

- 3 target rooms with empty `desc`
- `Market Street` assignment
- `Market District` assignment
- visible landmark `Old Bell Tower`
- `generation_context.emotional_tone = bustling and hopeful`
- `generation_context.cultural_signature = human frontier port town`

Final successful live run summary:

```python
{
    'status': 'success',
    'rooms_succeeded': ['market_square', 'smith_lane', 'harbor_road'],
    'rooms_failed': [],
    'duration_ms': 40354,
    'checkpoint_path': 'C:\\Users\\gary\\AppData\\Local\\Temp\\tmpbp9idhg4\\checkpoints\\mt600a_fixture_phase_3_room_descriptions_20260502T144550Z.yaml',
    'actual_cost_usd': 0.053976,
    'input_tokens': 11752,
    'output_tokens': 1248,
    'prompt_contexts': [
        {
            'room_id': 'market_square',
            'geographic_context': {
                'zone_type': 'outdoor_city',
                'streets': [{'name': 'Market Street', 'type': 'street', 'runs': 'north-south', 'district': 'market_district'}],
                'districts': [{'name': 'Market District', 'slug': 'market_district', 'character': 'bustling, commercial, mid-quality'}],
                'visible_landmarks': [{'name': 'Old Bell Tower', 'slug': 'old_bell_tower', 'type': 'tower', 'description_seed': 'weathered stone belfry with silent bells'}],
                'gates': [],
                'doorway_rooms': []
            },
            'geographic_summary': 'street: Market Street; district: Market District; landmark: Old Bell Tower',
            'estimated_prompt_tokens': 397
        },
        {
            'room_id': 'smith_lane',
            'geographic_context': {
                'zone_type': 'outdoor_city',
                'streets': [{'name': 'Market Street', 'type': 'street', 'runs': 'north-south', 'district': 'market_district'}],
                'districts': [{'name': 'Market District', 'slug': 'market_district', 'character': 'bustling, commercial, mid-quality'}],
                'visible_landmarks': [],
                'gates': [],
                'doorway_rooms': []
            },
            'geographic_summary': 'street: Market Street; district: Market District',
            'estimated_prompt_tokens': 363
        },
        {
            'room_id': 'harbor_road',
            'geographic_context': {
                'zone_type': 'outdoor_city',
                'streets': [],
                'districts': [],
                'visible_landmarks': [],
                'gates': [],
                'doorway_rooms': []
            },
            'geographic_summary': 'not on a named street',
            'estimated_prompt_tokens': 308
        }
    ]
}
```

Verbatim generated descriptions from the successful run:

### `market_square`

> Market Square opens wide where Market Street runs north and south through the Market District, its worn cobbles spreading around a central fountain whose basin shows years of steady use. Market stalls line the square's edges, their timber frames weathered but upright, and the stone pavement between them carries the scuff and stain of constant foot traffic. The Old Bell Tower rises visible to the east, its silhouette a familiar mark above the rooftops, and the square hums with the motion of merchants and buyers moving between the stalls.

### `smith_lane`

> Smith Lane cuts east from Market Street into a narrow alley between timber-framed buildings, their upper stories leaning close enough to nearly meet overhead. The packed earth underfoot shows steady traffic, worn smooth by the passage of carts and foot traffic serving the Market District's workshops. Fresh sawdust and wood shavings scatter near the eastern end, marking where craftsmen clear their doorways each morning.

### `harbor_road`

> Harbor Road runs straight and wide between timber-framed buildings that lean slightly toward the street, their upper stories jutting out over the lower. The packed earth underfoot shows constant traffic, worn smooth down the center where carts and foot traffic pass most heavily. Voices carry from open doorways and the occasional shout echoes from further down the road, marking the steady flow of commerce and movement through this part of town.

Quality read:

- `market_square` explicitly names `Market Street`, `Market District`, and `Old Bell Tower`
- `smith_lane` explicitly names `Market Street` and `Market District`
- `harbor_road` had no named street/district assignment in `geographic_structure`, so the absence of those names is expected and correct
- all three descriptions read with a bustling, civic-commercial tone consistent with `emotional_tone = bustling and hopeful`
- no invented street or district names were introduced

Cost check:

- Final live verification cost: `$0.053976`
- Ceiling: `$5.00`
- Result: comfortably under ceiling

Prompt tuning note:

- The first live pass proved the plumbing but did not consistently name the district or make tone sufficiently legible.
- A bounded prompt wording adjustment was applied inside the approved scope of `build_room_description_user_message(...)`.
- The final live pass above is the acceptance run.

## Phase H — Documentation

Updated:

- `docs/architecture/zone_orchestration.md`

Added coverage for:

- Phase 3 room description generation
- geographic structure consumption pattern
- pass-1 persistence strategy
- Phase 3 failure semantics
- richer dry-run reporting

## Final state

MT-600c shipped. Phase 3 room description generation is wired to the canonical DireBuilder generator. Geographic structure context flows into the canonical prompt assembly path through `generation_context.geographic_context`, and the prompt now renders `emotional_tone` and `cultural_signature` when present with backward-compatible no-op behavior when absent. The orchestrator generates only rooms with empty descriptions, preserves existing descriptions, records per-room failures without retry, checkpoints Phase 3 progress, and updates dry-run reporting with per-room geographic summaries and estimated prompt cost. Live fixture verification produced real geographically-aware descriptions that named assigned street and district context where present and stayed well under the cost ceiling. Ready for MT-600d.