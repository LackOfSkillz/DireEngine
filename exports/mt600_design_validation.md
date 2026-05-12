# MT-600-design validation

Status: SHIPPED (design only)

Deliverable: `docs/design/ai_zone_generation.md`

## Scope followed

- Read-only audit only.
- No code changes.
- No YAML/content/data edits.
- No redesign of working builder/runtime systems.
- No game-design or content-design decisions locked on Gary's behalf.

## Audit coverage completed

- Topology and canonical zone-artifact path reviewed.
- Room-description AI path reviewed.
- Controlled-vocabulary and typed-generation input surfaces reviewed.
- State-markup runtime and applicable-state derivation reviewed.
- ZoneScore critic path reviewed.
- Runtime zone import and placement/spawn path reviewed.
- Canonical example zone `new_landing` sampled for live schema population patterns.

## Core findings

1. The repo already has the foundational pieces for AI-assisted zone generation.
2. The missing layer is a top-level orchestrator, not a missing schema or missing runtime loader.
3. Room-description AI is real and usable, but it is room-scoped rather than zone-scoped.
4. ZoneScore is a viable critic, but it is not yet wired into a repair loop.
5. The canonical zone schema supports many more surfaces than the current AI pipeline populates.
6. `new_landing` shows that descriptions, terrain, exits, and placements can be populated while `generation_context`, `stateful_descs`, room tags, ambient, and quest hooks remain sparse.

## Implications for implementation

- MT-600a can stay tightly scoped if it focuses on orchestration skeleton plus score wiring.
- The highest-leverage early path is to batch and repair the already-existing room-description generator before expanding to NPC/item or quest surfaces.
- A later implementation slice will need a locked answer on which generation client/path is authoritative.
- Surface expansion beyond prose should be staged, not attempted all at once.

## Open questions handed forward

- Authoritative generation path.
- V1 surface coverage.
- Score thresholds for retry/review.
- Retry granularity.
- Failure fallback policy.
- Checkpointing versus atomic final write.
- Acceptable determinism level.
- Whether multi-room coherence is required in v1.

## Result

MT-600-design is complete and implementation-actionable.
The next concrete step is drafting MT-600a around the thin orchestrator, using the existing room-generation and ZoneScore surfaces rather than building a new pipeline.