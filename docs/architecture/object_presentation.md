# Object Presentation

MT-516 defines how DireEngine presents and resolves object identity when many
similar-looking items are present.

MT-516-mixed extends the same resolver contract to nearby characters and NPCs
without merging character presentation into the object aggregation path.

## Core Rules

1. Storage stacking is for fungible items only.
2. Stacking is identity-based, not category-based.
3. Display aggregation is broader than storage stacking.
4. Aggregation groups by the player-visible object label.
5. Exact counts are used in v1.
6. Non-stackable ambiguous object targets prefer the newest matching arrival.
7. Mixed character/object commands use the same ordinal resolver vocabulary.
8. NPC display remains on the character listing path unless a future dispatch
	explicitly changes that presentation rule.

## Targeting Syntax

Object-targeting commands that consume the MT-516 resolver accept three explicit
selection forms:

- English ordinals: `first leaf`, `third corpse`, `one hundred third dagger`
- Numeric-suffix ordinals: `1st leaf`, `13th dagger`
- Numeric positional: `1.leaf`, `13.dagger`

The resolver also accepts `other <name>` as shorthand for the second matching
object after newest-first ordering.

The same selection forms apply to migrated nearby character and NPC commands:

- `attack first goblin`
- `whisper 2nd guard = stay sharp`
- `study anatomy 3.goblin`

When the player does not specify a position, object resolution defaults to the
 newest matching object in scope.

When migrated character/NPC commands do not specify a position, resolution also
defaults to the newest matching visible character in scope.

## Aggregation

Render-time aggregation is used for:

- room object listings via `Room.get_display_things()`
- `inventory`
- wearable container displays
- gem pouch displays
- fish string displays

Aggregation is computed at render time and does not alter database identity for
non-stackable objects.

Examples:

- two separate `dagger` objects render as `daggers (2)`
- one stackable `useful leaf` object with quantity `15` renders as `useful leaves (15)`

## Stackables

Stackable items merge on receive at object/container and character inventory
boundaries.

Current v1 stackability rule:

- explicit `db.stackable = True` always stacks
- otherwise, items with `item_type` `raw_resource` or `foraged_material` stack

Current forage-category roster observed in `world/builder/content/forage_catalog.yaml`:

- `fauna_part`
- `flora`
- `food`
- `healing_herb`
- `indoor_misc`
- `mineral_misc`
- `mushroom`
- `seashell`
- `wood`

The runtime stackability rule is intentionally narrower than the full catalog
roster. It uses explicit `stackable` metadata or known fungible item types,
without changing forage generation logic.

## Split Semantics

Partial stack drops are supported in v1 with leading-quantity syntax:

- `drop 5 leaves`

This is distinct from positional targeting:

- `drop 2.leaf` means select the second matching leaf object

When a partial stack is dropped, a new object is created with copied attributes
and the requested quantity, while the held stack keeps the remainder.

## Resolver Scope

The centralized resolver now supports these scope families:

- `inventory` for carried objects
- `room` for nearby non-character, non-exit objects
- `characters` for nearby visible characters and NPCs, excluding the caller
- `npcs` for nearby visible NPCs only

Combined scopes are ordered. The first scope with a match wins.

Example:

- `resolve_target("goblin", scopes=("characters", "room"))`
- `resolve_target("dagger", scopes=("characters", "room"))`

This lets mixed commands use one resolution call without having to know whether
the noun refers to a nearby character or a nearby object.

The centralized MT-516 resolver is now used by the migrated object-only commands
and the migrated nearby mixed character/object commands. Corpse-specialized and
global/admin search flows may still use narrower command-local logic when that
is the safer fit.

## Character Listing

Room characters and NPCs continue to render through `Room.get_display_characters()`.

Current MT-516-mixed decision:

- NPC aggregation is deferred.
- Characters and NPCs still list individually.
- Object aggregation remains confined to `Room.get_display_things()` and other
	object/container listing surfaces.

Rationale:

- NPCs carry combat, interaction, and awareness state.
- The codebase already separates character listing from object listing.
- Changing NPC presentation is a content/design decision, not a required part of
	extending ordinal targeting to character scope.

## Slippy Reference Adaptation

Adapted patterns from `docs/references/slippy_target_resolver_2026-05-01.md`:

- newest-first ordering
- ordinal and positional selection
- possessive/article normalization
- `other` shorthand

Not adopted as generic v1 behavior:

- full shared character/NPC/object aggregation
- embedded container parsing as a global resolver concern
- broad replacement of all Evennia search behavior