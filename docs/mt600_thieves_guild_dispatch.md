# MT-600-thieves-guild — Author and ship the thieves guild demo zone (revised)

## Background

The MT-600 arc has an orchestrator that generates AI-driven zone content (Phases 1-4 working as of MT-600d acceptance run via the new terminal harness). What it does not yet have is a complete, walkable zone that a player can experience end-to-end. The two existing test fixtures aren't game-grade, and `new_landing.yaml`'s descriptions don't match its intended character.

This dispatch builds a 20-room thieves guild zone hand-authored to a Hall-of-Miracles tonal seed, runs MT-600 Phases 1-4 against it, promotes the orchestrator's output back into the source YAML so the canonical zone file ends up populated, imports it into the live DireMUD server, and verifies walkability.

Cost projection (from MT-600c and MT-600d calibration):
- Phase 3: ~$0.36
- Phase 4: ~$2.10
- Phases 1-2: negligible
- Total: ~$2.50

Wall-clock projection: ~35-45 minutes for orchestrator phases plus import/walkability.

## Scope

This dispatch:

1. Authors `worlddata/zones/thieves_guild.yaml` as a 20-room hand-authored `interior_large` zone with the design specified below.
2. Runs orchestrator Phases 1-4 against it via `tools/orchestrator_live_verify.py`.
3. Promotes orchestrator output back into the source YAML after each phase (see Phase B persistence note).
4. Imports the zone into the live DireMUD server via `@zone load`.
5. Verifies walkability and NPC presence.
6. Documents results in `exports/mt600_thieves_guild_validation.md`.

This dispatch does NOT:
- Implement the stolen-goods economy (placeholder Vendor for the fence is fine; mechanics deferred).
- Implement the donation shelf rank-gated container (placeholder feature only).
- Implement guild rank progression hooks.
- Modify orchestrator, prompting, or schema code.
- Modify the import service.
- Modify any other zone.
- Tune prompts.

## Architectural guardrails

The implementation surface is:
- One new file: `worlddata/zones/thieves_guild.yaml`
- One new validation report: `exports/mt600_thieves_guild_validation.md`
- IN-SCOPE small extension: `tools/orchestrator_live_verify.py` may be extended with a `--write-back` flag (or a sibling small script in `tools/`) that promotes the orchestrator's final in-memory zone state from a phase's checkpoint back into the source YAML. This is a genuine tooling gap surfaced by this dispatch — production zones must end up populated, not stuck in checkpoints. Keep the extension surgical: it should read the phase result and prefer writing the orchestrator's final working state directly back to the source path when that state is available in a clean shape. Use checkpoint promotion only as a fallback when the orchestrator does not expose final state cleanly. No other harness behavior changes.

NO changes to:
- `world/builder/orchestration/`
- `world/builder/services/`
- `world/builder/prompting/`
- `world/builder/schemas/`
- `world/worlddata/services/import_zone_service.py`
- `commands/cmd_zone.py`
- Any test file under `tests/`

Stop-and-report triggers:
- If `interior_large` schema validation rejects the authored geographic_structure with a non-trivial mismatch (a field-name typo the agent can clearly correct without design judgment is fine to fix in place).
- If the `--write-back` extension can't cleanly promote final state or checkpoint -> source YAML for any technical reason.
- If projected cost from any phase pre-flight exceeds $5.00.
- If `@zone load thieves_guild --dry` reports errors the agent can't trace to obvious YAML typos.
- If walkability verification reveals broken exits not from authoring typos.
- If the live DireMUD server isn't accessible.

## Zone design — locked, do not improvise

### Tonal seed (for `generation_context`)

```yaml
generation_context:
  setting_type: thieves_guild_hideout
  era_feel: medieval_underclass
  climate: subterranean_temperate
  voice: theatrical, ironic, communal, hardscrabble
  culture:
    - underclass-fantasy
    - hidden-society
  mood:
    - torchlit
    - smoky
    - communal
    - boisterous
    - wary-of-outsiders
  banned_phrases: []
  emotional_tone: theatrical defiance, communal warmth and rough humor among rogues, wary of outsiders
  cultural_signature: a hidden underclass court where thieves invert the surface world's hierarchy — dignity through shared survival, mockery through inverted ritual, dignity in being the unseen
```

Hall of Miracles from Hunchback of Notre Dame: torchlit underground community, theatrical inversion of class, ragged finery, ironic dignity, dangerous-feeling to outsiders but warm and communal among insiders. Spilled-ale-and-rough-character haunt, not grimdark. People drink, argue, laugh, mock. Worn but proud.

### Zone metadata

```yaml
schema_version: v1
zone_id: thieves_guild
name: The Thieves Guild
zone_type: interior_large
```

### Geographic structure (interior_large schema)

Required keys per `world/builder/schemas/geographic_structure_schema.py`: `halls`, `wings`, `floors`, `named_chambers`, `exits_to_parent`.

Best-fit population for this zone (agent reconciles with the actual schema's inner shape):

- **halls** — connective corridors:
  - Entry Stair (false_alley -> threshold -> watcher_nook -> court_of_coins)
  - Training Corridor (court_of_coins -> branches into 4 training rooms)
  - Commerce Row (court_of_coins -> honest_stall -> fences_curtain -> quartermaster_hold)
  - Leadership Stair (court_of_coins -> throne_in_tatters -> reliquary -> vault)
  - Common Passage (court_of_coins -> common_hearth -> branches)

- **wings** — logical groupings:
  - Entry: false_alley, sewer_grate, threshold, watcher_nook
  - Common: court_of_coins, common_hearth, donation_shelf_room, drinking_pit, memorial_wall
  - Training: lockyard, marks_walk, shadowed_hall, the_pit
  - Commerce: honest_stall, fences_curtain, quartermaster_hold
  - Leadership: throne_in_tatters, reliquary, vault
  - Atmospheric: rookery

- **floors** — `ground` (layer 0) and `upper` (layer 1, for rookery only)

- **named_chambers** — standout rooms within the zone:
  - Court of Coins (court_of_coins) — the central hub
  - Throne in Tatters (throne_in_tatters)
  - Sharing Shelves (donation_shelf_room)
  - Memorial Wall (memorial_wall)
  - Reliquary (reliquary)
  - Vault (vault)
  - Rookery (rookery)
  - Drinking Pit (drinking_pit)
  - Fence's Curtain (fences_curtain)

- **exits_to_parent** — zone-exit points:
  - False Alley (false_alley) — surface alley entry
  - Sewer Grate (sewer_grate) — sewer entry from below

If the schema's actual inner field names within these keys differ from what this draft assumes, use the schema's names verbatim. The schema is authoritative.

### Required per-room map coordinates

Every room MUST have `map.x`, `map.y`, `map.layer` populated (enforced by the import service). The agent assigns coordinates that reflect the topology; layout doesn't need design judgment beyond "neighboring rooms should be adjacent." Suggested:
- Ground floor (layer 0): all rooms except rookery
- Upper floor (layer 1): rookery
- Court of Coins at origin (0, 0); other rooms placed relative to it

### The 20 rooms (locked layout)

**Entry vestibule:**
1. `false_alley` — The False Alley
2. `sewer_grate` — The Sewer Grate
3. `threshold` — The Threshold
4. `watcher_nook` — The Watcher's Nook

**Common wing:**
5. `court_of_coins` — The Court of Coins (hub)
6. `common_hearth` — The Common Hearth
7. `donation_shelf_room` — The Sharing Shelves
8. `drinking_pit` — The Drinking Pit
9. `memorial_wall` — The Memorial Wall

**Training wing:**
10. `lockyard` — The Lockyard (lockpick training)
11. `marks_walk` — The Mark's Walk (pickpocket training)
12. `shadowed_hall` — The Shadowed Hall (stealth training)
13. `the_pit` — The Pit (combat training)

**Commerce wing:**
14. `honest_stall` — The Honest Stall (legit gear)
15. `fences_curtain` — The Fence's Curtain (stolen goods buyer)
16. `quartermaster_hold` — The Quartermaster's Hold

**Leadership wing:**
17. `throne_in_tatters` — The Throne in Tatters (Guild Leader)
18. `reliquary` — The Reliquary
19. `vault` — The Vault

**Atmospheric:**
20. `rookery` — The Rookery (upper floor, accessed via stair from Court of Coins)

### Connection topology

Same as previously specified — Court of Coins is the central hub with 4 cardinal exits to wing corridors, plus an `up` exit to rookery. False Alley and Sewer Grate both lead to Threshold; Threshold leads to Watcher's Nook; Watcher's Nook leads to Court of Coins. Wing corridors branch into their respective rooms. Bidirectional exits unless room descriptions imply one-way (e.g., vault).

### NPCs (locked typeclasses)

| ID | Typeclass | Room |
|---|---|---|
| `guild_leader` | `typeclasses.npcs.NPC` | `court_of_coins` |
| `guild_merchant` | `typeclasses.vendor.Vendor` | `honest_stall` |
| `fence` | `typeclasses.vendor.Vendor` | `fences_curtain` |
| `lockpick_trainer` | `typeclasses.npcs.NPC` | `lockyard` |
| `pickpocket_trainer` | `typeclasses.npcs.NPC` | `marks_walk` |
| `stealth_trainer` | `typeclasses.npcs.NPC` | `shadowed_hall` |
| `combat_trainer` | `typeclasses.npcs.NPC` | `the_pit` |
| `quartermaster` | `typeclasses.vendor.Vendor` | `quartermaster_hold` |
| `watcher` | `typeclasses.npcs.guard.GuardNPC` | `watcher_nook` |

The fence using `Vendor` gives him a working buy/sell shell; the stolen-goods 50% mechanic is a placeholder for a separate arc. Do NOT create new typeclasses.

### Items

Place a minimal set; use the closest existing container/item typeclasses available (agent's call, document substitutions in validation report):
- `donation_shelf` in `donation_shelf_room`
- `weapon_rack_pit` in `the_pit`
- `lockpick_practice_set` in `lockyard`

### Quest hooks (string IDs only, deferred)

- `false_alley`: `[find_hidden_entrance]`
- `watcher_nook`: `[prove_yourself_to_guild]`
- `throne_in_tatters`: `[audience_with_leader]`
- `fences_curtain`: `[first_fence_transaction]`
- `donation_shelf_room`: `[observe_guild_custom]`

Other rooms: empty quest_hooks.

### Stateful descs

Empty `{}` in the authored YAML. Phase 4 fills these.

## Phases

### Phase A — Author the zone YAML

Create `worlddata/zones/thieves_guild.yaml`:
- All 20 rooms with `id`, `name`, `desc: ''`, `stateful_descs: {}`, `exits`, `terrain` (interior-appropriate), `environment` (per schema convention for interior rooms — likely `dungeon` or `interior`; agent uses what existing interior zones use), `tags`, and **`map.x`, `map.y`, `map.layer` populated**.
- `geographic_structure` populated per `interior_large` schema.
- `generation_context` populated per the tonal seed above.
- `placements.npcs` and `placements.items` populated per the tables above.
- File schema-validates clean.

Pass criteria: file exists, schema-validates, contains 20 rooms with locked IDs, every room has map coordinates.

### Phase B — Run orchestrator Phases 1-4 with write-back

Extend the harness or add a sibling tool to support write-back: after a phase completes successfully, the orchestrator's in-memory final state is written back into the source YAML so subsequent phases and the import see the populated zone. Prefer writing the final working state directly when it is available in a clean shape. Use the checkpoint emitted by the phase only as a fallback persistence source.

Then run sequentially:

```text
python tools/orchestrator_live_verify.py --fixture worlddata/zones/thieves_guild.yaml --phase 1 --cost-ceiling 0.10 --write-back
python tools/orchestrator_live_verify.py --fixture worlddata/zones/thieves_guild.yaml --phase 2 --cost-ceiling 0.10 --write-back
python tools/orchestrator_live_verify.py --fixture worlddata/zones/thieves_guild.yaml --phase 3 --cost-ceiling 1.00 --write-back
python tools/orchestrator_live_verify.py --fixture worlddata/zones/thieves_guild.yaml --phase 4 --cost-ceiling 4.00 --write-back
```

After Phase 3, spot-check 3 rooms (one training, one common, one leadership) for tonal match. If prose is wildly off-tone, stop and report before spending Phase 4 budget.

Pass criteria: status `success` for each phase, all 20 rooms with non-empty descs and non-empty stateful_descs in the source YAML on disk, total cost under $5.00.

### Phase C — Import to live DireMUD

In-game commands (canonical surface from `commands/cmd_zone.py`):

```text
@zone load thieves_guild --dry
@zone load thieves_guild YES
```

Dry run first to surface errors without DB mutation. Confirm clean dry-run before executing the real load.

Pass criteria: zone imported, all 20 rooms exist in DB, all 9 NPCs spawned at placement rooms, no import errors.

### Phase D — Verify walkability

Programmatic graph traversal from `false_alley` confirming every room reachable, plus NPC presence checks at placement rooms. Use existing smoke-test patterns if one fits; otherwise inline check via the Evennia ORM.

Pass criteria:
- All 20 rooms reachable from `false_alley`
- All 9 NPCs at correct rooms
- All exits resolve to existing rooms
- No orphaned rooms

### Phase E — Validation report

Write `exports/mt600_thieves_guild_validation.md`:
- Total wall-clock and cost across all phases
- Per-phase status, duration, cost, room count
- Any item typeclass substitutions made
- Sample of generated descriptions: one room per wing (5 total)
- Sample of generated stateful_descs: one room, full variant map
- Walkability check result
- Teleport command for Gary (e.g., `@tel #<dbref>` to `false_alley`)

## Acceptance criteria

1. `worlddata/zones/thieves_guild.yaml` exists with all 20 rooms, descs and stateful_descs populated.
2. Total cost under $5.00.
3. Total wall-clock under 60 minutes.
4. `@zone load thieves_guild YES` succeeds without errors.
5. All 20 rooms reachable from `false_alley`; all 9 NPCs spawned.
6. Validation report exists with teleport command.
7. Mocked regression suite green: `pytest tests/test_zone_orchestrator.py tests/test_room_description_prompt.py tests/test_zone_orchestration_schema.py tests/test_builder_zone_list.py tests/test_import_zone_service.py`.
8. No file under `world/builder/`, `world/worlddata/services/`, `commands/`, or `tests/` was modified.

## Out of scope (queued as followups)

- Stolen-goods economy
- Donation shelf rank-gated mechanics
- Guild rank progression
- Quest hook implementations beyond ID strings
- Tonal tuning if Phase 3 prose is on-tone but slightly off
- MT-600d validation doc promotion
- Demo zone composition (8 single-room interiors per Path C)
