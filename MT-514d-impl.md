# MT-514d-impl — Runtime `$state(...)` parser for room descriptions

## Background

MT-514d audited render-time state behavior in DireEngine and produced
decisive findings:

- `$state(...)` markup is widespread in generation prompts, templates,
  and content — but the production engine has no parser. If literal
  markup ends up in `db.desc`, players see it verbatim.
- `desc_<state>` switching via `ExtendedDireRoom.get_stateful_desc()`
  works correctly when the matching `room_state` tag and `desc_<state>`
  attribute are present.
- Live content using either system: zero rooms. Out of 1180 rooms in
  the live DB, none have `desc_<state>` attributes, none have literal
  `$state(...)` markup, none have `room_state` tags.

So the infrastructure for one approach (`desc_<state>` switching) is
in place but unused. The other approach (runtime `$state(...)` parsing)
is the one the generation pipeline already produces, but the engine
doesn't evaluate it.

The user's design call: **build the runtime `$state(...)` parser**.
Keep the existing `desc_<state>` selector as a coexisting authoring
option for cases where content authors want a full variant override.
Two patterns supported; content picks what fits.

User decisions locked for this dispatch:

1. **Namespaced syntax:** `$state(group:value, content)` — e.g.,
   `$state(weather:storm, ...)`. Disambiguates state values across
   groups.
2. **Multi-value matching:** `$state(weather:storm|heavy_rain, ...)`
   fires on either match. Pipe-separated values within one group.
3. **AST caching:** parse description text into an AST once per room
   description; re-parse only when `db.desc` changes. Render-time
   cost is evaluation, not parsing.
4. **Error handling:** malformed markup is stripped from player
   output and logged as an admin warning. Players never see broken
   markup; staff are notified.
5. **Coexistence:** keep the existing `desc_<state>` selector
   alongside the new parser. Both are valid authoring patterns.
   Selection precedence is documented (see Phase D).

This dispatch is the implementation of all five locked decisions plus
the supporting infrastructure (state group registry, render-path
integration, tests, documentation).

## Architectural guardrails (READ FIRST)

This is a real engineering dispatch — probably the largest in the
MT-514 arc apart from MT-514c-impl. The biggest risk is scope drift.

The second-biggest risk is over-engineering the markup syntax. The
locked decisions specify a small, focused DSL. Resist adding features
the locked decisions don't include (nested fragments, conditional
operators, computed values, etc.). The DSL should do what's specified
and nothing more.

**Frozen scope:**

1. Phase A: Read MT-514d findings (`docs/audits/render_time_state.md`)
   and the existing render path in `typeclasses/rooms_extended.py`.
   Document the integration point precisely.
2. Phase B: Implement the parser. Tokenizes and parses `$state(...)`
   markup into an AST. Pure function, no side effects, no engine
   dependencies.
3. Phase C: Implement the state group registry. Maps state group
   names (`weather`, `invasion`, `season`, `time`) to query functions
   that return current values for a zone/room/character context.
4. Phase D: Implement the renderer. Evaluates the AST against current
   state, producing the final description string. Handles the empty-
   fragment case (state doesn't match → fragment renders as empty
   string, surrounding text remains coherent).
5. Phase E: Wire into `ExtendedDireRoom.get_stateful_desc()` (or
   wherever the integration point is). The runtime parser fires on
   the resolved description after `desc_<state>` selection. So a
   description with both a `desc_storm` variant and inline
   `$state(invasion:goblin_raid, ...)` markup gets the variant
   selected first, then markup evaluated within it.
6. Phase F: Caching layer. Parse the description's AST once and cache
   it; invalidate on description change.
7. Phase G: Error handling. Malformed markup is stripped from output
   and logged. Admin warning surface should be visible to staff but
   not to players.
8. Phase H: Tests at `tests/test_state_markup.py` covering parser,
   renderer, registry, caching, error handling, and integration with
   `get_stateful_desc()`.
9. Phase I: Live verification with fixture rooms. Same pattern MT-514d
   used — temporary room with markup, observe rendering, clean up.
10. Phase J: Documentation at `docs/architecture/state_aware_descriptions.md`.
    Defines the syntax, state groups, error behavior, authoring
    guidance, examples.
11. Phase K: Validation artifact at `exports/mt514d_impl_validation.md`.

**Frozen what-not-to-do list:**

- DO NOT add features beyond locked decisions:
  - No nested `$state(...)` inside `$state(...)` — flat fragments only
  - No conditional operators (`AND`, `OR`, `NOT` across groups)
  - No computed values or template variables (`$var(...)` etc.)
  - No state group beyond what's registered (no ad-hoc groups)
  - No content transforms beyond literal substitution
- DO NOT modify the existing `desc_<state>` selector. It coexists
  unchanged. The new parser fires after the selector resolves.
- DO NOT modify any room descriptions, zone YAMLs, or production
  content. Test fixtures are temporary and removed post-test.
- DO NOT modify the calendar, weather, invasion, terrain, foraging,
  or any other runtime state module. The parser consumes them via
  the registry.
- DO NOT modify generation prompts, templates, or AI generation
  pipeline. The agent reads them to confirm the syntax is consistent
  with what's produced, but does not change them.
- DO NOT add new state groups without explicit registry entries.
  Each state group maps to a query function that the parser calls.
  Adding a group is intentional, not implicit.
- DO NOT cache state values themselves — only the parsed AST. State
  values come from already-cached upstream services (weather,
  invasion). Re-querying them is cheap.
- DO NOT add admin commands or tooling for the markup system in
  this dispatch. That's polish for a future content-authoring arc.
- DO NOT precompile or batch-parse descriptions for all rooms at
  startup. Parsing is lazy per-room on first render and cached
  thereafter.
- DO NOT add new test infrastructure beyond what the existing test
  suite provides. Use unittest, pylanceRunCodeSnippet for live
  verification, follow patterns from `tests/test_forage.py` and
  `tests/test_weather.py`.

**Stop-and-report conditions:**

- If reading the existing render path reveals integration is more
  complex than expected (multiple description-resolution paths,
  unclear ordering, surprising side effects), stop and report.
- If the parser design surfaces ambiguity in the locked syntax
  (e.g., what does `$state(weather:storm|heavy_rain|, ...)` with
  trailing pipe mean), stop and report. Don't silently pick a
  resolution — surface the question.
- If the state group registry conflicts with existing module
  boundaries (e.g., the calendar API doesn't expose a clean query
  function for the registry to call), stop and report. We may
  need a small adapter, or we may need to surface a missing API.
- If caching breaks any existing test in subtle ways (e.g., test
  fixtures reuse room objects across tests and the cache holds
  stale ASTs), stop and report.
- If the parser's bounded-time test reveals that parsing a typical
  description is unexpectedly slow (more than a few milliseconds
  cold, less than a millisecond warm), stop and report.
- If integration with `get_stateful_desc()` reveals an ordering
  problem (e.g., `desc_<state>` selector and `$state(...)` parser
  fight for control), stop and report.
- If the live verification reveals the parser produces output that
  doesn't match unit test expectations, treat live as authoritative
  and stop and report.

## Phase A — Read MT-514d findings and integration point

Read `docs/audits/render_time_state.md` end to end. Confirm:

- The render path entry: `ExtendedDireRoom.get_stateful_desc()`
- The base description attribute: `db.desc`
- The variant attributes: `db.desc_<state>` selected by `room_state`
  tag
- The Evennia appearance flow: `return_appearance()` calls
  `get_display_desc()` (or equivalent) which delegates to the
  custom `get_stateful_desc()` in `ExtendedDireRoom`

Document precisely where the new parser fires. The integration
order is:

1. `return_appearance()` builds the room appearance
2. `get_display_desc()` (or override) requests the description
3. `get_stateful_desc()` selects between `desc` and `desc_<state>`
   based on `room_state` tags (existing behavior, unchanged)
4. **NEW:** the resolved description string passes through the
   `$state(...)` parser/renderer, which evaluates fragments against
   current runtime state
5. The final string is returned to `return_appearance()` for display

The new step fires last. This means:
- A `desc_storm` variant can itself contain `$state(invasion:goblin_raid, ...)`
  markup, and both layers compose
- The base `desc` (no state variant matched) can contain markup
- Either pattern is valid authoring

## Phase B — Parser implementation

Build a parser that turns description text into an AST.

### B.1 Module location

`engine/render/state_markup.py` (or wherever existing engine
patterns suggest — agent decides based on existing module
organization). New module, no existing code to refactor.

### B.2 AST structure

Conceptually:

```python
@dataclass
class TextNode:
    text: str

@dataclass
class StateNode:
    group: str           # e.g., "weather"
    values: tuple[str]   # e.g., ("storm", "heavy_rain") for multi-value
    content: str         # the inline content if state matches
```

The full AST for a description is `list[TextNode | StateNode]` —
flat sequence of text and state fragments interleaved. No nesting.

### B.3 Tokenizer

The tokenizer scans description text and produces tokens:
- Plain text runs
- `$state(group:values, content)` fragments

Recognized syntax:
- `$state(weather:storm, content)` — single value
- `$state(weather:storm|heavy_rain, content)` — multi-value
- `$state(invasion:goblin_raid, content)` — different group
- Content can contain anything except an unescaped closing paren

Edge cases:
- Unbalanced parens in content: malformed, log warning, strip fragment
- Missing colon: malformed, log warning, strip fragment
- Empty group or empty values: malformed
- Whitespace tolerance around group, values, content: be lenient

### B.4 Parser

The parser consumes tokens and produces the AST. Pure function;
no side effects.

### B.5 Tests

Unit tests for:
- Plain text with no markup → single TextNode
- Description with one fragment → text + state + text
- Description with multiple fragments → interleaved sequence
- Multi-value fragment → StateNode with tuple of values
- Malformed markup → fragment stripped, plain text preserved
- Edge whitespace and formatting
- Empty description → empty AST
- Description with literal `$state` text that's not a fragment
  (e.g., `$states are interesting`) → preserved as plain text

## Phase C — State group registry

The registry maps group names to query functions.

### C.1 Module location

Same module as parser (`engine/render/state_markup.py`) or a
small companion module. Agent decides.

### C.2 Registry shape

```python
# Pseudocode
STATE_GROUPS = {
    "weather": lambda context: get_current_weather(context.zone_id),
    "invasion": lambda context: get_current_invasion(context.zone_id),
    "season": lambda context: get_current_season(),
    "time": lambda context: get_current_time_of_day(),
}
```

Where `context` is a small object carrying the rendering context:
- The room being rendered
- The viewer (character) — may inform some queries
- The zone_id

The agent designs the actual context object based on what the
existing query functions need.

### C.3 Initial groups

- `weather` — current zone weather state
- `invasion` — current zone invasion state
- `season` — current calendar season
- `time` — current time-of-day

These are the four groups the prompts and templates already
reference. No new groups in this dispatch.

### C.4 Query function failure handling

If a query function raises or returns None:
- The fragment renders as empty (state didn't match)
- The error is logged as an admin warning
- The render does not fail

### C.5 Tests

Unit tests for:
- Each registered group resolves correctly when state matches
- Each registered group resolves to empty when state doesn't match
- Unknown group → empty fragment + admin warning logged
- Query function error → empty fragment + admin warning logged

## Phase D — Renderer

The renderer evaluates the AST against current state.

### D.1 Renderer shape

```python
def render(ast: list, context: Context) -> str:
    result = []
    for node in ast:
        if isinstance(node, TextNode):
            result.append(node.text)
        elif isinstance(node, StateNode):
            current = STATE_GROUPS[node.group](context)
            if current in node.values:
                result.append(node.content)
            # else: fragment renders as empty
    return "".join(result)
```

Pseudocode; agent implements with proper error handling and the
actual context type.

### D.2 Empty-fragment behavior

When a fragment doesn't match (state isn't in values, or query
returns None), the fragment contributes empty string. Surrounding
text remains coherent. This means content authors should write
descriptions that read coherently with all fragments removed —
the markup is additive atmosphere, not load-bearing prose.

This is a content-authoring guideline that goes in Phase J docs.

### D.3 Tests

Unit tests for:
- Description with no fragments renders unchanged
- Fragment that matches → content included
- Fragment that doesn't match → empty
- Multi-value fragment matches any of its values
- Multiple fragments, mixed match/no-match → correct interleaving
- Description rendering is deterministic given same state
- Description rendering changes when state changes

## Phase E — Wire into `get_stateful_desc()`

The integration point.

### E.1 Modify `ExtendedDireRoom.get_stateful_desc()`

The existing method selects among `desc`, `desc_<state>` based on
`room_state` tag. After selection, the resolved description string
passes through the renderer.

Pseudocode:

```python
def get_stateful_desc(self):
    # Existing selector logic — unchanged
    description = self._select_desc_variant()  # returns desc or desc_<state>

    # NEW: render any $state(...) markup
    ast = self._get_or_parse_ast(description)
    context = self._build_render_context()
    return render(ast, context)
```

The agent inspects the actual existing implementation and chooses
the integration point that matches the code's current structure.

### E.2 The render context

Carries the rendering context:
- `self` (the room)
- The viewer if available (some state queries may want it)
- The zone_id

Agent designs based on what the registered query functions need.

### E.3 Performance

Render fires on every `look`. Should be fast:
- AST cached per description (Phase F)
- State queries are cached upstream (weather, invasion)
- Renderer iterates AST, calls registry, concatenates strings

Bounded-time target: render of a typical description (200-500
chars, 1-3 fragments) should complete in under 5ms warm.

If the agent's measurement reveals slower performance, document
and propose mitigation.

## Phase F — AST caching

Parsing description text on every render is wasteful. Cache the
parsed AST per room.

### F.1 Cache shape

Module-level dict keyed by description text (or by room ID +
description hash). Cleared on description change.

### F.2 Invalidation

The cache invalidates when `db.desc` (or the relevant variant
attribute) changes. Two reasonable approaches:

**Option F.2.a:** Hash the description text; key the cache by
hash. Different text = different key. No explicit invalidation
needed.

**Option F.2.b:** Store the cache on the room object itself (as
an `ndb` attribute, not persistent). Invalidate on attribute set
hooks.

Option F.2.a is simpler. Agent picks; documents the choice.

### F.3 Tests

Unit tests for:
- Same description text produces same AST (cached)
- Modified description text produces new AST (cache miss)
- Cache survives multiple renders without growth pathology
- Cache doesn't leak across room instances inappropriately

## Phase G — Error handling

Malformed markup behavior:

### G.1 Detection

The parser detects malformed markup during tokenization:
- Unbalanced parens
- Missing colon between group and values
- Empty group or values
- Unknown state group (this is detected at render time, not parse
  time, since the registry is consulted during render)

### G.2 Behavior

When malformed markup is detected:
- The malformed fragment is stripped from output (player sees
  surrounding text without the broken fragment)
- An admin warning is logged via Evennia's logger (or whatever
  staff-visible logging exists in DireEngine)
- The warning includes: room ID, description preview, the specific
  error

Players never see broken markup. Staff see warnings and can fix
content.

### G.3 Tests

- Malformed fragment is stripped
- Warning is logged with the expected information
- Malformed input doesn't raise unhandled exceptions

## Phase H — Tests

`tests/test_state_markup.py` — focused unit tests parallel to
`tests/test_forage.py` and `tests/test_weather.py` patterns.

Coverage:

### Parser

- `test_parse_plain_text` — no markup → single TextNode
- `test_parse_single_fragment` — one fragment → text + state + text
- `test_parse_multiple_fragments` — multiple fragments interleave
- `test_parse_multi_value_fragment` — pipe-separated values
- `test_parse_unbalanced_parens` — malformed → stripped
- `test_parse_missing_colon` — malformed → stripped
- `test_parse_empty_description` — empty AST
- `test_parse_literal_dollar_state` — `$states are` preserved as text

### Registry

- `test_registry_resolves_weather` — weather group calls correctly
- `test_registry_resolves_invasion`
- `test_registry_resolves_season`
- `test_registry_resolves_time`
- `test_registry_unknown_group_logs_warning`
- `test_registry_query_error_logs_warning`

### Renderer

- `test_render_no_fragments_returns_text`
- `test_render_matching_fragment_includes_content`
- `test_render_non_matching_fragment_empty`
- `test_render_multi_value_matches_any`
- `test_render_mixed_matches`
- `test_render_state_change_changes_output`

### Caching

- `test_ast_cached_for_same_description`
- `test_ast_recomputed_for_changed_description`
- `test_cache_does_not_leak_across_rooms`

### Integration

- `test_get_stateful_desc_renders_markup` — full integration test
  with `ExtendedDireRoom.get_stateful_desc()`
- `test_desc_state_variant_with_markup` — `desc_storm` variant
  containing `$state(invasion, ...)` composes correctly
- `test_no_markup_no_change_in_behavior` — descriptions without
  markup render as before (regression guard)

### Bounded-time

- `test_render_completes_within_bounded_time` — typical render
  under 5ms warm

## Phase I — Live verification

Same pattern MT-514d used. Temporary fixture room, observe rendering
across state changes, clean up.

### I.1 Setup

Create a temporary `ExtendedDireRoom` with a base description that
exercises multiple state groups:

```
A small clearing. $state(weather:storm|heavy_rain, Rain pelts the
ground.) $state(invasion:goblin_raid, A goblin's footprints are
scattered nearby.) The trees sway gently.
```

### I.2 Observation matrix

For each combination, capture verbatim render output:

- Weather=clear, invasion=none → markup fragments empty, base text
  remains
- Weather=storm, invasion=none → rain fragment fires
- Weather=heavy_rain, invasion=none → rain fragment fires (multi-value)
- Weather=clear, invasion=goblin_raid → goblin fragment fires
- Weather=storm, invasion=goblin_raid → both fragments fire
- Weather=fog, invasion=none → neither fragment fires (fog isn't in
  the rain match)

### I.3 Cleanup

Delete the fixture room. Restore any modified character location.
Verify no residual state.

### I.4 Performance

Measure render time on a real `look` against the fixture:
- Cold (first render): expect 1-5ms
- Warm (cached AST): expect under 1ms

Document timings.

## Phase J — Documentation

`docs/architecture/state_aware_descriptions.md` — the contract for
content authors and the AI generation pipeline.

Structure:

```markdown
# State-Aware Description Markup

## Overview
[2-3 paragraphs explaining the markup system, when to use it, how
it relates to `desc_<state>` variants]

## Syntax
[The `$state(group:values, content)` form, with examples]

## Registered state groups
[Each group: name, what it queries, what values it can return,
example fragment]

## Authoring guidance
[How to write descriptions that read coherently with fragments
absent. Markup is additive atmosphere, not load-bearing.]

## Authoring patterns

### Pattern 1: inline atmospheric fragments
[Use markup when state-aware text is a sentence or two of
atmosphere within an otherwise-static description]

### Pattern 2: full variant override
[Use `desc_<state>` when a state genuinely needs entirely
different prose — e.g., a flooded room during severe weather]

### Pattern 3: combined
[A `desc_storm` variant can itself contain `$state(invasion, ...)`
markup. Both layers compose.]

## Error behavior
[Malformed markup is stripped; staff are warned; players don't
see broken syntax]

## Examples
[Real worked examples covering common cases]
```

Documentation is not an afterthought. Without it, content authors
(and the AI generation pipeline) won't know the contract.

## Phase K — Validation artifact

`exports/mt514d_impl_validation.md`:

```markdown
# MT-514d-impl validation

Status: SHIPPED

## Phase A-G implementation
[Files modified, modules created, integration point, key design
choices encoded.]

## Tunable values shipped
[Bounded-time target, cache invalidation strategy chosen, etc.]

## Phase H tests
[Test count, all-passing confirmation, bounded-time threshold
chosen and result.]

## Phase I live verification
[Verbatim outputs of each observation in the matrix, performance
measurements, fixture cleanup confirmed.]

## Phase J documentation
[Document checked in at docs/architecture/state_aware_descriptions.md]

## Known limitations
[The locked-decision boundaries: no nested fragments, no logical
operators across groups, no computed values, etc. Documented as
"out of scope for v1, may be revisited in v2 if content authoring
proves limited."]

## Final state
[One line: "Runtime $state(...) parsing shipped. Both authoring
patterns ($state markup and desc_<state> variants) coexist. Ready
for content authoring and the manual trial zone build."]
```

## Verification checklist

1. MT-514d findings read; integration point documented.
2. Parser implemented and tested.
3. State group registry implemented with four initial groups.
4. Renderer implemented and tested.
5. Integration into `get_stateful_desc()` complete.
6. AST caching works and invalidates correctly.
7. Error handling: malformed markup stripped, warnings logged.
8. All locked decisions encoded:
   - Namespaced syntax (`group:value`)
   - Multi-value matching with `|`
   - AST caching
   - Strip-with-warning on malformed
   - Coexistence with `desc_<state>` selector
9. Tests at `tests/test_state_markup.py` all pass.
10. Live verification matrix all states pass.
11. Documentation checked in at
    `docs/architecture/state_aware_descriptions.md`.
12. Validation artifact created.
13. No production content modified.
14. No code outside the in-scope list modified.

## Stop conditions

- Edit only:
  - `engine/render/state_markup.py` (new, or wherever existing
    engine patterns suggest)
  - `typeclasses/rooms_extended.py` (modify `get_stateful_desc()`)
  - `tests/test_state_markup.py` (new)
  - `docs/architecture/state_aware_descriptions.md` (new)
  - `exports/mt514d_impl_validation.md` (new)
  - Possibly a small registry/context module if separation is
    cleaner — agent decides
- Stop and report on render path complexity surprises.
- Stop and report on syntax ambiguities in locked decisions.
- Stop and report on registry/module boundary conflicts.
- Stop and report on caching breakages of existing tests.
- Stop and report on bounded-time perf miss.
- Stop and report on integration ordering problems.
- Stop and report on live verification anomalies.
- Do not extend syntax beyond locked decisions.
- Do not modify production content.
- Do not chain follow-up fixes within this dispatch.

## Required artifacts

1. New `engine/render/state_markup.py`
2. Updated `typeclasses/rooms_extended.py`
3. New `tests/test_state_markup.py`
4. New `docs/architecture/state_aware_descriptions.md`
5. New `exports/mt514d_impl_validation.md`

## Followup queue

- **Content authoring dispatch:** After MT-514d-impl ships,
  optionally a separate dispatch (or content task on user's
  timeline) to populate state-aware descriptions on a sample of
  rooms. Probably the manual trial zone is where this lands —
  authoring trial zone descriptions with markup is the natural
  exercise of the system.
- **AI generation prompt updates:** Verify the existing prompts
  produce markup matching the now-implemented syntax. The audit
  showed prompts already use `$state(...)` form; this is a
  verification, not a redesign. Likely a small content-pipeline
  task.
- **Performance v2 (deferred):** If render-time performance becomes
  a concern in active play (large rooms, many concurrent players,
  complex descriptions), revisit caching strategy. v1 cache is
  per-description AST; v2 might cache rendered output keyed by
  state vector. Not a v1 concern.
- **Syntax v2 (deferred):** If content authoring reveals limits in
  the locked syntax (no nested fragments, no logical operators),
  revisit. v2 might add `$state(weather:storm AND time:night, ...)`
  or similar. Not a v1 concern.
- **MT-516 (next):** Targeting, stackables, display aggregation.
- **MT-515 (after):** Project-wide skill-attempts framework.
- **Manual trial zone build:** Becomes feasible after MT-514d-impl
  ships (description rendering ready), MT-516 ships (player UX
  cleaned up), and content authoring conventions are documented.