# Bundle Extension API

Purpose: canonical contract for DireEngine bundle registration, discovery, and boot-time loading.

This document is the implementation contract introduced by DRG-022.5. Downstream Phase 4 dispatches should register content through this API instead of introducing new one-off registries or hardcoding new profession/race/zone/trade content into the engine.

## DireLore authority

DireLore on `127.0.0.1:5432` is the single source of truth for canonical mechanics, maps, skills, professions, stats, spells, abilities, items, effects, shops, and recipes. Existing DireEngine code is not the authority for re-engineering math or content behavior.

For this dispatch's proof of concept, the only required canon query is `public.canon_stats`. The implemented stat registry confirms the schema directly from DireLore and loads these columns:

- `id`
- `name`
- `abbreviation`
- `gsl_dispatch_id`
- `description`
- `source_entity_id`
- `confidence`

If DireLore is unavailable at boot, the engine falls back to a minimal hardcoded stat set only so the engine remains operable. That fallback is a compatibility mechanism, not a replacement source of truth.

## Package layout

The extension architecture lives under `engine/bundles/`.

Key modules:

- `engine/bundles/registry.py`: base registry contract
- `engine/bundles/manifest.py`: `bundle.toml` parser
- `engine/bundles/loader.py`: bundle discovery, validation, ordering, and loading
- `engine/bundles/boot.py`: startup entry point and registry hub
- `engine/bundles/*_registry.py`: specific registry implementations

## Registry contract

Every registry implements the same minimal interface:

```python
class Registry:
    def register(self, key: str, definition: dict, *, source_bundle: str) -> None: ...
    def get(self, key: str) -> dict | None: ...
    def require(self, key: str) -> dict: ...
    def list_keys(self) -> list[str]: ...
    def list_by_bundle(self, bundle_id: str) -> list[str]: ...
    def is_registered(self, key: str) -> bool: ...
    def unregister(self, key: str, *, source_bundle: str) -> None: ...
```

Behavioral rules:

- `get()` returns `None` for missing keys and never raises for absence.
- `require()` raises `BundleNotLoadedError` for missing keys.
- `register()` raises `BundleConflictError` if a different bundle already owns the key.
- `unregister()` raises `BundleOwnershipError` if the caller bundle does not own the key.
- Definitions are copied on read and write; callers do not mutate registry internals by reference.

## Active registries

Eight registries now exist:

1. `profession_registry`
2. `race_registry`
3. `zone_registry`
4. `trade_registry`
5. `content_registry`
6. `skill_registry`
7. `stat_registry`
8. `spell_circle_registry`

Only `stat_registry` is populated in DRG-022.5. The others exist as stable extension points and remain empty until downstream migrations register content.

## Definition schemas

Current minimum schema requirements:

- Profession: `id`, `display_name`, `bundle_id`, `tier`
- Race: `id`, `display_name`, `bundle_id`, `tier`
- Zone: `id`, `display_name`, `bundle_id`, `tier`
- Trade: `id`, `display_name`, `bundle_id`, `tier`
- Content: `id`, `content_type`
- Skill: `id`, `display_name`
- Stat: `id`, `display_name`, `abbreviation`
- Spell circle: `id`, `display_name`

Downstream dispatches may extend these payloads, but should preserve the existing required fields so the loader and consuming code stay predictable.

## Manifest format

Bundles are discovered from `bundle.toml` files.

Example:

```toml
[bundle]
id = "T1-PROF-RANGER"
display_name = "Ranger Profession"
version = "1.0.0"
tier = 1

[requires]
engine = ">=1.0.0"
free_bundles = ["T0-CRAFTING-INFRA", "T0-OUTDOORSMANSHIP", "T0-SPELL-CIRCLES"]
paid_bundles = []
optional_bundles = ["T1-ZONE-CROSSING"]

[provides]
professions = ["ranger"]
spell_circles = ["nature"]

[entrypoint]
register_callable = "world.bundles.ranger.register"
```

Required manifest fields:

- `bundle.id`
- `bundle.display_name`
- `bundle.version`
- `entrypoint.register_callable`

Supported dependency fields:

- `requires.engine`
- `requires.free_bundles`
- `requires.paid_bundles`
- `requires.optional_bundles`

## Loader behavior

`BundleLoader` performs four jobs:

1. Discovery: scans `world/bundles/`, repo-root `bundles/`, and any configured `settings.BUNDLE_PATHS`
2. Validation: checks duplicate bundle IDs, engine version compatibility, conflicting `provides`, missing required dependencies, and dependency cycles
3. Ordering: topological sort over required bundle dependencies
4. Loading: imports each bundle's `register_callable` and passes a `BundleContext(manifest, registries)` object

Failure handling:

- Duplicate IDs, conflicting `provides`, and cycles are validation errors.
- Missing required dependencies skip the dependent bundle instead of crashing the engine.
- Missing optional dependencies do not block load.
- A bundle registration exception is captured in the load report; the engine continues.

## Boot integration

`server/conf/at_server_startstop.py` now calls `engine.bundles.boot.boot_bundles()` during `at_server_init()`.

Boot sequence for DRG-022.5:

1. Reset all registries.
2. Populate `stat_registry` from `public.canon_stats` via `connect_direlore()`.
3. If that query fails, populate `stat_registry` from a compatibility fallback and log a warning.
4. Discover and load any bundle manifests.
5. Keep registries read-only for the rest of the process lifetime.

Hot reload is not implemented in v1. Adding/removing bundles requires restart.

## Graceful degradation

Consumers must prefer `get()` when missing content is expected or survivable.

Examples:

- Profession lookup for optional content: `profession_registry.get("moon_mage")`
- Zone lookup for optional exits: `zone_registry.get("riverhaven")`
- Spell circle lookup for optional profession content: `spell_circle_registry.get("nature")`

Consumers must use `require()` only when absence is a true invariant break.

Examples:

- A loaded bundle trying to look up one of its own required local definitions
- A character object resolving a profession after the profession system is fully migrated and no fallback path remains

Current graceful-absence guarantees:

- Engine boots with zero discovered bundles.
- Missing required dependencies skip bundles cleanly.
- Missing optional dependencies do not block load.
- Missing registry keys return `None` through `get()`.

## Stats proof of concept

`stat_registry` is the first migrated substrate registry.

Loaded source:

- `public.canon_stats` via `world.systems.canon_seed.connect_direlore`

Fallback source:

- `engine/bundles/stat_registry.py:FALLBACK_STAT_DEFINITIONS`

Current Character integration:

- `typeclasses/characters.py` now derives its default stat map from `stat_registry`
- `Character.ensure_stat_defaults()` backfills from registry defaults
- `Character.set_stat()` validates names through `stat_registry`

Compatibility note:

- The canonical 5432 stat set is `strength`, `reflex`, `agility`, `charisma`, `discipline`, `wisdom`, `intelligence`, `stamina`, `concentration`, and `aura`
- Older engine-only stat names should not be treated as canon. They can be bridged temporarily only where needed for compatibility during later migrations.

## Skills migration follow-up

`skill_registry` is the second migrated substrate registry.

Loaded source:

- `public.canon_skills` via `world.systems.canon_seed.connect_direlore`

Fallback source:

- `engine/bundles/builtin_skills.py:FALLBACK_SKILLS`

Current integration:

- `engine/bundles/boot.py` populates `skill_registry` before bundle discovery
- `world/systems/skills.py` exposes registry-backed helpers for canonical lookup, group listing, and pulse-group lookup
- `engine/services/pulse_service.py` now uses registry metadata instead of `SKILL_GROUPS`
- `commands/cmd_experience.py` prefers registry display names when present

Current DireLore caveat:

- `canon_skills` currently contains 63 rows, but many remain unresolved placeholder names such as `unknown_0`
- `canon_skills` does not yet expose a reliable canonical group column beyond sparse `skillset` values
- DRG-023 wires the table exactly as it exists today and marks unresolved rows with `resolved = False`; downstream canon-cleanup dispatches can improve grouping once DireLore data is richer

Compatibility note:

- Legacy runtime skill names remain valid through explicit helper resolution rather than being baked into the registry as fake canon entries
- The old `SKILL_GROUPS` pulse-order table was replaced with registry-backed pulse metadata plus legacy pulse-group defaults for existing engine skills

## Combat integration follow-up

DRG-024 did not add a separate combat-content registry. Combat remains a Tier 0 engine substrate, but it now consumes canonical skill identity through the same registry-backed helpers introduced in DRG-023.

Current integration:

- `engine/services/combat_service.py` passes canonical skill names such as `brawling`, `large_blunt`, or `evasion` into the combat resolver through the existing context surface
- `domain/combat/resolution.py` resolves OF and EDF from actor stats plus the current skill values; it does not hardcode profession-specific combat identities
- the resolver preserves the legacy `AttackResolution.details` contract so higher layers can migrate incrementally without inventing a parallel combat API

Boundary note:

- bundle-facing registries own combat metadata identity when skills, items, or future profession abilities need registration
- the combat math itself remains engine-owned Tier 0 substrate code under `domain/combat/` and `engine/services/combat_service.py`
- follow-up bundle work should register profession/race/item modifiers through stable engine APIs rather than embedding new combat math in bundle code

## Worked example: free Ranger bundle

Expected future structure:

```text
world/bundles/ranger/
├── bundle.toml
└── __init__.py
```

`bundle.toml` would declare `T1-PROF-RANGER`, required Tier 0 bundles, and `professions = ["ranger"]`.

The registration entry point would do only registry work:

```python
def register(context):
    context.registries.profession_registry.register(
        "ranger",
        {
            "id": "ranger",
            "display_name": "Ranger",
            "bundle_id": "T1-PROF-RANGER",
            "tier": 1,
            "canon_profession_id": 5,
        },
        source_bundle=context.manifest.bundle_id,
    )
```

The engine should consume that registry entry through services, not by importing `world.systems.ranger` directly.

## Worked example: paid Moon Mage bundle

Expected future structure:

```text
bundles/moon_mage/
├── bundle.toml
└── __init__.py
```

`bundle.toml` would declare `T2-PROF-MOONMAGE`, required magic/planetary substrate bundles, and `professions = ["moon_mage"]`.

If that bundle is not installed:

- `profession_registry.get("moon_mage")` returns `None`
- chargen can hide Moon Mage from selection
- any zone/shop/help text that references Moon Mage must degrade gracefully instead of crashing

## Migration guidance for downstream dispatches

Use this sequence when moving a hardcoded surface into bundle registration:

1. Keep the consuming service/typeclass path authoritative.
2. Move content identity and metadata into the appropriate registry.
3. Add a bundle manifest and registration callable.
4. Replace direct imports and profession/race/zone string branching with registry lookups.
5. Prefer `get()` for optional content and explicit degradation.
6. Add focused tests for missing-bundle behavior before removing old hardcoded fallbacks.

## Changelog requirement

At the end of each Phase 4 task, append the outcome to `CHANGELOG.md` so the repo maintains a human-readable historical trail alongside the roadmap and audit docs.