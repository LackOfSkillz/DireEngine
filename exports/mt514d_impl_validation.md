# MT-514d-impl validation

Status: SHIPPED

## Phase A-G implementation

Files shipped:

- `engine/render/state_markup.py`
- `typeclasses/rooms_extended.py`
- `tests/test_state_markup.py`
- `docs/architecture/state_aware_descriptions.md`
- `exports/mt514d_impl_validation.md`

Implementation choices encoded:

- Namespaced runtime syntax: `$state(group:value, content)`
- Multi-value matching: pipe-separated values within one group
- Coexistence preserved: `desc_<state>` selection still resolves first, markup renders second
- Parser/AST is pure and side-effect free
- Cached parse results use `@lru_cache` keyed by raw description text
- Malformed fragments are stripped from output and logged with room context
- Unknown groups and query failures render empty and log warnings

## Tunable values shipped

- Parse cache: `@lru_cache(maxsize=2048)` keyed by full description text
- Registered groups: `weather`, `invasion`, `season`, `time`
- Performance target used for tests: warm average render below `5ms`
- Bounded-time test implementation: warm average measured over repeated cached renders

## Phase H tests

Focused implementation tests:

- Command: `c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_state_markup`
- Result: `28` tests passed

Nearest regression slice:

- Command: `c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_calendar`
- Result: `19` tests passed

Total executable validation run for this dispatch: `47` passing tests.

Covered behaviors:

- parser tokenization and AST shape
- malformed markup stripping
- registry resolution for all four groups
- unknown-group and query-failure warnings
- renderer matching and non-matching behavior
- parse caching behavior
- `ExtendedDireRoom.get_stateful_desc()` integration
- coexistence with `desc_<state>` variants
- bounded-time warm render check

## Phase I live verification

Verification method:

- temporary live `ExtendedDireRoom` fixture created in the Evennia runtime
- fixture description contained both `weather` and `invasion` markup
- direct live `return_appearance()` calls used for authoritative output capture
- fixture deleted after verification

Fixture description:

```text
A small clearing.$state(weather:storm|heavy_rain, Rain pelts the ground.)$state(invasion:goblin_raid, A goblin's footprints are scattered nearby.) The trees sway gently.
```

Observation matrix outputs:

```json
[
  {
    "weather": "clear",
    "invasion": "none",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. The trees sway gently."
  },
  {
    "weather": "storm",
    "invasion": "none",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. Rain pelts the ground. The trees sway gently."
  },
  {
    "weather": "heavy_rain",
    "invasion": "none",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. Rain pelts the ground. The trees sway gently."
  },
  {
    "weather": "clear",
    "invasion": "goblin_raid",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. A goblin's footprints are scattered nearby. The trees sway gently."
  },
  {
    "weather": "storm",
    "invasion": "goblin_raid",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. Rain pelts the ground. A goblin's footprints are scattered nearby. The trees sway gently."
  },
  {
    "weather": "fog",
    "invasion": "none",
    "output": "|cMT514D Impl Fixture(#27192)|n\nA small clearing. The trees sway gently."
  }
]
```

Cleanup result:

- fixture deleted: `true`

Performance measurements:

- full live `return_appearance()` cold render: `13.601ms`
- full live `return_appearance()` warm average over 500 renders: `1.35ms`
- parser/renderer cold render in isolation: `0.696ms`
- parser/renderer warm average over 1000 renders: `0.014ms`

Interpretation:

- The shipped parser is comfortably inside the intended warm render budget.
- The larger cold `return_appearance()` cost is dominated by the broader Evennia room
  appearance path, not the parser itself.

## Phase J documentation

Document checked in:

- `docs/architecture/state_aware_descriptions.md`

Documented areas:

- syntax contract
- registered state groups and example values
- authoring guidance
- coexistence with `desc_<state>` variants
- malformed markup behavior
- current v1 boundaries

## Known limitations

Out of scope for v1 and intentionally not shipped:

- nested `$state(...)` fragments
- logical operators across groups
- computed values or template variables
- ad hoc groups outside the registry
- rendered-output caching keyed by state vector
- admin tooling or authoring commands for markup inspection

These remain valid v2 follow-ups if content authoring later proves constrained.

## Final state

Runtime `$state(...)` parsing shipped. Both authoring patterns (`$state(...)` markup and
`desc_<state>` variants) coexist. Ready for content authoring and the manual trial zone
build.