# AI Zone Generation Design

**Date:** 2026-05-02
**Author:** MT-600-design
**Status:** Design complete; awaiting locked decisions for MT-600a

## Executive Summary

DireEngine already has most of the primitives needed for AI-assisted zone authoring, but they are not yet composed into an end-to-end zone generator. The current pipeline can import and preserve topology, validate and load zone YAML, generate room prose one room at a time, render state markup at runtime, score a zone artifact for completeness/depth/engagement, and import room/item/NPC content into live runtime state.

The missing layer is orchestration. The repo does not currently contain a top-level zone generation coordinator that takes a zone skeleton, applies generation across multiple content surfaces, runs a critic pass, and retries only the surfaces that fail quality checks. The room-description pipeline is the strongest existing AI surface, but it is currently scoped to one room at a time and does not own NPCs, item placement, quest hooks, ambient content, or zone-wide iteration.

The recommended architecture is a thin planner-orchestrator that composes existing systems rather than replacing them. It should treat zone YAML as the canonical working artifact, dispatch surface-specific generators in a bounded order, preserve deterministic vocab- and schema-driven inputs, and use ZoneScore as the critic. This is materially smaller than building a new authoring stack, but it is larger than a single-room AI prompt extension.

## Current Pipeline Audit

### 1. Topology and zone artifact generation

What exists:

- `world.builder.services.map_importer.import_map(...)` imports map payloads into Evennia rooms/exits.
- `world.builder.services.map_exporter.export_map(...)` exports live builder-tagged rooms into a structured map/zone-like payload.
- `world.worlddata.services.import_zone_service` loads canonical zone YAML from `worlddata/zones/*.yaml`, normalizes rooms, exits, placements, tags, ambient data, stateful descriptions, and pushes that into runtime rooms and content.

What it does well:

- Produces and preserves room/exit topology.
- Keeps `worlddata/zones/*.yaml` as the canonical authoring artifact.
- Supports richer room fields than bare topology: `desc`, `stateful_descs`, `details`, `ambient`, `terrain`, `tags`, `quest_hooks`, `npcs`, `items`, and `placements`.

What it does not do:

- It does not generate content beyond topology.
- It does not decide which content surfaces should be filled next.
- It does not run any AI loop or quality loop.

Inputs:

- Map-like room/exit payloads for import.
- Canonical zone YAML for runtime import.

Outputs:

- Built rooms/exits in Evennia.
- Canonical zone payloads on disk and normalized live runtime state.

### 2. Room description generation

What exists:

- `world.builder.prompting.room_description_prompt` assembles the prompt for room generation.
- `world.builder.prompting.room_description_generation.generate_room_description(...)` drives an async local-LLM room generation flow.
- `web.api.llm_api` exposes per-room generation and prompt-debug HTTP endpoints.
- `world.builder.services.anthropic_client.RoomDescriptionGenerator` exposes a two-pass generator used by DireBuilder: pass 1 plain prose, pass 2 state-markup augmentation.
- `web.views.direbuilder_generate_description(...)` exposes the two-pass builder generation flow for one room at a time.

What it does well:

- Uses room fields plus zone generation context as inputs.
- Preserves controlled constraints through prompt assembly: room tags, typed generation input, allowed exits, banned phrases, and applicable state groups.
- Already understands state groups/states and can generate markup-friendly output in the builder flow.

What it does not do:

- It is room-scoped, not zone-scoped.
- It does not coordinate multiple rooms for narrative consistency.
- It does not write or validate an entire zone in one pass.
- The repo currently exposes multiple generation clients/surfaces, but no single authoritative zone-generation pipeline.

Inputs:

- Room payload.
- Zone payload and `generation_context`.
- Room tags and typed generation input.
- Allowed exits and interactive-object lists.

Outputs:

- Pass-1 room prose.
- Pass-2 markup-bearing room prose in the DireBuilder path.
- Provenance/telemetry for per-room generation.

### 3. Controlled vocabulary and generation constraints

What exists:

- `world.builder.schemas.generation_context_schema` normalizes zone-level controlled fields.
- `world.builder.schemas.room_tag_schema` normalizes room identity and atmosphere tags.
- `world.builder.schemas.typed_generation_input_schema` resolves typed generation constraints from room/zone/area payloads.
- `world.builder.vocab.zone_vocab.yaml`, `room_vocab.yaml`, `atmosphere_vocab.yaml`, and `terrain_vocab.yaml` define the controlled vocabularies.

What it does well:

- Separates deterministic vocabulary from generative prose.
- Gives the future orchestrator safe structured inputs rather than requiring raw prompt invention.
- Provides a clear boundary between generated prose and schema-governed metadata.

What it does not do:

- It does not decide values on its own.
- It does not currently populate the empty fields in a canonical zone without human or higher-level orchestration.

### 4. State markup and environmental runtime variation

What exists:

- `engine.render.state_markup` parses and renders `$state(...)` fragments.
- `determine_applicable_state_groups(...)` and `determine_applicable_states(...)` in the room-description prompt module derive which state groups apply to a room.
- Weather, invasion, season, and time are already queryable runtime surfaces.
- `world.content.climate_weather_compatibility.yaml` constrains valid weather by climate.

What it does well:

- The runtime render path exists.
- The prompt layer already knows how to describe which state groups apply.
- The builder already has a second-pass mechanism capable of producing state-aware text.

What it does not do:

- There is no zone-level batch orchestration that ensures all rooms get appropriate stateful content.
- The canonical example zone does not yet show broad usage of `stateful_descs`.

### 5. ZoneScore V1 critic

What exists:

- `world.builder.scoring.zone_scorer.score_zone(...)` computes completeness, depth, and engagement from zone YAML.
- `web.views.direbuilder_zone_score(...)` exposes live score evaluation.

What it does well:

- Operates on the canonical zone artifact.
- Already grades key authoring surfaces including zone fields, room descriptions, terrain, identity tags, stateful description presence, ambient messages, items/NPC presence, and quest hooks.
- Returns room-by-room gaps, not just a top-level score.

What it does not do:

- It is a critic only.
- It does not trigger retries or repair loops.
- It does not produce a generation plan.

### 6. Runtime content import and spawn

What exists:

- `world.worlddata.services.import_zone_service` applies room content and placements into runtime rooms.
- `server.systems.zone_runtime_spawn` expands NPC/item room assignments and placements into runtime objects.
- `world.builder.services.template_service` and `template_schema_v1` provide item/NPC template registries.

What it does well:

- Supports NPCs, items, ambient data, room details, stateful descs, terrain, and tags.
- Supports both direct room assignment and `placements` sections.
- Keeps runtime spawn decoupled from authoring-time YAML.

What it does not do:

- It does not author new NPCs/items.
- It does not decide which templates belong where.
- It does not synthesize quest or service content.

## Content Composition Surfaces

The canonical authoring target already supports the following surfaces for a fully alive zone:

| Surface | Present in schema/runtime | Observed status in `new_landing` | Current producer type |
| --- | --- | --- | --- |
| Zone id / name | Yes | Present | Template/manual |
| Zone generation context | Yes | Present but mostly empty/null | Controlled-vocab manual |
| Room ids / names | Yes | Present | Imported/generated topology |
| Room topology / exits | Yes | Present | Imported/generated topology |
| Exit metadata (`typeclass`, travel fields) | Yes | Present | Template/imported |
| Base room descriptions | Yes | Present broadly | AI-assisted or hand-authored |
| `stateful_descs` | Yes | Structurally present, commonly empty in `new_landing` | AI-capable but not zone-orchestrated |
| `details` | Yes | Structurally present, commonly empty | Hand-authored or future AI |
| Ambient messages | Yes | Structurally present, commonly empty | Hand-authored or future AI |
| Environment | Yes | Present | Template/manual |
| Terrain primary/secondary | Yes | Present | Controlled-vocab manual/backfilled |
| Room identity tags | Yes | Structurally present, commonly null/empty in `new_landing` | Controlled-vocab manual or future AI |
| Room states | Yes | Structurally present, commonly empty | Derived/manual/future AI |
| Quest hooks | Yes | Structurally present, commonly empty | Hand-authored |
| NPC placements | Yes | Present in `placements.npcs` | Manual/template-driven |
| Item placements | Yes | Present in `placements.items` | Manual/template-driven |
| Room-level NPC/item references | Yes | Supported by importer/runtime | Manual/template-driven |
| Interactive object constraints | Yes, via typed generation input | Available as prompt input | Manual/schema-driven |
| Climate/weather compatibility | Yes | Available via content YAML + runtime | Auto-derived from existing systems |
| Services/vendors/trainers | Indirectly via NPCs/templates | Possible, not centrally orchestrated | Manual/template-driven |
| Lore hooks/signage/books | Partially via details/items/NPCs | Possible, not centrally orchestrated | Manual |
| Encounter/hunting content | Outside the room-description path | Not covered by current builder AI | Manual/system-specific |

## Surface Classification

| Surface | Classification | Notes |
| --- | --- | --- |
| Room topology | Auto-derived | Produced from map import/export and zone YAML topology |
| Room/zone ids | Auto-derived | Builder/runtime identifiers |
| Room names | Template-driven / imported | Present in canonical zones; can be generated upstream of prose |
| Base room descriptions | AI-generated | Existing per-room AI pipeline |
| Stateful markup descriptions | AI-generated but not yet zone-orchestrated | Supported by prompt/client path, not by whole-zone workflow |
| Zone generation context | Vocab-picker + hand-authored | Controlled schema with explicit vocab |
| Room tags | Vocab-picker + hand-authored | Controlled room/atmosphere vocab |
| Terrain | Vocab-picker + manual/backfill | Controlled terrain vocabulary |
| Exit references | Auto-derived | From topology |
| Exit mention constraints | Auto-derived | Typed generation input uses known exits |
| Ambient messages | Hand-authored today | Schema exists, but no evidence of broad generation |
| Quest hooks | Hand-authored | Scorer reads them; no generation path found |
| NPC placements | Template-driven + hand-authored | Runtime spawn exists; authoring still manual |
| Item placements | Template-driven + hand-authored | Runtime spawn exists; authoring still manual |
| Climate/weather runtime effects | Auto-derived | Driven by existing weather/invasion/calendar systems |
| Forage behavior by terrain | Auto-derived | Driven from terrain plus forage catalog |
| Lore/service content | Hand-authored | No general AI authoring surface found |

## Gap Analysis

The current gap is real but bounded. The repo already has good local components, but it does not yet have an end-to-end zone authoring loop.

### Gap 1. No top-level zone coordinator

Current state:

- Generation is invoked per room.
- Scoring is invoked per zone.
- Runtime import is invoked on final zone YAML.

Missing:

- A controller that sequences zone skeleton -> per-surface generation -> scoring -> retry -> final write/import.

### Gap 2. Room generation is local, not relational

Current state:

- Prompt assembly uses room-local context plus zone-level soft context.
- Allowed exits and room tags constrain hallucination.

Missing:

- Zone-wide narrative coherence.
- Neighborhood-level consistency checks.
- Shared landmark, district, service, and faction continuity across adjacent rooms.

### Gap 3. Critic exists, but closed-loop repair does not

Current state:

- ZoneScore can identify weak rooms and missing surfaces.

Missing:

- A repair loop that uses those findings to regenerate only failing rooms or surfaces.
- Surface-specific retry policies.

### Gap 4. Non-prose surfaces are not under a general AI authoring path

Current state:

- NPC/item runtime systems and templates exist.
- Zone YAML supports ambient, details, stateful descs, quest hooks, tags, and placements.

Missing:

- A generation path for NPC roster placement, item placement, ambient content, details, and quest-hook scaffolding.
- A policy for which of those surfaces remain manual in v1.

### Gap 5. Canonical zone examples are structurally rich but semantically sparse in several fields

Observed in `new_landing`:

- Room descriptions and terrain are broadly populated.
- `stateful_descs`, `ambient.messages`, `quest_hooks`, and many room-tag fields are commonly empty.
- `generation_context` exists but is empty/null in the file header.

Implication:

- The authoring schema is ahead of the population pipeline.
- The orchestration layer should treat these as fillable surfaces rather than inventing a new schema.

### Gap 6. Existing AI entrypoints are split by client/surface

Current state:

- One path uses the local LLM client and per-room generation API.
- Another path uses the DireBuilder two-pass generator and returns pass-1/pass-2 outputs.

Missing:

- A single authoritative orchestration entrypoint for zone generation.
- A locked decision on which existing generation surface the orchestrator should treat as canonical.

## Orchestration Design

### Proposed default

Use a thin planner-orchestrator, not a pure one-pass linear pipeline.

This is closer to Option B than Option A, but intentionally lightweight. The orchestrator should own task ordering, shared context assembly, bounded retries, and score-driven repair, while delegating actual generation work to existing surface generators.

Why this is the default:

- A purely linear pipeline is too rigid once some surfaces are optional or conditional by zone type.
- A full autonomous planner would overshoot the reframe and recreate systems that already exist.
- A thin orchestrator can preserve deterministic schema-driven surfaces while still deciding which generators to call and when.

### Architecture shape

Recommended artifact flow:

1. Load or create the initial zone skeleton from existing map/topology tooling.
2. Normalize the working zone artifact to canonical YAML shape.
3. Build a generation plan by surface, using zone type and current missing fields.
4. Run surface generators in bounded order.
5. Re-score the resulting zone with ZoneScore.
6. Retry only failing surfaces/rooms within bounded iteration limits.
7. Emit final zone YAML for review/import.

The orchestrator should not directly own prose rules, vocab rules, or runtime import logic.

### Planner shape

The planner can be small and mostly deterministic.

Inputs:

- Zone skeleton / current zone YAML.
- ZoneScore criteria and current score payload.
- Controlled vocab and typed-generation schemas.
- Runtime-capability metadata: which surfaces the current zone already supports.

Outputs:

- Ordered task list, for example:
  - populate generation context
  - generate room descriptions
  - generate stateful descriptions for weather/time-capable rooms
  - populate identity tags where empty
  - populate ambient/detail surfaces if in-scope
  - run critic
  - re-run failed rooms/surfaces

Behavior:

- Prefer deterministic branching over freeform planning where possible.
- Use LLM planning only when the surface order or repair strategy cannot be encoded cheaply.
- Avoid re-planning the whole zone when only a few rooms fail the critic.

### Critic shape

ZoneScore should be the primary critic for v1.

Critic inputs:

- Entire working zone YAML.

Critic outputs:

- Composite and sub-scores.
- Rooms needing attention.
- Room-level biggest-gap signals.

Repair policy:

- Map score gaps to generators by surface.
- Example: `no description` -> rerun room-description generator.
- Example: `no atmosphere` or missing stateful coverage -> rerun state/atmosphere generator if that surface is in scope.
- Example: `untagged` -> assign to structured tag-generation/manual-review queue depending on locked decisions.

### Integration with existing systems

The orchestrator should compose the existing repo surfaces in this order:

- Topology source: `map_importer` / existing zone YAML.
- Working artifact: in-memory zone dict matching `worlddata/zones/*.yaml`.
- Surface generators: existing room-description generation path plus future adjacent generators.
- Deterministic inputs: zone/room/terrain vocab, typed generation input, climate/weather compatibility, template registries.
- Critic: `score_zone(...)`.
- Finalization: write canonical zone YAML, then optionally hand off to runtime import.

### Cost and iteration model

The current repo already tracks prompt size, prompt hashes, latency, tokens, and approximate cost in the room-generation surfaces. The orchestrator should reuse those telemetry surfaces rather than creating parallel accounting.

Recommended bounds for v1 design:

- Bounded retries per room/surface, not open-ended loops.
- Zone-level hard stop after a small number of critic cycles.
- Escalate unresolved failures to a review queue rather than continuing silently.

Exact thresholds should remain a locked implementation decision.

## Open Questions For Locked Decisions

1. Which existing generation path is authoritative for MT-600a: the local-LLM per-room path, the DireBuilder two-pass path, or a unified wrapper over both?
2. Which surfaces are in scope for AI generation in v1 beyond base room descriptions: stateful descs, tags, ambient, details, NPC placements, item placements, quest hooks?
3. Should the orchestrator fill `generation_context` itself from controlled vocab, or should that remain a human-authored seed input?
4. What ZoneScore threshold counts as "good enough for review" versus "must retry"?
5. Should retry operate only at room granularity, or also at finer surface granularity within a room?
6. When a surface cannot be satisfied, should the orchestrator leave it empty, fall back to templates, or hard-stop the zone run?
7. Are NPC and item placements in-scope for AI proposal in v1, or should v1 stop at descriptive/textual zone completion?
8. Should the orchestrator write the zone YAML only once at the end, or persist checkpoint snapshots between phases?
9. How much non-determinism is acceptable across repeated runs on the same input skeleton?
10. Is multi-room narrative coherence a v1 requirement, or a later phase after single-room quality is stable?

## Implementation Dispatch Sequence

### MT-600a: Zone orchestration skeleton

- Introduce the top-level orchestration entrypoint.
- Load a working zone artifact.
- Build a deterministic task plan from missing surfaces.
- Wire score evaluation and dry-run task reporting.
- No new generation surfaces yet beyond composition.

### MT-600b: Existing room-description AI integration

- Batch room-description generation across a zone.
- Reuse the existing prompt/generation surfaces.
- Persist generated descriptions into the working zone artifact.
- Validate on a bounded zone slice first, then on a real small zone.

### MT-600c: Score-driven repair loop

- Run ZoneScore after generation.
- Retry only rooms/surfaces that fail configured thresholds.
- Emit a clear review summary for unresolved failures.

### MT-600d: Stateful description generation

- Promote existing state-group/state logic from per-room capability to zone-wide orchestration.
- Populate `stateful_descs` for rooms whose applicable state groups demand them.

### MT-600e: Structured non-prose surfaces

- Decide and implement the first structured adjunct surfaces from Phase F decisions.
- Candidates: tags, ambient, details, NPC/item placement suggestions.

### MT-600f: End-to-end zone generation validation

- Generate a complete small zone from skeleton to final YAML.
- Run critic, repair loop, and runtime import validation.
- Confirm the artifact loads and plays without manual patching beyond review.

## Scope Notes

- This design does not recommend rebuilding ZoneForge, ZoneScore, runtime import, or the room prompt stack.
- This design does not lock content policy or worldbuilding choices on Gary's behalf.
- This design does not assume every surface should be AI-generated in v1.
- The current gap is orchestration, not absence of foundational infrastructure.

## Appendix: Code References

- `world/builder/services/map_importer.py`
- `world/builder/services/map_exporter.py`
- `world/worlddata/services/import_zone_service.py`
- `world/builder/prompting/room_description_prompt.py`
- `world/builder/prompting/room_description_generation.py`
- `world/builder/services/anthropic_client.py`
- `world/builder/services/llm_client.py`
- `world/builder/scoring/zone_scorer.py`
- `world/builder/schemas/generation_context_schema.py`
- `world/builder/schemas/room_tag_schema.py`
- `world/builder/schemas/typed_generation_input_schema.py`
- `world/builder/services/template_service.py`
- `server/systems/zone_runtime_spawn.py`
- `engine/render/state_markup.py`
- `world/content/climate_weather_compatibility.yaml`
- `world/builder/vocab/zone_vocab.yaml`
- `world/builder/vocab/room_vocab.yaml`
- `world/builder/vocab/atmosphere_vocab.yaml`
- `world/builder/vocab/terrain_vocab.yaml`
- `worlddata/zones/new_landing.yaml`
- `web/api/llm_api.py`
- `web/views.py`