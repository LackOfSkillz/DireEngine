# MT-600-design — AI zone generation: gap analysis and orchestration design

## Background

DireEngine already has substantial zone-authoring infrastructure
that the AI generation pipeline will compose, not replace:

- **ZoneForge:** generates zone scaffolding from DragonRealms
  maps; produces room/exit topology
- **AI-assisted room descriptions:** existing pipeline that
  generates room descriptions given context
- **ZoneScore V1:** defines what makes a good zone (coverage,
  quality, completeness criteria)
- **Terrain system:** `terrain.primary` / `terrain.secondary`
  taxonomy with content hooks (foraging, weather, runtime state)
- **State markup parser:** `$state(...)` at render time per
  MT-514d-impl
- **Forage catalog:** terrain-keyed content at
  `world/builder/content/forage_catalog.yaml`
- **Vocab pickers:** controlled vocabulary for content domains
- **Climate / weather content:** YAML-driven atmospheric and
  weather content per zone
- **Zone YAML format:** the canonical authoring target
  (`worlddata/zones/*.yaml`)

The roadmap target — "AI generates a complete, runnable zone
end-to-end with no human intervention beyond review" — is
estimated at ~70-80% complete given how much of the pipeline
already exists.

This dispatch produces the design document for closing the
remaining 20-30%. The output is `docs/design/ai_zone_generation.md`
specifying:

1. What exists and works (audit of current pipeline)
2. What's missing for end-to-end automation
3. Architecture proposal for the orchestration layer
4. Open questions requiring locked decisions before implementation
5. Implementation dispatch sequence (MT-600a, b, c, ...)

No code in this dispatch. Pure design.

## Architectural guardrails (READ FIRST)

This is a design dispatch, not implementation. The output is a
markdown document plus a list of open questions for Gary to lock
before MT-600a drafts.

The biggest risk is over-engineering. The reframe is "wire the
AI to use existing tools well," not "design a new AI pipeline."
The design should lean heavily on what already works and call
out only the actual gaps.

The second-biggest risk is design opinions slipping in as
locked decisions. The dispatch enumerates open questions for
Gary; it does not make game-design or content-design choices
on his behalf.

**Frozen scope:**

1. Phase A: Audit current pipeline. Read ZoneForge code, the
   existing AI room description pipeline, ZoneScore V1, the
   zone YAML format, terrain system, vocab pickers, content
   YAMLs. Document what each does, what its output looks like,
   what its boundaries are.
2. Phase B: Audit content composition surfaces. For a working
   zone (e.g., new_landing), list every content surface that
   needs to be populated to make the zone fully alive: room
   descriptions, terrain tags, exit names, NPC roster, item
   catalogs, weather/climate config, state markup, runtime
   state hookups.
3. Phase C: Identify what's currently AI-generated, what's
   manually authored, what's drawn from vocab pickers, what's
   templated. Each surface from Phase B classified.
4. Phase D: Identify the actual gap. What needs to happen for
   AI to take a zone from "ZoneForge skeleton" to "fully alive,
   runnable zone with all content surfaces populated"?
5. Phase E: Design the orchestration layer. How does the AI
   sequence work across surfaces? What's the planner shape?
   What's the critic shape? What's the integration with
   ZoneScore? Specifically — and this is the load-bearing
   design choice — does AI orchestration need a new top-level
   coordinator, or can it extend the existing room-description
   AI pipeline?
6. Phase F: Surface open questions. What design decisions need
   Gary's input before MT-600a can ship?
7. Phase G: Propose implementation dispatch sequence. Concrete
   list of MT-600a, b, c, ... with what each ships and what
   ordering dependency exists.
8. Phase H: Produce design document at
   `docs/design/ai_zone_generation.md`.
9. Phase I: Validation tracker at
   `exports/mt600_design_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT modify any code. Read-only audit + design.
- DO NOT modify any YAML, content, or data files.
- DO NOT propose specific implementation in the design doc.
  Implementation is for MT-600a's dispatch.
- DO NOT redesign existing systems (ZoneForge, room description
  AI, ZoneScore, vocab pickers). The reframe is "compose them
  better," not "rebuild them."
- DO NOT make game-design choices for Gary (which content
  domains AI should cover, what quality bar to enforce, what
  iteration limits to set, etc.). Surface as open questions.
- DO NOT speculate on cost or model selection beyond what's
  already used by the existing AI pipeline. If a new model
  tier is needed for the orchestrator vs the generators, flag
  as open question.
- DO NOT recommend Anthropic-specific or any vendor-specific
  choices. Existing AI pipeline implies a current choice;
  use it as default.
- DO NOT exceed ~2 hours of agent work. If the surface is
  bigger than expected, stop and report.

**Stop-and-report conditions:**

- If the existing AI room description pipeline doesn't exist
  in the repo as expected, stop and report. The audit
  assumption may be wrong.
- If ZoneForge's output shape doesn't match what the design
  expects, stop and report.
- If ZoneScore V1's criteria aren't actually defined anywhere
  yet (only conceptually agreed upon), stop and report.
- If audit reveals the gap is much larger than 20-30% (e.g.,
  the existing pipeline is more brittle than thought), stop
  and report. Reframe needed.
- If audit reveals the gap is smaller than 20-30% (e.g.,
  existing pipeline is closer to end-to-end than thought),
  stop and report. Implementation may be one tight dispatch.

## Phase A — Current pipeline audit

The agent reads:

- `world/builder/zoneforge.py` (or wherever ZoneForge lives)
- The AI room description module (path TBD; agent finds it)
- `world/builder/zone_score.py` (or wherever ZoneScore lives)
- `worlddata/zones/new_landing.yaml` as the canonical example
  zone (211 rooms, terrain backfilled)
- `world/builder/content/*.yaml` for content shape
- The zone-loading path that turns YAML into runtime objects

For each component:
- Purpose
- Input shape
- Output shape
- Quality boundary (what it produces well, what it doesn't)
- Coupling to other components

## Phase B — Content composition surfaces

For a fully alive zone, list every content surface:

- Room metadata: key, name, district/zone identity
- Room descriptions (default state)
- State-keyed description variants (`desc_storm`, `desc_calm`, etc.)
- `$state(...)` markup for atmospheric prose mixing
- Terrain primary + secondary tags
- Exit names and bidirectional consistency
- Exit descriptions (when relevant)
- NPC roster (which NPCs spawn here, with what hooks)
- Item catalogs (what loot, what containers, what stackables)
- Weather/climate config for the zone
- Atmospheric content (ambient messages, sounds)
- Forage hooks (terrain → catalog mapping; usually automatic
  but some zones override)
- Hunting/encounter tables if applicable
- Lore hooks (signage, books, scholars to consult)
- Service hookups (banks, vendors, healers, trainers)
- Quest hooks (initial quest givers, quest content)

The agent uses new_landing as the reference for what's populated
and how.

## Phase C — Surface classification

For each surface in Phase B, classify:

- **AI-generated:** the existing pipeline produces this
- **Vocab-picker:** drawn from controlled vocabulary
- **Template-driven:** standard pattern with parameters
- **Hand-authored:** writer-required
- **Auto-derived:** computed from other fields (e.g., terrain
  → forage catalog mapping)
- **Empty / not applicable:** not all zones need all surfaces

Document in a table.

## Phase D — Gap analysis

Given the classification, what's currently impossible to AI-author
end-to-end?

Likely candidates (agent confirms or refutes):
- Multi-room narrative coherence (room A's description
  references something in room B)
- NPC roster + dialog orchestration
- State markup variants for weather/invasion
- Quest scaffolding
- Lore content that needs world-grounding

For each gap, document:
- What's currently required from a human author
- What an AI-generated alternative would need to consume
- Whether existing pipeline components could be extended or
  composed to fill the gap

## Phase E — Orchestration layer design

This is the load-bearing design phase. Given the audit and
gaps, propose:

### E.1 Architecture shape

Two candidate shapes:

**Option A — Linear pipeline:** ZoneForge → room descriptions
→ NPC roster → loot tables → state markup → ZoneScore review
→ retry-failed-surfaces. One-pass through surfaces with
critic at the end.

**Option B — Planner-orchestrator:** A top-level planner
decides which surfaces to populate in what order, dispatches
to surface-specific generators (existing room AI, new NPC AI,
new state AI), and re-plans based on critic output.

Agent picks proposed default; documents tradeoffs.

### E.2 Planner shape

If a planner is needed:
- What input does it consume? (zone skeleton, ZoneScore criteria,
  content directory, runtime state model docs)
- What output does it produce? (sequence of generation tasks)
- What model handles planning? (likely the same as the
  generators, or a tier higher)
- How does it handle failures? (re-plan, escalate, abort)

### E.3 Critic shape

ZoneScore V1 already defines what good looks like. The critic:
- Consumes the generated zone YAML
- Evaluates against ZoneScore criteria
- Returns pass/fail with specific surface-level feedback
- Triggers re-generation of failing surfaces

### E.4 Integration with existing systems

How does the orchestrator talk to:
- ZoneForge (gets initial scaffolding)
- Room description AI (extends to per-room generation in
  context of full zone)
- Vocab pickers (preserves as deterministic picks)
- Content YAMLs (catalog data, climate, weather — read-only
  inputs to generation)
- Zone YAML output (writes the canonical authoring artifact)

### E.5 Cost / iteration model

- Estimated tokens per zone (very rough)
- Iteration bounds (max retries, max planner cycles)
- Escalation path when bounds exceeded (fall back to scaffolding
  + flag for human author)

## Phase F — Open questions

Surface design decisions Gary needs to lock before MT-600a:

- Quality bar: ZoneScore threshold for "shippable" vs "needs
  human review"
- Content coverage: which surfaces does AI generate v1, which
  remain manual
- Cost ceiling: how much is acceptable per zone generation
- Iteration policy: silent retries vs surfaced retries
- Vendor constraints: same model as room AI vs newer/larger
  for orchestration
- Testing model: dry-run mode that skips API calls and uses
  fixtures, vs real generations against scratch zones
- Failure recovery: when AI can't satisfy a surface, what
  happens — fall back to template, flag for human, abort
  zone, etc.
- Output shape: single zone YAML produced atomically vs
  iterative writes that can be inspected mid-flight
- Determinism: should a re-run with same inputs produce
  identical output, or is non-determinism acceptable

The agent enumerates; does not answer.

## Phase G — Implementation dispatch sequence

Propose the MT-600 series shape:

- **MT-600a:** Skeleton orchestrator + integration with
  ZoneForge. Reads ZoneForge output; produces sequence of
  generation tasks; doesn't yet generate anything (mocks the
  AI calls). Validates the wiring.

- **MT-600b:** Hook the existing room description AI as the
  first concrete generator. Generates descriptions for all
  rooms in a zone, in context of the full zone topology.
  Validates against new_landing as the test case.

- **MT-600c:** Add critic. Wire ZoneScore V1 to evaluate
  generated room descriptions and trigger re-generation of
  failing rooms.

- **MT-600d:** State markup variant generation. AI generates
  `desc_storm`, `desc_calm`, etc. for rooms. Validates the
  `$state(...)` pipeline shipped in MT-514d-impl.

- **MT-600e:** Additional content surfaces (NPC roster, loot,
  ambient). Triaged by Phase D's gap analysis.

- **MT-600f:** End-to-end test on a fresh small zone. Generate
  a complete zone from a DragonRealms map; verify it loads,
  plays, and passes ZoneScore.

The agent's proposed sequence is a starting point; Gary may
re-order or split based on Phase F's open question answers.

## Phase H — Produce design document

`docs/design/ai_zone_generation.md` with the structure:

```markdown
# AI Zone Generation Design

**Date:** <date>
**Author:** MT-600-design
**Status:** Design complete; awaiting locked decisions for MT-600a

## Executive summary
[3-5 sentences: pipeline status, gap, proposed orchestration
approach, dispatch sequence]

## Current pipeline audit (Phase A)
[Component inventory with purpose, IO shapes, quality boundaries]

## Content composition surfaces (Phase B)
[Per-surface table for a fully-alive zone]

## Surface classification (Phase C)
[How each surface is currently produced]

## Gap analysis (Phase D)
[What's currently impossible to AI-author end-to-end]

## Orchestration design (Phase E)
[Architecture, planner, critic, integration, cost]

## Open questions for locked decisions (Phase F)
[Design decisions awaiting Gary's input]

## Implementation dispatch sequence (Phase G)
[MT-600a through n with summaries and dependencies]

## Appendix: code references
[File paths, line ranges for the audit work]
```

## Phase I — Validation tracker

`exports/mt600_design_validation.md`:

```markdown
# MT-600-design validation

Status: SHIPPED (design only)

Deliverable: `docs/design/ai_zone_generation.md`

## Phases A through G complete.

## Implications for implementation
[Brief: how big is MT-600a, what unknowns remain, what Gary
needs to decide before implementation drafts]
```

## Verification checklist

1. Phase A audits all current components factually
2. Phase B enumerates all content surfaces
3. Phase C classifies each surface
4. Phase D names actual gaps
5. Phase E proposes architecture with tradeoffs
6. Phase F surfaces open questions
7. Phase G proposes dispatch sequence
8. Phase H design doc complete
9. Phase I validation in place
10. No code modified
11. No game-design or content-design choices made for Gary
12. Doc is implementation-actionable once Phase F is answered

## Stop conditions

- Edit only `docs/design/ai_zone_generation.md` (new) and
  `exports/mt600_design_validation.md` (new)
- Stop on missing-component surprises
- Stop on gap-size surprises (much smaller or much bigger
  than reframe expects)
- Stop on ~2 hour agent-time bound
- Do not implement anything
- Do not propose game-design or content-design choices

## Required artifacts

1. `docs/design/ai_zone_generation.md` (new)
2. `exports/mt600_design_validation.md` (new)

## Followup queue

- **MT-600a:** First implementation dispatch. Drafted from
  Phase E architecture and Phase G sequence after Gary locks
  Phase F open questions.

- **MT-600b through n:** Per Phase G proposed sequence.

- **Manual zone build:** Now genuinely deferred. The reframe
  ("AI builds e2e proves humans can too") changes this from
  "do first" to "AI generation is the primary verification
  path; human authoring remains as fallback."

- **Open source release:** AI zone generation working e2e is
  a reasonable launch criterion; this dispatch helps clarify
  whether that bar is realistic for the launch timeline.
```