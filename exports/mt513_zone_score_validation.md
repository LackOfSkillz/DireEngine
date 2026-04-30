# MT-513 Zone Score Validation

## Scope
Validated the MT-513 Zone Score V1 implementation against both sources:
- `docs/mt513_zone_score_dispatch.md`
- `world/races/zonescore.md`

## Live UI Validation

### Builder2 (`/direbuilder/?zone=builder2`)
- Header rendered as `DireEngine ZoneScore — We build better zones by building better builders.`
- Tooltip icon rendered on the Zone Score header.
- Composite and sub-scores rendered correctly.
  - Composite: `57`
  - Tier: `Rough`
  - Completeness: `63`
  - Depth: `6`
  - Engagement: `100`
- Panel defaulted collapsed, expanded correctly, and rendered all four sections:
  - Completeness
  - Depth
  - Engagement
  - Needs Attention / All Rooms
- Needs Attention room click selected `CRO_450_350` in the editor.
- `Show all rooms` expanded the room list and `Show fewer rooms` was available afterward.
- Stale/save/refetch cycle verified.
  - Dirty edit made the stale marker visible.
  - Save cleared the stale marker.
  - Score payload `computed_at` advanced on refetch.
  - Verified timestamps: `2026-04-30T19:33:34.932246Z` -> `2026-04-30T19:33:45.029616Z` -> `2026-04-30T19:33:45.349023Z`

### new_landing (`/direbuilder/?zone=new_landing`)
- Header and score strip rendered correctly on the 211-room zone.
- Score payload rendered correctly.
  - Composite: `48`
  - Tier: `Sketch`
  - Completeness: `71`
  - Depth: `25`
  - Engagement: `40`
- Reloaded page retained score rendering and subsequent browser fetch measured `204ms`.

## Score Endpoint Validation

### Payload Shape
Validated live responses for both `builder2` and `new_landing` include:
- `composite`
- `tier`
- `completeness`
- `depth`
- `engagement`
- `rooms_needing_attention`
- `room_scores`
- `room_count`
- `computed_at`
- `zone_id`

### Timing
Steady-state live endpoint timings after switching builder YAML reads to PyYAML's C-backed safe loader:
- `builder2`: `57ms` browser fetch, `167ms` PowerShell fetch after restart
- `new_landing`: `204ms` browser fetch on the reloaded page, `240ms` warmed PowerShell fetch

Cold-start note after web-server restart:
- The first `new_landing` request after restart measured `3584ms` while the server/path warmed.
- Subsequent live requests dropped under the `500ms` target.

## Quest Hooks Validation
- No `quest_hooks` UI was added to DireBuilder.
- Temporarily edited `worlddata/zones/builder2.yaml` to set one room's `quest_hooks` to `['test_hook']`.
- Reloaded/fetched live score endpoint and confirmed `engagement.breakdown.quests_pct` changed from `0` to `0.1667`.
- Restored `worlddata/zones/builder2.yaml` immediately afterward.
- Final live check confirmed `quests_pct` returned to `0`.

## Legacy Builder Isolation
- `/builder/` still loads.
- No Zone Score UI is present there.
- No `quest_hooks` references are present in the legacy builder UI.

## Scope Guard Check
- Engine systems were not modified.
- AI pipeline wiring was not modified.
- Legacy `/builder/` behavior remained isolated from MT-513 changes.

## Result
MT-513 Zone Score V1 is implemented, live-validated, and documented.
The warm live path now meets the `sub-500ms` requirement for the 211-room zone.