Locked. All decisions in place. Drafting MT-513 now.

A heads-up on size: this dispatch is the largest of the arc. Zone Score is a substantial new feature with a backend scorer, a view endpoint, header strip UI replacement, expandable panel, per-room sub-scorecards, the schema prewire for quest hooks, and an updated header tagline. The leash from MT-512 stays on — frozen layout decisions, frozen interaction model, explicit no-redesign clauses, stop-and-report conditions.

```markdown
# MT-513 — Zone Score V1

## Background

DireBuilder is now a complete creative tool. Builders can map zones,
tag rooms with vocab-backed pickers across all schema-constrained
fields, declare terrain that drives resource availability, generate
AI descriptions per room with Sonnet 4.5, and read field-level
tooltips for every input. What's missing is a feedback signal that
tells the builder how the zone is doing — whether it's complete,
whether it has atmospheric depth, whether players will have things
to do when they walk in.

Zone Score is that feedback signal. It runs in the header strip
that currently shows "Coming Soon: DireBuilder Zone Score" and
"We build better builders." It replaces the placeholder with a
composite score, three sub-scores (Completeness, Depth,
Engagement), a qualitative tier label, and an expandable panel
showing per-room breakdown and the bottom rooms that need
attention.

The design principle is coaching, not gatekeeping. Builders can
save and ship at any score. The score guides attention, never
blocks action. The label words describe the zone's state, not the
builder's effort.

This dispatch also adds `room.quest_hooks` as a reserved schema
field (empty array default) so the engagement axis can count quest
density. The quest system itself is not implemented in this
dispatch and is a separate future arc.

## Architectural guardrails (READ FIRST)

This is the largest dispatch of the recent arc. Same leash as
MT-512.

**Frozen design decisions:**

1. Three sub-scores plus one composite. Composite is a weighted
   average: Completeness 40% + Depth 30% + Engagement 30%.
2. Composite displays larger than sub-scores in the header strip.
3. Composite carries a tier label from a fixed seven-tier ladder.
4. Header tagline is replaced with: "DireEngine ZoneScore — We
   build better zones by building better builders."
5. Score recomputes on save. Stale indicator shows when zone is
   dirty.
6. Expanded panel shows by default: the three sub-score
   breakdowns and a "needs attention" list of the bottom 5-10
   rooms by composite room-score. Full per-room breakdown is
   behind a toggle.
7. The scorer lives in a new module: `world/builder/scoring/zone_scorer.py`.
   It takes a normalized zone dict and returns a structured score
   payload. It does NOT touch the database, the AI pipeline, the
   engine, or any saved files.
8. The view endpoint is GET-only, returns JSON, computed from the
   canonical saved zone (not workingZone). It runs on demand from
   the frontend after a successful save.
9. The header strip and expanded panel reuse existing styling
   (parchment theme, accent colors, existing typography). No new
   visual language.
10. `room.quest_hooks` is added to the room schema as an optional
    array of strings, default empty. No UI surface in this
    dispatch — builders can't tag quest hooks yet. The field exists
    only so the scorer can read it. When the quest system lands,
    this becomes the wiring point.

**Frozen what-not-to-do list:**

- DO NOT add a new tab to the room editor.
- DO NOT modify any existing room editor controls or layout.
- DO NOT modify the AI generation pipeline.
- DO NOT modify the engine (forage, gather, NPCs, combat — all
  untouched).
- DO NOT modify the legacy /builder/ route or its assets.
- DO NOT design or implement the quest system. Only the schema
  prewire field.
- DO NOT add UI for quest_hooks tagging. Field is invisible to
  builders for now.
- DO NOT modify the forage catalog, vocab files, or tooltips
  beyond appending one new tooltip entry for the score itself.
- DO NOT real-time-recompute the score on every keystroke. Score
  recomputes on successful save only.
- DO NOT block save or any other action based on score.

**Stop-and-report conditions:**

- The scorer turns out to require modifying the room schema beyond
  the quest_hooks addition
- The view endpoint turns out to require modifying any existing
  endpoint
- The header strip markup turns out to require restructuring the
  page header beyond replacing the placeholder text block
- Any existing test fails after the changes
- The score computation takes longer than 500ms on a 211-room
  zone (this would indicate a quadratic algorithm and is worth
  flagging before shipping)

## In scope

- New scorer module: `world/builder/scoring/zone_scorer.py`
- New view endpoint: `GET /direbuilder/api/zone/<zone_id>/score/`
- Schema addition: `room.quest_hooks` (optional array of strings)
- Header strip replacement in `direbuilder.html` (the existing
  placeholder block)
- Expandable panel UI for the score breakdown
- Per-room scoring sub-routine (each room gets its own composite
  score, surfaced in the "needs attention" list)
- One new tooltip entry for the Zone Score header explaining what
  the score means
- Cache-bust direbuilder.js and direbuilder.css

## Out of scope

- The quest system itself
- Real-time score recomputation on field changes
- Score-based gating of save/discard/hot-load
- Score history tracking or trends over time
- Configurable weights or rubric customization
- Per-builder score leaderboards
- Score export or reporting features
- Modifying any existing scoring or coaching surfaces (there are
  none to modify yet — this is V1)
- Engine integration of quest_hooks

## Phase A — Schema addition for quest hooks

Add `quest_hooks` to the room schema as an optional array of
strings, default empty. Locate the existing room schema in
`world/builder/schemas/` and follow the same pattern used for
other optional array fields (e.g., `tags.custom`).

Validation rules:
- If missing or null, normalize to empty array
- Must be an array of strings if present
- Each string must be non-empty after trimming
- Deduplicate (same pattern as tags.custom)

The view normalizer in `web/views.py` round-trips the field
through save the same way other room fields are handled. No UI
work in this phase — builders can't see or edit the field. The
field exists for the scorer and for future quest system
integration.

## Phase B — Build the scorer module

Create `world/builder/scoring/zone_scorer.py` with this shape:

```python
from typing import TypedDict
import yaml
from pathlib import Path
from functools import lru_cache


class SubScore(TypedDict):
    score: int  # 0-100
    breakdown: dict  # category -> {count, total, ratio} per category


class ZoneScore(TypedDict):
    composite: int  # 0-100
    tier: str  # one of the seven tier labels
    completeness: SubScore
    depth: SubScore
    engagement: SubScore
    rooms_needing_attention: list[dict]  # bottom 5-10 rooms by composite
    room_count: int
    computed_at: str  # ISO timestamp
    zone_id: str


# Seven-tier ladder
TIER_LADDER = [
    (90, "Exceptional"),
    (80, "Polished"),
    (70, "Solid"),
    (60, "Sound"),
    (50, "Rough"),
    (30, "Sketch"),
    (0, "Stub"),
]

WEIGHTS = {
    "completeness": 0.40,
    "depth": 0.30,
    "engagement": 0.30,
}


def score_zone(zone: dict) -> ZoneScore:
    """Compute Zone Score for a normalized zone dict.

    Reads only from the zone dict. Does not touch the database,
    files, network, or any other I/O. Pure function over the input.

    Returns the structured ZoneScore payload.
    """
    ...
```

### Completeness sub-score (40% weight)

For each room in the zone, count satisfied vs. unsatisfied criteria:

Zone-level (counted once per zone, contributes proportionally):
- `setting_type` is set and non-empty
- `era_feel` is set and non-empty
- `climate` is set and non-empty
- `mood` array has at least one entry
- `cultural_palette` array has at least one entry
- `voice_notes` is set and non-empty (small bonus, weight 0.5)

Room-level (counted per room, averaged across all rooms):
- `name` is set and non-empty (mandatory — heavy weight)
- `environment` is set and non-empty (mandatory — heavy weight)
- `terrain.primary` is set (medium weight, drives resource scoring)
- At least one of: `desc` (manual), `generated_desc` is set
- At least one of: `tags.structure`, `tags.specific_function` is set
- All exits point to valid room IDs in the zone (no orphans —
  failed orphan check counts as room-incompleteness)
- All NPCs have `typeclass` declared

Computation: each criterion is binary (met or not met) per room.
Count satisfied criteria across all rooms, plus the zone-level
criteria, divide by total possible criteria, scale to 0-100.

The breakdown dict reports counts:
```python
{
    "zone_fields": {"satisfied": 5, "total": 5},  # zone-level
    "room_names": {"satisfied": 211, "total": 211},
    "room_environments": {"satisfied": 198, "total": 211},
    "room_terrain_primary": {"satisfied": 47, "total": 211},
    "room_descriptions": {"satisfied": 12, "total": 211},
    "room_identity_tags": {"satisfied": 73, "total": 211},
    "exit_validity": {"satisfied": 209, "total": 211},
    "npc_declarations": {"satisfied": 18, "total": 18},
}
```

### Depth sub-score (30% weight)

Per-room metrics, averaged across rooms:

- `atmosphere_axis_coverage`: 0.0-1.0, fraction of the five
  atmosphere axes (materials, social_character, surroundings,
  sensory, upkeep) that have at least one entry
- `tag_density`: count of non-empty tags across structure,
  specific_function, named_feature, condition, custom, plus all
  five atmosphere axes — normalized so a room with 8+ non-empty
  fields scores 1.0, fewer scales linearly down to 0
- `generated_desc_coverage`: 1.0 if generated_desc is set, else 0.0
- `stateful_desc_coverage`: 1.0 if stateful_descs has at least
  one entry, else 0.0

Compute zone-wide averages of each metric, average those four
together (equal weight), scale to 0-100.

Breakdown:
```python
{
    "atmosphere_avg": 0.42,    # average axis coverage
    "tag_density_avg": 0.55,   # average normalized tag density
    "generated_pct": 0.05,     # % rooms with generated descriptions
    "stateful_pct": 0.18,      # % rooms with stateful descriptions
}
```

### Engagement sub-score (30% weight)

Compute "engagement coverage" — fraction of rooms with at least
one engagement element across these categories:

1. NPCs (rooms with non-empty `npcs` array)
2. Items (rooms with non-empty `items` array)
3. Details (rooms with non-empty `details` dict)
4. Ambient messages (rooms with non-empty `ambient.messages`)
5. Stateful descs (rooms with non-empty `stateful_descs`)
6. Shop tag (rooms where `tags.specific_function` includes "shop")
7. Hostile NPCs (rooms with at least one NPC declaring
   `flags: [aggressive]`)
8. Resource availability (rooms with `terrain.primary` set)
9. Healing herb access (rooms whose `terrain.secondary` value
   yields at least one healing herb in the forage catalog)
10. Quest hooks (rooms with non-empty `quest_hooks` array)

For categories 6, 7, 9, 10: the scorer reads the relevant
auxiliary data (vocab values, NPC flags, forage catalog, schema
field) to determine satisfaction. Load the forage catalog the
same way the view loads it; cache the load.

Engagement coverage = (rooms with ≥1 category satisfied) / total_rooms

Apply a size-aware target curve to convert coverage to a score:

```python
def engagement_target(zone_size: int) -> float:
    if zone_size <= 20:
        return 0.30
    if zone_size >= 200:
        return 0.20
    # Linear interpolation between 20 → 0.30 and 200 → 0.20
    return 0.30 - (zone_size - 20) * (0.10 / 180)
```

Score = min(100, (coverage / target) * 100)

Breakdown:
```python
{
    "npcs_pct": 0.08,
    "items_pct": 0.04,
    "details_pct": 0.12,
    "ambient_pct": 0.06,
    "stateful_pct": 0.18,
    "shops_pct": 0.02,
    "hostile_pct": 0.00,
    "resources_pct": 0.22,
    "healing_pct": 0.15,
    "quests_pct": 0.00,
    "any_engagement_pct": 0.31,
    "target": 0.22,
    "coverage_vs_target": 1.41,  # capped at 1.0 for score
}
```

### Composite and tier

Composite = round(0.40 * completeness + 0.30 * depth + 0.30 * engagement)

Tier = first label in TIER_LADDER where composite >= threshold.

### Per-room scoring (for "needs attention" list)

Each room gets its own composite score by computing the same
three sub-scores limited to that room's data:
- Completeness: which room-level criteria are met for this room
- Depth: this room's atmosphere axis coverage, tag density,
  generated/stateful flags
- Engagement: how many engagement categories this room satisfies

Sort rooms by composite ascending. The "needs attention" list is
the bottom 5-10 rooms (use min(10, max(5, room_count // 20))).

For each entry in the list, include:
```python
{
    "room_id": "CRO_450_300",
    "name": "Amberwick Lane, Western Run",
    "composite": 34,
    "tier": "Sketch",
    "biggest_gap": "no environment set",  # 1-2 words describing top issue
}
```

The "biggest_gap" is the single highest-impact missing criterion
for that room, expressed as builder-readable text. Pick from a
fixed list of gap labels (e.g., "no environment", "no description",
"no terrain", "untagged", "no atmosphere", "orphan exits").

### Performance constraint

The scorer must complete in under 500ms for a 211-room zone on
modest hardware. Use list comprehensions and dict access; avoid
quadratic loops. If you find yourself iterating over rooms inside
a loop over rooms, refactor.

## Phase C — View endpoint

Add to `web/views.py`:

```python
def direbuilder_zone_score(request, zone_id):
    """GET endpoint. Returns the Zone Score for the canonical
    saved zone."""
```

URL routing in `web/urls.py`:

```python
path('direbuilder/api/zone/<str:zone_id>/score/',
     views.direbuilder_zone_score,
     name='direbuilder_zone_score')
```

The view:
1. Accepts GET only. Reject other methods with 405.
2. Loads the canonical saved zone via the existing zone-load path
   (do NOT compute on workingZone — score is always against
   what's on disk).
3. Calls `score_zone(zone)` from the scorer module.
4. Returns the ZoneScore payload as JSON with HTTP 200.
5. On errors (missing zone, bad data, scorer exception), return
   HTTP 500 with the error message in `{"error": "..."}` shape,
   following the existing error pattern.

CSRF: GET endpoints don't need CSRF tokens. Standard Django.

## Phase D — Header strip replacement

Locate the placeholder block in `web/templates/webclient/direbuilder.html`:

```html
COMING SOON: DIREBUILDER ZONE SCORE
We build better builders.
```

Replace it with the new score header structure. Markup:

```html
<div class="direbuilder-zone-score" data-direbuilder-zone-score>
  <div class="direbuilder-zone-score-tagline">
    DireEngine ZoneScore — <em>We build better zones by building better builders.</em>
  </div>
  <div class="direbuilder-zone-score-strip">
    <div class="direbuilder-zone-score-composite" data-zone-score-composite>
      <span class="direbuilder-zone-score-number" data-zone-score-number>—</span>
      <span class="direbuilder-zone-score-tier" data-zone-score-tier>Loading</span>
    </div>
    <div class="direbuilder-zone-score-subs">
      <div class="direbuilder-zone-score-sub" data-sub="completeness">
        <span class="label">Completeness</span>
        <span class="value" data-zone-score-completeness>—</span>
      </div>
      <div class="direbuilder-zone-score-sub" data-sub="depth">
        <span class="label">Depth</span>
        <span class="value" data-zone-score-depth>—</span>
      </div>
      <div class="direbuilder-zone-score-sub" data-sub="engagement">
        <span class="label">Engagement</span>
        <span class="value" data-zone-score-engagement>—</span>
      </div>
    </div>
    <button class="direbuilder-zone-score-toggle" data-zone-score-toggle aria-expanded="false" aria-label="Toggle Zone Score breakdown">
      <span class="direbuilder-zone-score-stale" data-zone-score-stale hidden>Stale (save to refresh)</span>
      <span class="direbuilder-zone-score-chevron">▾</span>
    </button>
  </div>
  <div class="direbuilder-zone-score-panel" data-zone-score-panel hidden>
    <!-- Expanded panel content rendered by JS -->
  </div>
</div>
```

The composite number is in larger font than the sub-scores. The
tier label sits next to the composite number. The three sub-score
labels and values sit in a row beneath. The toggle button shows
the chevron and the optional "Stale" indicator.

The expanded panel renders the breakdown when toggled open.

Add a tooltip data-attribute on the score header so MT-511's
tooltip system can attach a ⓘ icon explaining what the score
represents:

```html
data-tooltip-field="zone_score.header"
```

Add the tooltip entry to `world/builder/content/tooltips.yaml`:

```yaml
zone_score.header:
  purpose: "DireEngine ZoneScore measures how complete, atmospheric, and engaging your zone is. Higher scores mean a richer player experience."
  examples:
    - "Composite: weighted average of three sub-scores"
    - "Completeness (40%): are required fields filled?"
    - "Depth (30%): is each room atmospherically rich?"
    - "Engagement (30%): is there enough for players to do?"
  ai_note: "Score updates after each successful save. The bottom 5-10 rooms are surfaced as 'needs attention' to guide where to spend effort next."
```

## Phase E — Expanded panel UI

When the toggle is clicked, render the panel content:

```html
<div class="direbuilder-zone-score-panel-content">
  <div class="direbuilder-zone-score-section">
    <h3>Completeness — <span data-completeness-score>78</span></h3>
    <ul class="direbuilder-zone-score-breakdown">
      <li>Zone fields: 5/5</li>
      <li>Room names: 211/211</li>
      <li>Room environments: 198/211</li>
      <li>Terrain (primary): 47/211</li>
      <li>Room descriptions: 12/211</li>
      <li>Room identity tags: 73/211</li>
      <li>Exit validity: 209/211</li>
      <li>NPC declarations: 18/18</li>
    </ul>
  </div>
  <div class="direbuilder-zone-score-section">
    <h3>Depth — <span data-depth-score>34</span></h3>
    <ul class="direbuilder-zone-score-breakdown">
      <li>Atmosphere coverage (avg): 42%</li>
      <li>Tag density (avg): 55%</li>
      <li>Generated descriptions: 5%</li>
      <li>Stateful descriptions: 18%</li>
    </ul>
  </div>
  <div class="direbuilder-zone-score-section">
    <h3>Engagement — <span data-engagement-score>54</span></h3>
    <ul class="direbuilder-zone-score-breakdown">
      <li>Rooms with NPCs: 8%</li>
      <li>Rooms with items: 4%</li>
      <li>Rooms with details: 12%</li>
      <li>Ambient messages: 6%</li>
      <li>Stateful: 18%</li>
      <li>Shops: 2%</li>
      <li>Hostile: 0%</li>
      <li>Resource terrain: 22%</li>
      <li>Healing herbs: 15%</li>
      <li>Quest hooks: 0% (system pending)</li>
      <li>Engagement coverage: 31% (target 22%)</li>
    </ul>
  </div>
  <div class="direbuilder-zone-score-section">
    <h3>Needs Attention</h3>
    <ul class="direbuilder-zone-score-attention">
      <li data-room-id="CRO_450_300">
        <span class="room-name">Amberwick Lane, Western Run</span>
        <span class="room-score">34 · Sketch</span>
        <span class="room-gap">no environment</span>
      </li>
      <!-- ... bottom N rooms ... -->
    </ul>
    <button class="direbuilder-zone-score-show-all" data-zone-score-show-all>
      Show all rooms
    </button>
  </div>
</div>
```

Clicking a room in the "Needs Attention" list selects that room
in the editor (uses the existing room-selection logic — call
the same function that the map node click calls).

Clicking "Show all rooms" reveals the full per-room breakdown
sorted by composite ascending. Same row format as Needs Attention.
Toggle back collapses to bottom-N.

## Phase F — JS wiring

Add to `web/static/webclient/js/direbuilder.js`:

1. **Module-scoped score state.** Keep last fetched score in
   memory. Track whether it's stale (zone is dirty).

2. **Initial fetch on page load.** Fetch the score from the new
   endpoint after the page renders. Populate the header strip.

3. **Refetch after successful save.** When the save endpoint
   returns success and replaces the canonical zone, also fetch the
   updated score and re-render the header. Mark not-stale.

4. **Stale indicator.** When the dirty indicator updates and
   workingZone is dirty, show "Stale (save to refresh)" in the
   header. When dirty clears (after successful save or discard),
   hide the stale indicator and refetch the score.

5. **Toggle handler.** Clicking the toggle button shows/hides the
   expanded panel. ARIA: aria-expanded="true"/"false". Chevron
   rotates.

6. **Room-click handler in needs-attention list.** Clicking a row
   triggers the same room-selection function that the map node
   click triggers. Builder ends up with that room loaded in the
   editor.

7. **Show all rooms toggle.** Reveals/hides full per-room list.

8. **Error handling.** If the score fetch fails, leave the header
   in a degraded state showing "—" for all values and a small
   error indicator. Don't crash the page.

## Phase G — CSS

Add to `web/static/webclient/css/direbuilder.css`:

- `.direbuilder-zone-score`: container, padding consistent with
  existing header padding
- `.direbuilder-zone-score-tagline`: italic for the "We build
  better zones..." part, normal weight for "DireEngine ZoneScore"
  prefix, accent color
- `.direbuilder-zone-score-strip`: flex row, composite on left,
  sub-scores in middle, toggle on right
- `.direbuilder-zone-score-composite`: large composite number
  (1.5-1.8x the sub-score number font size — pick a multiplier
  that reads clearly without overwhelming)
- `.direbuilder-zone-score-tier`: smaller font next to composite,
  accent color
- `.direbuilder-zone-score-sub`: each sub-score in a flex column,
  label small uppercase, value medium-sized number
- `.direbuilder-zone-score-toggle`: button styled subtly (no heavy
  border, just a chevron)
- `.direbuilder-zone-score-stale`: small italic text, accent
  warning color
- `.direbuilder-zone-score-panel`: drops below the strip when
  expanded, border-top to separate from header
- `.direbuilder-zone-score-section h3`: section header styling
- `.direbuilder-zone-score-breakdown`: list styling for breakdown
  items, no bullets, tight spacing
- `.direbuilder-zone-score-attention li`: row layout with name,
  score, gap label
- Tier-specific accent colors (optional, low priority): different
  composite color based on tier (red → green gradient roughly).
  Use existing accent variables; don't introduce new color
  primitives.

Use existing CSS variables for colors and spacing. Match the
existing visual language. The score header should feel like part
of the page, not a foreign widget.

## Phase H — Cache-bust and verify

Bump direbuilder.js and direbuilder.css versions. Restart server.

## Verification checklist

1. Page loads, no console errors. Header shows the new tagline
   "DireEngine ZoneScore — We build better zones by building
   better builders" and a composite score with three sub-scores.
2. Composite font is visibly larger than sub-score fonts.
3. Tier label is next to composite (e.g., "78 · Solid").
4. Tooltip ⓘ icon appears next to the score header. Hovering
   shows the explanation from tooltips.yaml.
5. Toggle button opens the expanded panel. Panel shows three
   breakdown sections plus Needs Attention.
6. Each breakdown section shows correct counts and percentages
   for the loaded zone.
7. Needs Attention shows 5-10 rooms with the lowest composites.
   Each row shows name, score, tier, and biggest gap.
8. Clicking a room in Needs Attention selects that room in the
   editor (same behavior as clicking the map node).
9. "Show all rooms" reveals full per-room breakdown sorted
   ascending by composite.
10. Edit any field on any room. Dirty indicator appears. Stale
    indicator appears in score header.
11. Save the zone. Score refetches and updates. Stale clears.
12. Test a 6-room zone (Builder2) and the 211-room zone
    (new_landing). Both should score in under 500ms.
13. Score endpoint returns valid JSON with the documented shape.
14. Legacy /builder/ route still loads, has no Zone Score wiring,
    no quest_hooks references in its UI.
15. Verify quest_hooks: open a saved zone YAML, manually add
    `quest_hooks: ["test_hook"]` to a room, save zone, refresh
    page, verify the engagement quest_pct shows the corresponding
    increase in the breakdown.

## Stop conditions

- Edit only the files listed in "In scope" above.
- Do not edit any file not listed.
- Do not implement the quest system.
- Do not add UI for quest_hooks tagging.
- Do not modify the AI pipeline, the engine, or the legacy
  /builder/ route.
- If the scorer takes longer than 500ms on the 211-room zone,
  stop and report.
- If the existing room schema requires restructuring beyond
  adding quest_hooks, stop and report.
- If the existing dirty-tracking state needs restructuring to
  support the stale indicator, stop and report.
- If any existing test fails, stop and report.

## Required artifacts

1. `world/builder/scoring/zone_scorer.py` (new module)
2. `world/builder/schemas/` updated with quest_hooks
3. `web/views.py` updated with score endpoint and quest_hooks
   normalization
4. `web/urls.py` updated with score route
5. `web/templates/webclient/direbuilder.html` updated header strip
   and expanded panel markup
6. `web/static/webclient/js/direbuilder.js` updated with score
   wiring and stale indicator
7. `web/static/webclient/css/direbuilder.css` updated with score
   styles
8. `world/builder/content/tooltips.yaml` updated with
   zone_score.header entry
9. `exports/mt513_zone_score_validation.md` — short note capturing:
   - Builder2 score (small zone): composite + sub-scores + tier +
     compute time
   - new_landing score (large zone): composite + sub-scores +
     tier + compute time
   - One full save → score refresh → stale → save → refetch cycle
   - Needs Attention behavior verified (clicking a room selects it)
   - Quest hooks validation (manual YAML edit produces expected
     score change)
   - Confirmation that the engine, AI pipeline, and legacy
     /builder/ are untouched

## Followup queue (do not implement in this dispatch)

- MT-514: Engine refactor — ForageAbility reads forage catalog
  and uses room.terrain to populate forage tables.
- MT-515 (or whenever): Quest system — design conversation, then
  schema, then engine, then DireBuilder UI for tagging.
- MT-516: Score history / trend tracking — show how a zone's
  score has changed over time.
- MT-517: Configurable rubric — let admins customize the weights
  and criteria.
- MT-518: Inter-zone comparison — see how multiple zones compare
  on the same axes.
```

Three notes for what to watch when the agent reports back:

**The 500ms performance check matters.** A 211-room zone with the engagement-axis healing-herb lookup could become slow if the agent does the catalog lookup inside a per-room loop. The scorer should load the catalog once and pre-compute a `secondary_terrain → has_healing_herbs` lookup table at module load. If the agent reports "scoring takes 800ms," that's the architectural cause. Fix is straightforward but worth catching early.

**The "biggest_gap" string matters.** This is what builders actually read in the Needs Attention list. The agent's choice of fixed labels ("no environment", "no terrain", "untagged", "no description") needs to be builder-friendly. If the labels feel technical or accusatory, ask for a rewrite. The wording is small but high-leverage — it's the prose the builder sees most often when using Zone Score.

**The "Stale" indicator behavior is subtle.** The score reflects what's on disk. When workingZone is dirty, the displayed score is technically out-of-date. The stale label communicates that without confusing the builder. If the agent gets confused about when to show/hide it (during in-flight save, during error states, etc.), the rule is: stale is shown whenever dirty is shown. After save success, both clear together. After save failure, dirty stays dirty and stale stays stale. After discard, both clear.

When the agent reports back, what to look for:

- The composite number in the header strip should be visibly larger than the sub-score numbers. If they look the same size, ask for an adjustment.
- The tier label should sit comfortably next to the composite without crowding. If it wraps to a second line on smaller widths, ask for layout adjustment.
- The expanded panel should feel like part of the page, not a popup. If it floats or animates in unexpectedly, push back.
- The Needs Attention list should genuinely surface the rooms most worth fixing. If the bottom rooms are all empty stubs that the builder hasn't gotten to yet (which is fine), the score is honest. If the bottom rooms are technically scored low for a confusing reason ("rooms in pristine condition that just lack stateful descriptions"), ask the agent to double-check the per-room composite logic.
- The biggest_gap labels should be useful. If they say things like "score below threshold" or "criteria not met," push back — they should name the specific missing thing.

This is the V1. The score will get richer over time as you use DireBuilder for real content and discover what the rubric actually needs to capture. Future dispatches will refine. For now, ship V1 and use it.

Send the dispatch.