# Mana Systems Excavation

Source: live `direlore` PostgreSQL on `127.0.0.1:5432`, database `direlore`, queried read-only on 2026-04-12.

Primary query path used:

`sections -> raw_pages -> canon_spells / canon_abilities / canon_professions -> profession_* -> entities / facts`

Contract note:

- The active DireLore overlay explicitly prefers `sections` and `raw_pages` over sparse canonical tables for mechanics work.
- That preference was necessary here. Most of the real mana-system detail lives in raw section text, not in normalized resource tables.

## 1. TABLE MAP

### High-signal tables actually carrying mana-system evidence

`public.sections`

- Columns: `id`, `url`, `heading`, `content`, `section_tag`
- Purpose: primary high-signal mechanics surface.
- Evidence found here: attunement behavior, mana spectrum, room-based mana, environmental modifiers, spell prep syntax, cyclic-spell drain behavior, cambrinth formulas, perceive timing, devotion regen item pulses, empath shock, profession-specific perception rules.

`public.raw_pages`

- Columns: `url`, `title`, `raw_html`, `raw_text`, `fetched_at`, `content_hash`
- Purpose: page-level fallback when section extraction is sparse or truncated.
- Evidence found here: full spell metadata blocks for `Persistence of Mana`, `Eylhaar's Feast`, `Moon Mage attunement`, `Devotion Regeneration`, `Harness Regeneration` redirect behavior.

`public.page_metadata`

- Columns: `url`, `page_type`, `title`, `categories`, `processed`, `priority_level`, `priority_group_id`, `priority_created_at`
- Purpose: page classification and retrieval support.
- Mana-system value: secondary only. Useful for organizing page families, not for formulas.

`public.canon_spells`

- Columns: `id`, `name`, `spell_type`, `signature`, `cyclic`, `version_label`, `version_family`, `lifecycle_status`, `source_entity_id`, `confidence`, `created_at`, `spell_slots`, `mana_type`, `valid_spell_target`, `difficulty`, `prerequisites`, `effect`, `skill_range_min_max`
- Purpose: partial normalized spell metadata.
- Mana-system value: strong for spell taxonomy and partial cost model.
- Weakness: many rows still have `NULL` mana type / incomplete profession linkage.

`public.canon_abilities`

- Columns: `id`, `name`, `ability_type`, `tree`, `version_label`, `version_family`, `lifecycle_status`, `source_entity_id`, `confidence`, `created_at`, `slot_cost`, `use_cost`, `requirements`, `ability_skill`, `difficulty`, `effect`, `messaging`
- Purpose: normalized non-spell ability metadata.
- Mana-system value: partial only. Useful for khri-/ability-style cost fields, but not the main mana model.

`public.canon_professions`

- Columns: `id`, `name`, `description`, `guild`, `role`, `source_entity_id`, `confidence`, `created_at`
- Purpose: profession identity layer.
- Mana-system value: weak alone; profession-specific mana behavior mostly remains in raw pages.

`public.profession_spells`

- Columns: `id`, `profession_id`, `spell_id`
- Purpose: intended spell-to-profession link table.
- Actual state: effectively placeholder-level for this topic. Querying major magic professions returned `1` row each, which is not credible coverage for real spellbooks.

`public.profession_abilities`

- Columns: `id`, `profession_id`, `ability_id`
- Purpose: intended ability-to-profession link table.
- Actual state: effectively unusable for mana excavation. Queries for `Empath`, `Cleric`, `Moon Mage`, and `Warrior Mage` returned `NULL` ability arrays.

`public.entities`

- Columns: `id`, `name`, `normalized_name`, `entity_type`, `source_url`, `confidence`, `is_promoted`, `entity_subtype`
- Purpose: derived entity catalog.
- Mana-system value: corroborative only.

`public.facts`

- Columns: `id`, `entity_id`, `key`, `value`, `source_url`, `confidence`, `normalized_key`, `normalized_value`, `provenance`
- Purpose: normalized fact store.
- Mana-system value: corroborative only; not sufficient as the primary source.

### Tables that look relevant but did not materially carry the mana model

`public.canon_mechanics`

- Columns: `id`, `mechanic_type`, `name`, `description`, `structured_data`, `source_entity_id`, `confidence`, `created_at`
- Intended purpose: normalized mechanics.
- Actual result for mana-related queries: mostly noise such as items with cambrinth in the name, not a coherent mana-system model.

`public.mechanic_rules`

- Columns: `id`, `mechanic_id`, `rule_type`, `rule_text`, `numeric_value`
- Intended purpose: normalized rule fragments.
- Mana-system value: `NOT FOUND IN DB` as a usable, comprehensive mana rules layer.

`public.mechanic_entity_links`

- Columns: `id`, `mechanic_id`, `entity_id`, `entity_type`
- Intended purpose: attach mechanics to entities.
- Mana-system value: `NOT FOUND IN DB` as a useful connected graph for mana resources.

## 2. RESOURCE MODEL

### Core resource layers reconstructed from the DB

`Environmental mana`

- Represented in `sections` and `raw_pages`, not in a normalized room-resource table.
- Four primary real mana realms are modeled: `Holy`, `Life`, `Elemental`, `Lunar`.
- `Necromantic mana` is described as a perceived amalgam, not a true independent mana realm.
- For most guilds, available mana is room-based plus cyclic/environmental modifiers.
- Moon Mages are the major exception: their mana is global/time-based rather than room-based.

`Attunement pool`

- Represented textually as the caster's usable mana pool.
- The DB explicitly says attunement functions like magical fatigue.
- It is spent by `HARNESS`, `CAST`, and `CHARGE`-style actions.
- It is improved by Attunement skill and by profession/environment modifiers.
- Exact pool-size formula: `NOT FOUND IN DB`.

`Held / harnessed mana`

- Separate from total attunement.
- Spells can be prepared at a chosen mana amount, then supplemented by harnessed mana and cambrinth discharge.
- Cyclic spells consume held mana continuously unless redirected to cambrinth or, with feats, directly to attunement.

`Spell preparation amount`

- Represents the player-chosen mana input into a spell pattern.
- This is the main channeling/input layer of the casting system.
- Spells expose min/max prep ranges in raw spell pages and category summaries.

`Cambrinth stored energy`

- Cambrinth does not store raw ambient mana in the strictest sense; it stores the energy released by manipulating mana.
- It is a mobile external buffer.
- It can be charged, linked, partially invoked, leaked over time, and used to sustain cyclic spells.

### Companion profession resources connected to mana but not identical to mana

`Cleric devotion`

- Separate pool-like resource.
- Increases effective access to Holy mana in a room.
- Has its own regeneration items.
- Conceptually represents divine favor / conduit capacity rather than generic mana.

`Spirit health`

- Separate resource with direct magic interactions.
- Cleric spell `Eylhaar's Feast` explicitly converts spirit health into attunement, vitality, or fatigue.
- This makes spirit health a fuel-adjacent reservoir for Clerics.

`Empathic shock`

- Not mana, but a profession-specific anti-violence impairment resource/state.
- It drains over time while online unless the Empath is completely insensitive.
- It suppresses or weakens empathy- and healing-related systems, including several mana-adjacent abilities/spells.

`Life essence`

- Perceived by Empaths through `PERCEIVE HEALTH`.
- Used as the conceptual target of diagnosis/healing/construct-detection, but not exposed as a normalized numeric player resource table.

### Storage model conclusion

- Persistent player resource tables for `mana`, `attunement`, `devotion`, `shock`, `spirit`, or `held mana`: `NOT FOUND IN DB`.
- The DireLore DB is preserving the engine's thinking as rules text, spell metadata, and category summaries, not as live runtime state tables.

## 3. FORMULAS (EXPLICIT)

### Exact formulas found

`Cambrinth charge roundtime`

```text
RT = 2 + floor( CHARGE / (5 + floor(Arcana_Ranks / 100)) )
```

Variables:

- `RT` = charge roundtime in seconds
- `CHARGE` = mana amount being added in that charge action
- `Arcana_Ranks` = user's Arcana skill ranks

Additional rule:

```text
If cambrinth is not full and attempted_charge > remaining_capacity:
    roundtime is based on remaining_capacity actually added

If cambrinth is already full and you overcharge it:
    RT = 5
```

`Worn cambrinth Arcana requirement`

```text
Arcana_Ranks_Required = 100 + 2 * Mana_Capacity
```

Variables:

- `Mana_Capacity` = max mana capacity of the worn cambrinth item

`Devotion regeneration item pulse`

```text
Every 60 seconds:
    if Devotion < 100%:
        Devotion += 1% of Max_Devotion
```

Additional rule:

- Item must be worn and turned on.
- Effect stacks with other devotion regeneration items.

`Perceive / Concentrate roundtime scaling`

```text
Default perceive RT range = 8 to 12 seconds

For every 60 Attunement ranks up to 300:
    min_RT -= 1 second
    max_RT -= 1 second

At 300 ranks:
    perceive RT range = 3 to 7 seconds

For every 60 Attunement ranks after 300:
    max_RT -= 1 second

At 540 ranks:
    perceive RT = 3 seconds always
```

`Attunement training timer for most guilds`

```text
Experience from room mana perception:
    max 1 award per room per 60 seconds
```

`Moon Mage attunement training timer`

```text
PERCEIVE MANA training timer for Moon Mages ≈ 2 minutes
```

`Spell stance allocation`

```text
For Potency, Duration, Integrity:
    each facet can be set from 70% to 130%
```

If one facet does not apply:

```text
Power is distributed according to the ratio of the remaining facets.
```

Example preserved by the DB:

```text
Duration = 130%
Integrity = 85%
Potency = 85%

For a TM spell, Duration does not apply.
Integrity : Potency = 85 : 85 = 1 : 1
```

`Eylhaar's Feast conversion input`

```text
Input_Percentage = 1..99
Input is a percentage of Max_Spirit_Health
```

Conversion output:

```text
Spirit_Health -> Attunement
Spirit_Health -> Vitality
Spirit_Health -> Fatigue
```

Exact conversion ratio from spirit to target resource: `NOT FOUND IN DB`.

### Semi-explicit math / threshold systems

`Attunement level thresholds`

The DB preserves named thresholds at:

```text
0, 5, 10, 13, 20, 25, 33, 40, 100
```

Interpretation:

- The table is qualitative messaging over an underlying percentage/strength ladder.
- `100` = complete attunement.
- Values above `100` are possible and described as above-normal attunement.

`Moon Mage planetary perception bands`

The DB preserves four qualitative planet-range buckets:

```text
barely within
within
well within
deep within
```

Exact Attunement-rank cutoffs for those ranges: `NOT FOUND IN DB`.

`Cambrinth leakage`

```text
Stored_Energy(t + X) = 0.5 * Stored_Energy(t)
```

Interpretation:

- Cambrinth uses half-life decay.
- The page explicitly says the standing energy drops by `50%` every `X` time unit.
- Exact `X`: `NOT FOUND IN DB`.

`Cyclic drain scaling`

```text
Mana_Drain_Per_Pulse = f(Prepared_Mana)
```

The DB explicitly says:

- cyclic spells drain held mana periodically
- prep amount controls how much mana is pulled per pulse

Exact function `f`: `NOT FOUND IN DB`.

`Cleric ALIGN skill modifier`

```text
Two skills: +15%
Three skills: -15%
```

Immortal-specific skill mapping: `NOT FULLY FOUND IN DB` in the surfaced pages.

### Exact formulas the DB clearly implies should exist, but did not expose

`Attunement pool size formula`

```text
NOT FOUND IN DB
```

## Structured Spell Migration Ledger

Healing migration map:

- `empath_heal` -> new structured healing handler
- `cleric_minor_heal` -> new structured healing handler
- other healing spells -> legacy spell resolution

Current rule:

- The healing family now uses `SpellEffectService` when a healing spell exists in the structured registry.
- New healing spells must register into the structured handler path instead of adding logic to legacy `Character.resolve_*` branches.

Next family choice:

- `augmentation` -> selected as the next migrated family because it is self-targeted, state-only, and lower-coupling than targeted damage.
- `warding` -> selected as the next migrated family because it reuses the existing `warding_barrier` state, has no contest math, and avoids a parallel defensive storage model.

Migration state:

- Migrated families: `healing`, `augmentation`, `warding`
- Still legacy: remaining `utility`, `targeted_magic`, `debilitation`, cyclic-specific effects

## Targeted Magic Migration Note

Targeted magic seam:

- attack contest function: `engine/services/spell_contest_service.py::SpellContestService.resolve_targeted_magic`
- damage application function: `engine/services/state_service.py::StateService.apply_damage`
- ward absorption hook: `typeclasses/characters.py::apply_ward_absorption`

Contested-family rules:

- `SpellEffectService` routes only.
- Contest resolution owns hit or miss.
- `StateService` owns HP mutation when damage gets through.
- Warding absorbs on the authoritative barrier path before damage is applied.

Migration state:

- Migrated targeted spell(s): `flare`
- Migrated families: `healing`, `augmentation`, `warding`, `targeted_magic` (single-target bolt seam)
- Still legacy: remaining `utility`, `debilitation`, cyclic-specific effects, room-wide and remaining targeted spells

## Debilitation Migration Note

Debilitation seam:

- contest function: `engine/services/spell_contest_service.py::SpellContestService.resolve_debilitation`
- state mutation function: `engine/services/state_service.py::StateService.apply_debilitation_effect`
- authoritative status container: `Character.db.states["active_effects"]["debilitation"]`
- duration tick path: `typeclasses/characters.py::process_magic_states()` via `StateService.tick_active_effects`

Contested-family rules:

- `SpellEffectService` routes only.
- Debilitation reuses the spell contest path rather than defining a second contest system.
- `StateService` owns debilitation application and overwrite behavior.
- Debilitation durations tick on the existing magic-state lifecycle path.

Migration state:

- Migrated debilitation spell(s): `daze`, `slow`
- Migrated families: `healing`, `augmentation`, `warding`, `targeted_magic`, `debilitation`
- Still legacy: remaining `utility`, cyclic-specific effects, room-wide spells, and unmigrated legacy debilitation definitions

## Cyclic Migration Note

Cyclic seam:

- routing function: `engine/services/spell_effect_service.py::SpellEffectService._apply_cyclic_spell`
- contested application function: `engine/services/spell_contest_service.py::SpellContestService.resolve_cyclic_application`
- state mutation function: `engine/services/state_service.py::StateService.apply_cyclic_effect`
- authoritative cyclic container: `Character.db.states["active_effects"]["cyclic"]`
- upkeep tick path: `typeclasses/characters.py::process_magic_states()` via `StateService.process_cyclic_effects`

Cyclic rules:

- Migrated cyclic spells do not use `active_cyclic` as their authoritative state.
- Cyclic upkeep runs on the existing magic-state lifecycle path rather than a new ticker.
- `StateService` owns cyclic start, removal, tick effects, and collapse handling.
- `ManaService.consume_mana()` is the per-tick upkeep gate for migrated cyclic spells.

Migration state:

- Migrated cyclic spell(s): `regenerate`, `wither`
- Targeted cyclic application reuses contest logic before upkeep starts.
- Legacy `active_cyclic` / `process_cyclic()` runtime handling has been retired.
- Any remaining legacy spell metadata still tagged `cyclic` is blocked at cast time until migrated to the structured registry.

## AoE + Environment Migration Note

AoE seam:

- routing function: `engine/services/spell_effect_service.py::SpellEffectService._apply_aoe_spell`
- target filter helper: `engine/services/spell_effect_service.py::SpellEffectService.get_valid_aoe_targets`
- per-target contest path: `engine/services/spell_contest_service.py::SpellContestService.resolve_targeted_magic`
- mutation owner: `engine/services/state_service.py::StateService.apply_damage`

Environment seam:

- room context accessor: `engine/services/mana_service.py::ManaService.get_environmental_modifier`
- cast-time integration: `engine/services/mana_service.py::_get_effective_env_mana` and `_cast_spell`
- cyclic upkeep integration: `engine/services/state_service.py::StateService.process_cyclic_effects`

AoE rules:

- AoE is routing only; each target resolves independently through the existing targeted pipeline.
- AoE loops are O(n) over valid targets and must not introduce nested target scans.
- Wards, debuffs, and buffs apply per target through the same contest and damage rules as single-target spells.

Environment rules:

- Room state is context only and is never mutated by spell execution.
- `room.db.environmental_mana` is a multiplier layered on top of base room mana, not a second authority system.
- Cast-time debug traces now record `environmental_mana_modifier` and `effective_env_mana`.

Migration state:

- Migrated AoE spell(s): `arc_burst`
- Migrated room-cyclic spell(s): `storm_field`
- Environment-aware structured families: `targeted_magic`, `aoe`, `cyclic`

## Runtime Boundary Hardening Note

Character/runtime seam:

- prepare path: `typeclasses/characters.py::prepare_spell()`
- cast path: `typeclasses/characters.py::cast_spell()`
- structured branch gate: `typeclasses/characters.py::resolve_spell()` via `_resolve_structured_spell()`

Runtime rules:

- Migrated families must resolve through the structured branch before any legacy category resolver.
- Invalid single-target casts must fail before contest/effect execution.
- Missing learned-state must fail before mana preparation or effect execution.
- Dev-only structured spell traces must report `legacy_fallback=False` for migrated families.

Runtime coverage:

- `tests/services/test_character_spell_runtime.py` covers healing, augmentation, warding, targeted magic, debilitation, invalid-target failure, missing-learned-state failure, no-legacy-fallback checks, effect-container isolation, and tick-load correctness.

## Interaction Hardening Ledger

Structured families now covered together:

- `healing`
- `augmentation`
- `warding`
- `targeted_magic`
- `aoe`
- `debilitation`
- `cyclic`
- `utility`

Still legacy or partially legacy:

- deprecated blocked spell ids that are intentionally unregistered until a structured design exists

Drift audit:

- Commands: `cmd_prepare.py` and `cmd_cast.py` still delegate to Character runtime methods; no new direct spell-effect or direct debuff logic was introduced in command handlers during this phase.
- Legacy table: `typeclasses/spells.py` has been retired; migrated ids now live only in the structured registry and deprecated unsupported ids fail closed.
- AoE loops in live spell code remain single-pass over targets (`SpellEffectService._apply_aoe_spell` and `StateService.process_cyclic_effects` room branch).
- Structured healing now routes HP restoration through `StateService.apply_healing` instead of mutating HP directly inside `SpellEffectService`.

## Utility + Room Alignment Note

Global rules:

- DO NOT add new spell mechanics.
- DO NOT add new state systems.
- DO NOT introduce new handlers unless strictly required for routing.
- ALL migrated spells must use `SpellRegistry`, `SpellEffectService`, and `StateService` when mutation exists.
- Legacy execution paths must fail closed after migration.

Inventory freeze:

- Migrated room-wide spell ids: `radiant_burst`, `shared_guard`
- Migrated utility spell ids: `glimmer`, `cleanse`
- Migrated remaining legacy definitions on existing structured families: `hinder`, `shielding`
- Deprecated blocked legacy spell id: `radiant_aura` now fails closed as unregistered until a real structured design exists.

Dependency audit:

- No migrated utility or room spell path uses command-level spell logic.
- No migrated utility or room spell path uses direct HP mutation outside `StateService`.
- No migrated utility or room spell path uses custom timers or schedulers.
- Room remains read-only context for target discovery and environmental mana reads.

`Attunement regeneration rate formula`

```text
NOT FOUND IN DB
```

The DB only preserves qualitative guidance:

```text
The more harness/attunement you have used, the faster it returns.
```

`Spell mana-cost to final output formula`

```text
NOT FOUND IN DB
```

The DB preserves prep ranges, difficulty bands, spell stances, and cost categories, but not a final cast-power equation.

`Empath healing-transfer formula`

```text
NOT FOUND IN DB
```

The DB confirms transfer-linked healing systems exist, but not an exact wound-to-empath or vitality-transfer equation.

## 4. PULSE SYSTEM

### Pulse / timer surfaces directly preserved

`Perception training timer`

- System: Attunement learning
- Trigger: `PERCEIVE`, `CONCENTRATE`, `POWER`
- Interval: `60 seconds` per room for most guilds
- Effect: grants attunement experience once per room per timer window

`Moon Mage perception timer`

- System: Moon Mage attunement learning
- Trigger: `PERCEIVE MANA`
- Interval: approximately `2 minutes`
- Effect: grants Moon Mage attunement experience independent of room movement

`Devotion regeneration pulse`

- System: Cleric devotion recovery via items
- Trigger: worn active devotion-regeneration item
- Interval: `60 seconds`
- Effect: `+1% Max_Devotion` if below full

`Cyclic spell maintenance pulse`

- System: ongoing spell upkeep
- Trigger: active cyclic spell
- Interval: pulse exists, exact timing `NOT FOUND IN DB`
- Effect: drains held mana, cambrinth mana, or direct attunement depending on setup/feats

`Spell pulse payloads`

- Some spells are explicitly typed as `pulse damage` or `pulse to group`
- This indicates a repeated-application engine pattern beyond simple duration spells
- Exact pulse interval and backend scheduler definition: `NOT FOUND IN DB`

### Pulse map

```text
Perceive timer (60s, per room)
    -> Attunement learning
    -> no resource change except experience

Moon Mage perceive timer (~120s)
    -> Moon Mage attunement learning
    -> no direct mana change, experience only

Devotion item pulse (60s)
    -> Devotion pool
    -> +1% max devotion if below full

Cyclic spell pulse (interval NOT FOUND)
    -> held mana / cambrinth / direct attunement
    -> upkeep drain

Pulse-damage / pulse-to-group spells (interval NOT FOUND)
    -> damage / group effect application
    -> repeated spell effect resolution
```

### Missing scheduler detail

The DB proves that pulse-driven systems exist, but it does not expose a normalized engine scheduler table such as:

```text
pulse_name
frequency_seconds
subscribed_systems
resource_delta_formula
```

That layer is `NOT FOUND IN DB`.

## 5. PROFESSION DIFFERENCES

### Empath

Resource usage model:

- Primary realm: `Life mana`
- Normal room-based attunement model applies
- Companion systems: `life essence`, `empathic shock`, empathy-linked healing systems

Unique mechanics found:

- `PERCEIVE HEALTH` and diagnosis/life-force sensing
- remote diagnosis requires persistent link
- `Circle of Sympathy`: creates a tree that allows Empaths to share attunement
- `Embrace of the Vela'Tohr`: remote healing via conjured plant
- `Absolution`: allows Empath to attack undead without shock
- `Regenerate` exists in Empath spell lists

Shock interactions:

- shock is caused by direct, deliberate harm to living beings
- shock automatically drains while online unless completely insensitive
- complete insensitivity disables `healing others`, `link`, `perceive health`, `manipulate`, `shift`, `Guardian Spirit`, `Heart Link`, `Regenerate`, `Circle of Sympathy`, `Embrace of the Vela'Tohr`
- reduced-power healing still works for `Heal Wounds`, `Heal Scars`, `Heal`, `Vitality Healing`, `Flush Poisons`, `Cure Disease`

Math-like behavior:

```text
Shock sharing:
    recipient_shock_after_take ≈ 0.5 * remaining_shock
    source_shock_after_take ≈ 0.5 * remaining_shock
```

Exact internal shock scalar: `NOT FOUND IN DB`.

### Cleric

Resource usage model:

- Primary realm: `Holy mana`
- Holy mana access is gated by a supernatural connection and amplified by `Devotion`
- Companion systems: `Devotion`, `Spirit health`, `Communes`, `Align`, `Infusion`

Unique mechanics found:

- Clerics have access to more room mana depending on devotion
- `Eylhaar's Feast`: converts spirit health into attunement, vitality, or fatigue
- `Persistence of Mana`: `+Attunement skill`, `+Attunement pool regeneration`
- `Auspice`: `+Spirit health`, `+Spirit health regeneration`
- `ALIGN <immortal>`: `+15%` to two skills, `-15%` to three skills

Ritual model:

- Cleric ritual spells explicitly require ritual focus support
- `Persistence of Mana` is a ritual spell with `150-700` prep and `30-90` minute duration
- Active `Persistence of Mana` reduces harness time by `1` second, minimum `1` second, or `2` total if using `INFUSE`

Detailed mechanics for `Communes` and `Infusion`:

```text
NOT FOUND IN DB in a usable structured or section-backed form for this pass
```

### Warrior Mage

Resource usage model:

- Primary realm: `Elemental mana`
- Normal room-based attunement model applies, heavily weather-sensitive
- Companion system: elemental alignment/opposition

Unique mechanics found:

- `PERCEIVE ELEMENTS <element>` and `PERCEIVE ELEMENTS ALL`
- requires minimum `42` Attunement ranks
- `ALIGN (OPPOSITION) <element>` changes elemental stance
- category summary shows explicit elemental mana interactions such as `Ethereal Fissure: +Mana level, room-wide elemental only`
- Warrior Mage spellbooks include cyclic upkeep examples (`Aether Cloak`, `Electrostatic Eddy`) and infusion metamagics

Environmental dependency:

- Elemental mana peaks in inclement weather and storms
- the profession is explicitly given tools to inspect elemental environmental efficacy

### Moon Mage

Resource usage model:

- Primary realm: `Lunar mana`
- fundamentally different from room-based mana systems
- mana varies by time/celestial state, not by location
- subchannels are spellbook-specific: `Perception`, `Psychic Projection`, `Moonlight Manipulation`, `Enlightened Geometry`

Unique mechanics found:

- `PERCEIVE MOONS`, `PERCEIVE PLANETS`, `PERCEIVE MANA`, `PERCEIVE TELEOLOGIC SORCERY`, `PERCEIVE WATCHERS`
- can detect magic users, active spells, held mana, and moonbeam/watcher effects
- planetary bonuses are cumulative across perceivable planets
- `ALIGN MOON <moon>` sets default moon target for moon-dependent spells
- `ALIGN SPLIT`, `ALIGN TRANSMOGRIFY`, `ALIGN MOONBLADE` add prediction and storage behavior
- Moon Mage spell summary shows ritual and metamagic systems tightly bound to celestial conditions, for example `Braun's Conjecture`, `Invocation of the Spheres`, `Iyqaromos Fire-Lens`

Training difference:

```text
Moon Mage PERCEIVE MANA exp timer ≈ 2 minutes
```

This differs from the normal `60`-second per-room power-walking pattern.

### Other mana-using professions found in scope

`Bard`

- Uses `Elemental mana`
- preserved effect example: `Aether Wolves` decreases attunement pool regeneration

`Ranger`

- Uses `Life mana`
- `ALIGN <#>` uses some spirit health with Beseeches

`Paladin`

- Uses `Holy mana`
- Holy mana perception is confounded by soul state rather than devotion alone

`Necromancer`

- Perceives `Necromantic mana`, which the DB explicitly describes as not a true mana type but an unnatural composite perception

## 6. ENVIRONMENTAL EFFECTS

### Global environmental rules found

`Elemental mana`

```text
Peak: storms / inclement weather
Low: clear skies
```

`Holy mana`

```text
Peak: holy days / holidays
Low: points furthest from the nearest holy days
```

`Life mana`

```text
Peak: solstices
Low: equinoxes
```

`Lunar mana`

```text
Depends on:
    moon phase
    moon position above/below horizon
    moon distance from Elanthia
    conjunctions / oppositions / eclipses
    time of day
    weather

Peak tendency:
    clear weather
    night
```

`Arcane / Necromantic interactions`

```text
Arcane mana uses a fraction of available lunar mana as its modifier.

Necromantic mana uses Life + Elemental as primary sources,
with Lunar as a fluctuating bonus,
and Holy as a confounding influence.
```

### Room-layer rule

For non-Moon-Mage casters, the DB states:

```text
Available_Mana ≈ Room_Base_Mana + Attunement_Bonus + Mana_Type_Cycle_Modifier
```

Where:

- `Room_Base_Mana` = distinct mana level by room
- `Attunement_Bonus` = skill-driven adjacent-area/perk effect
- `Mana_Type_Cycle_Modifier` = weather / season / holy-day / celestial modifier by mana realm

Exact numeric equation: `NOT FOUND IN DB`.

### Profession/environment bindings

`Warrior Mage`

- can inspect elemental efficacy directly by element

`Cleric`

- devotion changes effective access to Holy mana in a room

`Moon Mage`

- breaks the room model entirely for core mana availability

## 7. ITEM SYSTEMS

### Cambrinth

Structure:

- external mana-adjacent energy store
- charge with mana-derived energy
- invoke to link and discharge into spellcasting
- focus to inspect contents
- release to break the link

Mechanics:

- can be invoked fully or partially
- partial invoke requires a skill check
- charging efficiency rises with Arcana, reaching full efficiency around `~200` ranks according to the page
- capacity scales with item size
- once charged with a mana realm, item is locked to that realm until retuned
- mixed-realm charging causes explosion/injury
- charged cambrinth leaks by half-life decay

Limitations:

- cannot replace the minimum ambient mana required to build the spell pattern in the first place
- can maintain cyclic spells after cast
- special areas can be completely magic-free and block even that

Typical capacities preserved by the DB:

```text
faceted orb: 144
orb: 108
wide armband: 48-50
held objects: 32
armband: 32
bracelet: 32
weapons: 8-24
anklet: 8-10
pendant: 8
ring/band: 4-6
```

### Dedicated cambrinth / raw channeling behavior

Found in raw prose on the Cambrinth page:

- cyclic spells normally drain held mana
- can be redirected to cambrinth by charging and invoking
- with `Dedicated Cambrinth Use`, cyclic upkeep can sit on cambrinth while freeing normal casting flow
- with `Raw Channeling`, cyclic spells can draw directly from attunement, freeing cambrinth for other spell boosts

Exact feat-table normalization: `NOT FOUND IN DB`.

### Ritual focus

Structure:

- external casting support item for ritual spells

Mechanics found:

- some ritual spells require ritual focus to cast successfully
- spellbook-specific focus can substitute without `Improvised Rituals`
- universal or realm-attuned focus requires `Improvised Rituals`

Limitations:

- spellbook or realm compatibility restrictions
- not a generic mana battery; it is a ritual-casting enabler / cost reducer

### Devotion regeneration jewelry

Structure:

- passive worn atmospheric items

Mechanics:

- pulse every `60s`
- restore `1%` of max devotion if below full
- stack with other such items

### Other item/external systems

`Mana storage items beyond cambrinth`

```text
NOT FOUND IN DB as a coherent generic system
```

`Energy buffers other than cambrinth / spirit-health conversion / ritual focus`

```text
NOT FOUND IN DB
```

## 8. GAP ANALYSIS

### A. What already exists in DireEngine's source model

- An environmental mana layer absolutely exists.
- A player attunement layer absolutely exists.
- Casting is clearly input/channeling based: prep amount, harnessed mana, cambrinth discharge, spell stance, and cyclic upkeep all depend on player-selected mana flow.
- Pulse/timer-based systems exist for learning, cyclic upkeep, and regeneration items.
- Profession-specific overlays exist on top of the shared mana model.
- External resource interaction exists through cambrinth, ritual focus, devotion items, and spirit-to-attunement conversion.

### B. What partially exists

- Spell metadata normalization exists in `canon_spells`, but coverage is partial.
- Profession linkage exists in schema, but not in trustworthy populated form.
- Companion resources like devotion and shock are represented in prose, not as normalized resource models.
- Cyclic and pulse systems are clearly present, but the scheduler/frequency layer is not normalized.
- Environmental effects are richly described, but not exposed as explicit numeric modifier tables.

### C. What is missing entirely

`NOT FOUND IN DB`:

- a normalized character-resource table for mana / attunement / devotion / shock / spirit
- exact attunement pool size formula
- exact attunement regeneration formula
- exact cyclic pulse interval
- exact cyclic drain-per-pulse formula
- exact healing-transfer math for Empaths
- a unified pulse scheduler table
- a unified environmental modifier table by mana type, region, room, and time
- a reliable normalized profession-to-spell / profession-to-ability graph

### D. What would conflict with the target model

Target model:

- environmental mana layer
- player attunement layer
- channeling/input-based casting
- pulse-based regeneration

Conflicts or caveats:

- Moon Mage mana is not room-local in the normal sense; it is global and celestial/time driven.
- Holy mana is not just environment plus attunement; Cleric access is additionally mediated by devotion / divine conduit status.
- Necromantic mana is not modeled as a clean fifth mana realm; it is an unnatural perceptual composite.
- Cambrinth cannot fully replace ambient mana because the caster still needs enough direct mana to construct the spell pattern.
- The real system is not mana-only. `Devotion`, `Spirit health`, and `Empathic shock` are separate resources/states that materially affect magical play.

### Storage recommendations from this excavation

- Add `resource_systems(resource_name, category, base_storage_mode, derived_from, profession_scope, source_url, confidence)`.
- Add `resource_formulas(resource_name, formula_type, formula_text, variables_json, exactness, source_url, confidence)`.
- Add `pulse_systems(pulse_name, interval_text, interval_seconds_nullable, affected_resource, delta_rule_text, source_url, confidence)`.
- Add `environmental_mana_modifiers(mana_type, factor_type, factor_name, peak_condition, low_condition, numeric_rule_nullable, source_url, confidence)`.
- Add `profession_resource_overlays(profession, resource_name, modifier_type, rule_text, source_url, confidence)`.
- Add `item_resource_interfaces(item_system, stored_resource, activation_verbs, constraints_text, decay_rule_text, source_url, confidence)`.

### Bottom line

DireLore already preserves the conceptual architecture the engine appears to be using:

```text
environment -> mana realm availability
caster -> attunement pool
player input -> prepare / harness / charge / invoke / cast
ongoing systems -> pulses / upkeep / regeneration
profession overlays -> devotion / shock / celestial alignment / elemental efficacy
```

What it does not preserve is the final mathematical backend in normalized form.

The DB knows how the engine thinks about resources.
It does not yet store that thinking as a clean resource-graph with complete formulas.

## 9. ENGINE-READY FORMULA SET

Status: design target

Constraint:

- The formulas in this section are implementation decisions for DireEngine.
- They are not recovered canon unless explicitly labeled as sourced support math.
- If stronger engine evidence appears later, these formulas may be revised.

### Runtime architecture lock

Do not implement a generic mana bar.

Implement this layered flow instead:

```text
room/environment -> effective environmental mana
effective environmental mana -> attunement pressure / shaping cost
attunement -> player-selected spell input
spell input -> prepared / held mana
prepared mana -> cast resolution / cyclic upkeep
profession overlays -> environment, healing, and regeneration modifiers
external stores -> cambrinth / ritual focus / companion resources
```

### 9.1 Environmental mana

Each room stores realm affinity:

```python
room.db.mana = {
    "holy": H,
    "life": L,
    "elemental": E,
    "lunar": U,
}
```

Normalization target:

```text
0.00 to 1.50

0.00 = unavailable
0.50 = poor
1.00 = normal
1.25 = rich
1.50 = peak
```

### 9.2 Effective environmental mana

For most guilds:

```text
effective_env_mana =
    room_realm_mana
    * global_cycle_modifier
    * profession_env_modifier
```

Clamp:

```text
effective_env_mana = clamp(value, 0.00, 2.00)
```

Overlay targets:

```text
Empath:
    profession_env_modifier = 1.00

Cleric:
    profession_env_modifier = 1.00 + devotion_percent * 0.25

Warrior Mage:
    profession_env_modifier = 1.00 + elemental_alignment_bonus

Moon Mage:
    effective_env_mana =
        lunar_global_state
        * celestial_alignment_modifier
        * weather_modifier
```

### 9.3 Attunement maximum

Attunement is the usable magical fatigue pool.

```text
attunement_max =
    40
    + attunement_skill * 0.60
    + intelligence * 0.80
    + discipline * 0.50
    + circle * 0.75
```

Clamp:

```text
attunement_max >= 40
```

### 9.4 Attunement regeneration per pulse

Pulse interval:

```text
mana_pulse_interval = 5 seconds
```

Regen model:

```text
attunement_missing = attunement_max - attunement_current
missing_ratio = attunement_missing / attunement_max

regen_per_pulse =
    (
        0.8
        + attunement_skill * 0.015
        + wisdom * 0.020
    )
    * (0.50 + missing_ratio)
    * regen_modifiers
```

`regen_modifiers` may include:

- spell effects such as `Persistence of Mana`
- wounds or fatigue penalties
- profession-specific bonuses or penalties

### 9.5 Spell mana input

Each spell must expose:

```text
min_prep
max_prep
```

Player chooses:

```text
mana_input
```

Constraint:

```text
min_prep <= mana_input <= max_prep
```

### 9.6 Cast viability gate

Ambient access requirement:

```text
ambient_floor_required = max(1, ceil(min_prep * 0.10))
```

Preparation must fail if:

```text
effective_env_mana * 100 < ambient_floor_required
```

This preserves the sourced constraint that cambrinth cannot fully replace real ambient access.

### 9.7 Attunement cost to prepare

Environment softens shaping cost:

```text
env_discount = 0.75 + (effective_env_mana * 0.25)
prep_cost = ceil(mana_input / env_discount)
```

Preparation allowed only if:

```text
attunement_current >= prep_cost
```

State change:

```text
attunement_current -= prep_cost
```

### 9.8 Harness conversion

Harness turns attunement into held spell energy.

```text
harness_efficiency =
    0.60
    + attunement_skill * 0.0015
    + arcana_skill * 0.0010
```

Clamp:

```text
harness_efficiency = clamp(value, 0.60, 0.95)
```

Conversion:

```text
attunement_spent = ceil(requested_harness / harness_efficiency)
held_mana += requested_harness
attunement_current -= attunement_spent
```

### 9.9 Final spell power

```text
skill_factor = 1.00 + (primary_magic_skill / 1000)
env_factor = 0.75 + (effective_env_mana * 0.35)
control_factor = 0.85 + (attunement_current / attunement_max) * 0.25

final_spell_power =
    mana_input
    * skill_factor
    * env_factor
    * control_factor
    * profession_cast_modifier
```

Clamp:

```text
final_spell_power <= mana_input * 2.5
```

### 9.10 Spell strain and backlash

```text
spell_difficulty =
    base_difficulty
    + max(0, cast_mana - safe_mana) * 1.25
    + tier * 6.0
    + max(0, 1.0 - effective_env_mana) * 12.0

control_score =
    primary_magic_skill * 0.55
    + attunement_skill * 0.30
    + arcana_skill * 0.10
    + intelligence * 0.35
    + discipline * 0.30

strain_penalty = max(0, (1 - attunement_current / max(1, attunement_maximum)) * 18.0)

cast_margin = control_score - spell_difficulty - strain_penalty + random(-10.0, 10.0)

success_band =
    excellent  if cast_margin >= 15
    solid      if cast_margin >= 8
    partial    if cast_margin >= 0
    failure    if cast_margin >= -10
    backlash   otherwise

backlash_chance = clamp(
    8.0 + max(0, -cast_margin) * 2.5 + max(0, tier - 2) * 3.0,
    0.0,
    75.0,
)
```

Clamp:

```text
0.0 to 75.0
```

Profession-specific backlash payloads are layered after chance resolution:

- Empath: shock gain
- Cleric: devotion loss
- Warrior Mage: self-hit damage
- Moon Mage: focus penalty metadata

### 9.11 Cyclic upkeep

Use the same `5` second pulse.

```text
cyclic_drain_per_pulse = max(1, ceil(prepared_mana * (0.08 + min(ticks_active, 10) * 0.01)))

cyclic_control_margin =
    control_score
    - (base_difficulty + ticks_active * 2.5)
    - strain_penalty
    + random(-5.0, 5.0)

unstable warning when cyclic_control_margin < 5
collapse check when cyclic_control_margin < 0
forced backlash allowed when cyclic_control_margin <= -12
```

Drain order:

```text
1. held mana
2. linked cambrinth energy
3. direct attunement if an explicit mode/feat allows it
4. otherwise the cyclic spell collapses
```

### 9.12 Cambrinth

Sourced support math retained exactly where the excavation found it.

Charge roundtime:

```text
RT = 2 + floor( CHARGE / (5 + floor(Arcana_Ranks / 100)) )
```

Worn requirement:

```text
Arcana_Ranks_Required = 100 + 2 * Mana_Capacity
```

Leakage model:

```text
half-life structure is sourced
exact interval was not found
implementation target: stored energy halves every 10 minutes
```

### 9.13 Cleric devotion overlay

```text
holy_access_bonus = 1.00 + devotion_percent * 0.25
```

Item pulse support:

```text
every 60 seconds:
    devotion += 1% of max_devotion if devotion is below max_devotion
```

### 9.14 Empath shock overlay

```text
shock_ratio = shock_current / shock_max
healing_power_modifier = 1.00 - shock_ratio * 0.80
```

Interpretation:

```text
no shock = 100% healing power
max shock = 20% healing power for actions that remain allowed
threshold-based disables still apply separately
```

### 9.15 Moon Mage celestial overlay

Moon Mages do not use room-local mana for their primary mana access.

```text
lunar_global_state =
    moon_phase_modifier
    * horizon_modifier
    * weather_modifier
    * conjunction_modifier

effective_env_mana = clamp(lunar_global_state, 0.20, 2.00)
```

## 10. AEDAN-PROOF MICROTASKS (MANA-001 TO MANA-030)

Version: SIR-EP v1.0
Status: LOCKED
Intent: implement the DireEngine mana runtime as a layered system, not a flat resource bar.

## Global Execution Rules

Every task in this section must preserve:

1. `Command -> Service -> Domain -> Result -> Presenter`
2. domain purity: no Evennia imports in `domain/`
3. service mutation only: state changes happen in services or runtime object methods, not domain math
4. explicit numeric handling: no `value = x or default` when `0` is valid
5. no chained `getattr(getattr(...))`
6. no unrelated cleanup inside mana tasks

If any task violates those rules, reject and rewrite it before implementation.

### Phase 1 - Domain Foundation (MANA-001 to MANA-008)

#### MANA-001 - Create the mana domain package

Create directory:

- `domain/mana/`

Create files:

- `domain/mana/__init__.py`
- `domain/mana/constants.py`
- `domain/mana/models.py`
- `domain/mana/rules.py`

Constraints:

- Do not import Evennia modules.
- Keep `__init__.py` export-only.
- Do not place character or room mutation logic in this package.

Acceptance:

- Imports from `domain.mana.rules` succeed.
- Imports from `domain.mana.models` succeed.

#### MANA-002 - Define mana constants

File:

- `domain/mana/constants.py`

Add:

```python
MANA_REALMS = ("holy", "life", "elemental", "lunar")

MANA_MIN = 0.0
MANA_MAX = 2.0

DEFAULT_ROOM_MANA = {
    "holy": 1.0,
    "life": 1.0,
    "elemental": 1.0,
    "lunar": 1.0,
}

DEFAULT_GLOBAL_MANA_MODIFIER = 1.0
DEFAULT_PROFESSION_MANA_MODIFIER = 1.0

MANA_PULSE_INTERVAL = 5
DEVOTION_PULSE_INTERVAL = 60
CAMBRINTH_HALF_LIFE_SECONDS = 600
MAX_FINAL_POWER_MULTIPLIER = 2.5
MAX_BACKLASH_CHANCE = 75.0
```

Constraints:

- Keep values numeric, not strings.
- Do not add canon values that were explicitly marked `NOT FOUND IN DB`.

Acceptance:

- Test code can import all constants without touching Evennia.

#### MANA-003 - Define domain models

File:

- `domain/mana/models.py`

Add dataclasses for:

- `AttunementState(current: float, maximum: float)`
- `PreparedManaState(realm: str, mana_input: int, prep_cost: int, held_mana: int = 0)`
- `ManaContext(room_mana: float, global_modifier: float, profession_modifier: float)`

Constraints:

- Use `maximum`, not `max`, as a field name.
- Models must be data-only.

Acceptance:

- Constructors work with plain Python values.

#### MANA-004 - Add clamp helpers and normalization helpers

File:

- `domain/mana/rules.py`

Add pure helpers:

- `clamp(value, min_value, max_value)`
- `clamp_mana(value)` using `MANA_MIN` and `MANA_MAX`
- `clamp_backlash(value)` using `0.0` and `MAX_BACKLASH_CHANCE`

Constraints:

- Do not import `math` just for clamping.
- Helpers must not mutate arguments.

Acceptance:

- Out-of-range values clamp predictably in unit tests.

#### MANA-005 - Implement attunement-cap math

File:

- `domain/mana/rules.py`

Add:

- `calculate_attunement_max(attunement_skill, intelligence, discipline, circle)`

Formula:

```text
40
+ attunement_skill * 0.60
+ intelligence * 0.80
+ discipline * 0.50
+ circle * 0.75
```

Constraints:

- Clamp minimum to `40`.
- Return `float`.

Acceptance:

- Higher inputs always produce equal or higher max attunement.

#### MANA-006 - Implement environmental mana math

File:

- `domain/mana/rules.py`

Add:

- `calculate_effective_env_mana(room_mana, global_modifier, profession_modifier)`
- `calculate_ambient_floor_required(min_prep)`

Formula:

```text
effective_env_mana = clamp(room_mana * global_modifier * profession_modifier, 0.0, 2.0)
ambient_floor_required = max(1, ceil(min_prep * 0.10))
```

Constraints:

- Use `math.ceil` for the ambient floor calculation.
- Do not hardcode profession logic in this function.

Acceptance:

- The same inputs always produce the same result.

#### MANA-007 - Implement regen, prep, harness, power, and backlash math

File:

- `domain/mana/rules.py`

Add pure functions:

- `calculate_attunement_regen(attunement_current, attunement_maximum, attunement_skill, wisdom, regen_modifiers=1.0)`
- `calculate_prep_cost(mana_input, effective_env_mana)`
- `calculate_harness_efficiency(attunement_skill, arcana_skill)`
- `calculate_harness_cost(requested_harness, harness_efficiency)`
- `calculate_final_spell_power(mana_input, primary_magic_skill, effective_env_mana, attunement_current, attunement_maximum, profession_cast_modifier=1.0)`
- `calculate_backlash_chance(prep_cost, attunement_current_before_cast, mana_input, min_prep, primary_magic_skill)`
- `calculate_cyclic_drain(prepared_mana, ticks_active=0)`
- `calculate_spell_difficulty(spell_profile, cast_mana, effective_env_mana)`
- `calculate_control_score(control_context, spell_profile)`
- `calculate_strain_penalty(attunement_current, attunement_maximum)`
- `calculate_cast_margin(control_score, spell_difficulty, strain_penalty, random_roll)`
- `resolve_success_band(cast_margin)`
- `calculate_backlash_severity(cast_margin)`
- `calculate_cyclic_control_margin(control_score, base_difficulty, strain_penalty, ticks_active, random_roll)`

Constraints:

- Use `math.ceil` where the formula calls for ceil.
- `attunement_maximum <= 0` must not divide by zero.
- `harness_efficiency` must clamp to `0.60` through `0.95`.
- `final_spell_power` must clamp to `mana_input * 2.5`.
- `backlash_chance` must clamp to `0.0` through `75.0`.

Acceptance:

- Regen increases as missing attunement increases.
- Better environment lowers prep cost.
- Higher skill never lowers final spell power for otherwise equal inputs.

#### MANA-008 - Add domain test coverage

Create file:

- `tests/domain/test_mana_rules.py`

Add tests for:

- clamp behavior
- attunement max monotonicity
- prep cost decreases in richer environments
- regen is higher when attunement is low
- harness efficiency clamps correctly
- final power clamps at the configured max multiplier
- backlash chance rises under higher strain
- cyclic drain has a minimum of `1`
- success bands resolve from cast margin
- severe negative margins escalate backlash severity

Constraints:

- Use `unittest`, matching the repo style.
- Test the domain layer only in this file.

Acceptance:

- `python -m unittest tests.domain.test_mana_rules` passes.

### Phase 2 - Service and Presenter Surface (MANA-009 to MANA-015)

#### MANA-009 - Create `ManaService`

Create file:

- `engine/services/mana_service.py`

Add class:

- `ManaService`

Add imports:

- `ActionResult` from `engine.services.result`
- pure rule functions from `domain.mana.rules`
- default constants from `domain.mana.constants`

Constraints:

- This service may mutate character and room state.
- Keep methods static to match existing service style.

Acceptance:

- The file imports cleanly.

#### MANA-010 - Add service state readers and writers

File:

- `engine/services/mana_service.py`

Add helper methods:

- `_get_db_holder(obj)` returning `obj.db` or `None`
- `_get_room_mana(room, realm)`
- `_get_attunement_state(character)`
- `_set_attunement_state(character, current, maximum)`
- `_get_prepared_mana_state(character)`
- `_set_prepared_mana_state(character, state_dict)`

Storage targets:

```python
room.db.mana = {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0}

character.db.attunement = {"current": float, "max": float}

character.ndb.prepared_mana = {
    "realm": str,
    "mana_input": int,
    "prep_cost": int,
    "held_mana": int,
}
```

Constraints:

- Do not use nested `getattr(getattr(...))`.
- Do not use `dict.get(..., default) or default` when `0` is valid.
- Missing storage should be initialized explicitly.

Acceptance:

- Helper methods return normalized dictionaries even on first use.

#### MANA-011 - Add profession overlay helpers

File:

- `engine/services/mana_service.py`

Add methods:

- `_get_profession_env_modifier(character, realm)`
- `_get_profession_cast_modifier(character, realm)`
- `_get_moon_mage_effective_env(character)`
- `_get_empath_healing_modifier(character)`

Initial overlay rules:

- Cleric Holy: `1.0 + devotion_percent * 0.25`
- Warrior Mage Elemental: `1.0 + alignment_bonus`
- Empath healing: `1.0 - shock_ratio * 0.80`
- Moon Mage Lunar: bypass room mana and use the dedicated lunar-global path

Constraints:

- Keep overlay logic separate from the domain math functions.
- Use defensive defaults of `1.0` only when the value is genuinely absent, not when it is `0`.

Acceptance:

- Overlay helpers can be called independently in service tests.

#### MANA-012 - Implement `can_prepare_spell`

File:

- `engine/services/mana_service.py`

Add:

- `can_prepare_spell(character, room, realm, mana_input, min_prep, max_prep)`

Return:

- `ActionResult.ok(...)` on success
- `ActionResult.fail(...)` on failure

Validation steps, in order:

1. missing character / room / realm
2. invalid realm not in `MANA_REALMS`
3. `mana_input` outside `min_prep` / `max_prep`
4. insufficient ambient floor
5. insufficient attunement

Include in result data:

- `effective_env_mana`
- `ambient_floor_required`
- `prep_cost`
- `realm`
- `mana_input`

Constraints:

- No state mutation in this method.
- Use `ActionResult.fail(errors=[...], data={...})` for blocked paths.

Acceptance:

- Failure returns structured data that explains why preparation was blocked.

#### MANA-013 - Implement state mutation methods

File:

- `engine/services/mana_service.py`

Add:

- `spend_attunement(character, amount)`
- `restore_attunement(character, amount)`
- `set_attunement_max(character, maximum)`
- `clear_prepared_mana(character)`

Constraints:

- Clamp current attunement to `0` through `max`.
- Preserve valid `0` values.

Acceptance:

- Spending never drives attunement negative.
- Restoring never exceeds max.

#### MANA-014 - Implement prepare, harness, and cast flow

File:

- `engine/services/mana_service.py`

Add:

- `prepare_spell(character, room, realm, mana_input, min_prep, max_prep)`
- `harness_mana(character, amount, attunement_skill, arcana_skill)`
- `cast_spell(character, realm, primary_magic_skill, profession_cast_modifier=1.0)`

`prepare_spell` must:

1. call `can_prepare_spell`
2. spend attunement
3. write `character.ndb.prepared_mana`
4. return `ActionResult.ok(...)`

`harness_mana` must:

1. calculate harness efficiency
2. compute attunement spent
3. increase `held_mana`
4. return structured result data

`cast_spell` must:

1. require an existing prepared state
2. compute final power
3. compute backlash chance
4. return `ActionResult.ok(data={...})`
5. clear prepared mana on successful cast

Constraints:

- Do not apply messaging in the service.
- Do not infer spell definitions from `character` internals.

Acceptance:

- Successful prepare mutates state once and returns structured payload.
- Successful cast clears prepared mana.

#### MANA-015 - Create `ManaPresenter`

Create file:

- `engine/presenters/mana_presenter.py`

Add class:

- `ManaPresenter`

Add methods:

- `render_prepare(result)`
- `render_harness(result)`
- `render_cast(result)`

Constraints:

- Presenter converts `ActionResult` to user-facing lines only.
- No state mutation.

Acceptance:

- Blocked results and successful results both render deterministic message payloads.

### Phase 3 - Profession and Pulse Integration (MANA-016 to MANA-022)

#### MANA-016 - Create service-level tests

Create file:

- `tests/services/test_mana_service.py`

Add focused tests for:

- low environment produces higher prep cost than rich environment
- `0` attunement blocks preparation
- successful prepare stores prepared mana
- harness increases held mana and reduces attunement
- successful cast clears prepared mana

Constraints:

- Use lightweight dummy objects like existing service tests.
- Mock only where needed.

Acceptance:

- `python -m unittest tests.services.test_mana_service` passes.

#### MANA-017 - Add Cleric and Empath overlay tests

File:

- `tests/services/test_mana_service.py`

Add tests for:

- Cleric devotion increases effective Holy access
- Empath shock reduces healing modifier

Constraints:

- Keep healing modifier tests on service helpers until a dedicated healing service consumes them.

Acceptance:

- The tests prove overlays change output in the expected direction.

#### MANA-018 - Add Moon Mage and Warrior Mage overlay tests

File:

- `tests/services/test_mana_service.py`

Add tests for:

- Moon Mage effective mana ignores room mana and uses the lunar-global path
- Warrior Mage elemental alignment bonus increases effective mana

Constraints:

- Make Moon Mage and non-Moon Mage behavior directly comparable in the test.

Acceptance:

- The tests fail if room mana is incorrectly used for Moon Mage mana access.

#### MANA-019 - Add mana pulse callbacks to the scheduler

File:

- `world/systems/scheduler.py`

Add callback functions:

- `_callback_process_mana_regen(owner, payload=None)`
- `_callback_process_devotion_pulse(owner, payload=None)`

Register them with:

- `register_event_callback("mana:process_regen", _callback_process_mana_regen)`
- `register_event_callback("mana:process_devotion", _callback_process_devotion_pulse)`

Callback behavior:

- call into `ManaService.regenerate_attunement(...)`
- call into `ManaService.apply_devotion_pulse(...)`

Constraints:

- Match the existing scheduler callback pattern already used for skill pulses.
- Do not invent a separate scheduler system.

Acceptance:

- Scheduler can resolve both callback names without raising `Unknown scheduler event callback`.

#### MANA-020 - Add pulse-facing service methods

File:

- `engine/services/mana_service.py`

Add:

- `regenerate_attunement(character, attunement_skill, wisdom, regen_modifiers=1.0)`
- `apply_devotion_pulse(character)`

Behavior:

- `regenerate_attunement` uses domain regen math and clamps to max
- `apply_devotion_pulse` restores `1%` of max devotion, not a raw `+1`

Constraints:

- Preserve valid zero values in stored state.
- `apply_devotion_pulse` must no-op cleanly if the character has no devotion data yet.

Acceptance:

- Service tests can call the pulse methods directly with dummy objects.

#### MANA-021 - Add scheduling helper methods for mana events

File:

- `engine/services/mana_service.py`

Add:

- `schedule_mana_regen(character, delay=MANA_PULSE_INTERVAL)`
- `schedule_devotion_pulse(character, delay=DEVOTION_PULSE_INTERVAL)`
- `cancel_mana_regen(character)`
- `cancel_devotion_pulse(character)`

Use:

- `schedule_event(...)`
- `cancel_event(...)`

Metadata target:

```python
metadata={"system": "mana", "type": "regen"}
metadata={"system": "mana", "type": "devotion"}
```

Constraints:

- Use canonical scheduler keys.
- Do not use arbitrary callback strings outside `register_event_callback` support.

Acceptance:

- The helper methods create and cancel scheduler jobs through the existing scheduler API.

#### MANA-022 - Add scheduler-focused tests

Create file:

- `tests/services/test_mana_scheduler.py`

Add tests for:

- callback registration succeeds
- scheduling helper emits a scheduler job with mana metadata
- cancel helper removes the job

Constraints:

- Reuse the scheduler testing approach already present in `diretest.py` rather than sleeping in real time.

Acceptance:

- `python -m unittest tests.services.test_mana_scheduler` passes.

### Phase 4 - Runtime Object Integration (MANA-023 to MANA-026)

#### MANA-023 - Add character defaults for mana storage

Target file:

- `typeclasses/characters.py`

Add or extend a defaults/bootstrap path so new characters have:

```python
character.db.attunement = {"current": 0.0, "max": 0.0}
character.db.devotion = {"current": 0.0, "max": 100.0}
character.db.shock = {"current": 0.0, "max": 100.0}
```

Constraints:

- Place this in an existing defaults initialization path, not arbitrary command code.
- Do not overwrite existing user state if data already exists.

Acceptance:

- A fresh dummy character can be normalized without extra mana setup calls.

#### MANA-024 - Add room defaults for mana storage

Target file:

- the existing room/bootstrap path that seeds room defaults

Add:

```python
room.db.mana = {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0}
```

Constraints:

- Only initialize when missing.
- Do not force all rooms to identical long-term values; this is a safe default only.

Acceptance:

- Service helpers can rely on a missing room normalizing to the default shape.

#### MANA-025 - Add a runtime entry point for mana preparation

Target file:

- the command or runtime surface that will own spell preparation

Requirement:

- route preparation through `ManaService.prepare_spell(...)`
- route result messaging through `ManaPresenter.render_prepare(...)`

Constraints:

- Do not put formula math into the command.
- Do not bypass `ActionResult`.

Acceptance:

- One runtime call site uses the new service and presenter path end-to-end.

#### MANA-026 - Add a runtime entry point for casting

Target file:

- the command or runtime surface that will own spell casting

Requirement:

- route cast execution through `ManaService.cast_spell(...)`
- route messaging through `ManaPresenter.render_cast(...)`

Constraints:

- Do not duplicate the power or backlash formulas in the command.

Acceptance:

- One runtime call site uses the new cast path end-to-end.

### Phase 5 - Validation and Handoff Lock (MANA-027 to MANA-030)

#### MANA-027 - Add regression tests for numeric-zero preservation

Target file:

- `tests/services/test_mana_service.py`

Add tests proving these values are preserved, not defaulted away:

- `attunement.current = 0.0`
- `room.db.mana[realm] = 0.0`
- `devotion.current = 0.0`
- `shock.current = 0.0`
- `prepared_mana.held_mana = 0`

Constraint:

- This task exists specifically to prevent `RULE-ANTI-002` regressions.

Acceptance:

- Tests fail if any implementation reintroduces `or default` behavior for numeric state.

#### MANA-028 - Add focused executable validation commands to the task notes

Validation targets:

- `python -m unittest tests.domain.test_mana_rules`
- `python -m unittest tests.services.test_mana_service`
- `python -m unittest tests.services.test_mana_scheduler`

Constraint:

- Do not close the implementation slice without at least one focused executable validation step.

Acceptance:

- The implementation handoff lists the exact narrow validations above.

#### MANA-029 - Add repo memory for the mana architecture lock

Repo memory target:

- `/memories/repo/` existing architecture or systems note

Record:

- mana is layered, not flat
- domain owns pure mana math
- service owns mutation and scheduler calls
- presenter owns messaging
- zero-valued numeric state must never be defaulted away

Acceptance:

- Future implementation work has a durable repo note describing the mana model boundary.

#### MANA-030 - Final implementation rule for Aedan

Carry this exact instruction into the handoff:

```text
Do not implement a generic mana bar.
Implement a layered system:
room/environment -> attunement -> player-selected input -> pulse/upkeep -> profession overlays.

All formulas in Section 9 are design targets unless contradicted by stronger engine evidence later.
```

Acceptance:

- The final task packet states the architecture lock and the provisional-formula rule explicitly.

## 11. IMPLEMENTATION NOTES (SAFE SLICE)

`Scheduler registration surface`

- `world.systems.scheduler.schedule_event(key, owner, delay, callback, payload=None, metadata=None, **schedule_kwargs)` is the real event wrapper.
- Scheduler expects:
    - `key: str`
    - `owner: object`
    - `handler: callable` or registered callback name via `register_event_callback(...)`
- Event callbacks resolve through registry names such as `"mana:process_devotion"`.
- Event jobs normalize to stable scheduler keys in the form `event:<event-key>:<owner-token>`.

`Current runtime control path`

- Generic attunement regeneration is already processed by the existing global status tick through `Character.regen_attunement()`.
- Structured cyclic upkeep is already processed by the existing global status tick through `Character.process_magic_states()`.
- Because those paths already exist, the engine must not add a second regen or cyclic ticker; doing so would double-apply mana effects.
- Scheduler-backed mana work in this slice is limited to the devotion pulse, while the generic prepare/cast runtime path is routed through `ManaService` and `ManaPresenter`.

## 12. AEDAN-PROOF MICROTASKS (MANA-111 TO MANA-140)

Version: SIR-EP v1.1
Status: LOCKED
Intent: expose cast tension, risk, and payoff to the player without degrading the current service/domain boundaries.

### Architecture guardrails

- Do not promote mana-specific fields into `ActionResult` core attributes.
- Keep all mana payload fields inside `result.data`.
- `ManaService` emits structured semantic keys only.
- `ManaPresenter` maps semantics to player-facing text.
- Do not create duplicate concepts such as `power_score` when `final_spell_power` already exists.
- Do not move cast/backlash/cyclic decision logic into the presenter.

### Phase 14 - Structured Payload + Presenter Routing (MANA-111 to MANA-120)

#### MANA-111 - Standardize ManaService payload keys

File:

- `engine/services/mana_service.py`

Ensure all cast paths populate:

```python
result.data.update({
    "success_band": band,
    "cast_margin": cast_margin,
    "final_spell_power": final_spell_power,
    "effective_env_mana": effective_env_mana,
    "safe_mana": safe_mana,
    "mana_input": mana_input,
})
```

Constraints:

- Do not add mana-specific fields to `ActionResult` attributes.
- Use stable semantic key names; do not mix `band` and `success_band` long-term.

Acceptance:

- All successful and failed cast payloads expose the same semantic keys where applicable.

#### MANA-112 - Standardize backlash payload

File:

- `engine/services/mana_service.py`

Ensure backlash resolution emits:

```python
result.data["backlash_payload"] = {
    "triggered": bool,
    "severity": int,
    "type": str,
}
```

Constraints:

- Preserve profession-specific payload details separately if they already exist.
- `triggered=False` must be explicit when no backlash fires.

Acceptance:

- Presenter can determine backlash state without reverse-engineering other fields.

#### MANA-113 - Standardize cyclic payload

File:

- `engine/services/mana_service.py`

Ensure cyclic updates emit:

```python
result.data["cyclic_state"] = {
    "active": bool,
    "ticks_active": int,
    "instability": float,
    "margin": float,
}
```

Constraints:

- Service emits numbers and state only.
- Presenter derives labels like stable or critical from these values.

Acceptance:

- Cyclic messaging can be generated without inspecting live character state directly.

#### MANA-114 - Create unified presenter entry point

File:

- `engine/presenters/mana_presenter.py`

Add:

- `render_full_cast(result) -> list[str]`

Constraints:

- Return ordered message lines, not one concatenated sentence.
- Existing `render_cast(...)` may delegate to this method.

Acceptance:

- A single presenter call produces the complete player-facing cast sequence.

#### MANA-115 - Enforce presenter-only messaging

Search and remove direct cast messaging from:

- `engine/services/mana_service.py`
- `typeclasses/characters.py`

Constraints:

- Service emits data only.
- Runtime code routes messaging only through presenter output.

Acceptance:

- No cast/backlash/cyclic flavor strings are emitted outside the presenter layer.

#### MANA-116 - Add ordered output contract

Presenter output must be assembled in this order:

1. environment
2. overprep warning
3. cast result
4. power feedback
5. instability warning
6. backlash, if any

Constraints:

- Preserve deterministic order even when some entries are absent.

Acceptance:

- Integration tests can assert a stable output sequence.

#### MANA-117 - Add presenter test scaffold

Create file:

- `tests/presenters/test_mana_presenter.py`

Add tests for:

- success band routes to the correct base message
- missing fields fall back safely

Constraints:

- Use plain `ActionResult` inputs with structured `data`.

Acceptance:

- Presenter tests pass without Evennia runtime setup.

#### MANA-118 - Add safe fallback handling

File:

- `engine/presenters/mana_presenter.py`

If missing:

```python
band = result.data.get("success_band", "unknown")
```

Fallback line:

```text
You attempt to shape the mana.
```

Acceptance:

- Presenter never crashes on incomplete mana payloads.

#### MANA-119 - Add debug overlay (dev only)

File:

- `engine/presenters/mana_presenter.py`

If `DEBUG_MANA` is enabled, append:

```text
[band=partial margin=3.1 power=42]
```

Constraints:

- Keep this behind an explicit debug flag.
- Do not contaminate normal player output.

Acceptance:

- Dev output exposes semantic fields without changing the service contract.

#### MANA-120 - Validate no duplicate messaging paths

Search for cast-feedback strings such as:

- `mana slips`
- `shape the mana`
- `pattern remains stable`

Acceptance:

- Presenter is the only owner of these message strings.

### Phase 15 - Backlash + Cyclic Feedback (MANA-121 to MANA-130)

#### MANA-121 - Implement backlash renderer

File:

- `engine/presenters/mana_presenter.py`

Add:

- `render_backlash(payload) -> str`

Use:

- `severity = payload["severity"]`
- `ptype = payload["type"]`

Acceptance:

- Backlash messaging can be rendered from payload alone.

#### MANA-122 - Map severity to base message

Add severity base messages:

- `1` -> slight disruption
- `2` -> violent twist
- `3` -> lash back
- `4` -> catastrophic collapse
- `5` -> devastating eruption

Constraints:

- Keep severity wording deterministic.

Acceptance:

- Severity tiers produce visibly different output.

#### MANA-123 - Add profession overlays

Map `type` values to overlays:

- `empath` -> empathic feedback
- `cleric` -> divine disruption
- `warrior_mage` -> elemental recoil
- `moon_mage` -> perceptual fracture

Acceptance:

- The same severity reads differently by profession flavor.

#### MANA-124 - Combine messages cleanly

Return:

```python
f"{base_message} {overlay}".strip()
```

Constraints:

- Missing overlay must not leave trailing punctuation or double spaces.

Acceptance:

- Combined backlash lines remain grammatically clean.

#### MANA-125 - Handle partial backlash

If:

- `success_band == "failure"`
- `backlash_payload["triggered"] is True`

Clamp presenter severity rendering to `<= 2`.

Constraints:

- Do not mutate the service payload.
- This is a presentation rule, not a service rule.

Acceptance:

- Minor failure backlash reads as a partial loss of control, not full catastrophe.

#### MANA-126 - Add cyclic feedback renderer

File:

- `engine/presenters/mana_presenter.py`

Add:

- `render_cyclic_state(state) -> str | None`

Acceptance:

- Cyclic upkeep messaging is rendered from `cyclic_state` only.

#### MANA-127 - Map cyclic instability tiers

Map instability or margin into labels:

- stable -> `The pattern remains stable.`
- strained -> `The pattern strains under sustained effort.`
- unstable -> `The pattern begins to destabilize.`
- critical -> `The pattern is slipping toward collapse.`

Constraints:

- Derive tiers from emitted numbers, not new service flags unless needed.

Acceptance:

- Repeated cyclic ticks escalate messaging severity predictably.

#### MANA-128 - Add collapse warning

If:

- `state["margin"] < 0`

Add:

```text
You feel the pattern slipping from your control!
```

Acceptance:

- Pre-collapse danger is visible to the player before total failure.

#### MANA-129 - Add cyclic test coverage

File:

- `tests/presenters/test_mana_presenter.py`

Add tests for:

- instability tier mapping escalates correctly
- collapse warning triggers when margin is negative

Acceptance:

- Presenter tests cover cyclic feedback transitions.

#### MANA-130 - Validate no duplicate cyclic messaging

Acceptance:

- Service only emits cyclic numbers and state.
- Presenter is the only owner of cyclic warning strings.

### Phase 16 - Temptation + Player Psychology (MANA-131 to MANA-140)

#### MANA-131 - Add power-tier messaging

File:

- `engine/presenters/mana_presenter.py`

Use:

- `power = result.data["final_spell_power"]`

Map:

- low -> weak
- mid -> moderate
- high -> strong
- very high -> overwhelming

Acceptance:

- Players can feel the difference between restrained and explosive casts.

#### MANA-132 - Tie power tiers to real output

Constraints:

- Use `final_spell_power` only.
- Do not infer power tiers directly from `mana_input`.

Acceptance:

- Power feedback matches actual output, not input intent.

#### MANA-133 - Add overprep warning

If:

- `mana_input > safe_mana`

Message:

```text
You push more mana into the pattern than is safe.
```

Acceptance:

- Unsafe overprepping is always surfaced to the player.

#### MANA-134 - Add instability warning

If:

- `cast_margin < 5`

Message:

```text
The mana resists your control.
```

Acceptance:

- Near-failure casts telegraph danger even when they still resolve.

#### MANA-135 - Add environment feedback

Use `effective_env_mana`:

- `< 0.5` -> struggling to draw sufficient mana
- `> 1.3` -> area thrumming with available power

Acceptance:

- Environmental pressure becomes visible instead of hidden math.

#### MANA-136 - Add temptation reinforcement

If both:

- `mana_input > safe_mana`
- `final_spell_power` is high

Add:

```text
The mana surges dangerously, but with immense potential.
```

Acceptance:

- Risk and reward are presented together, not separately.

#### MANA-137 - Ensure no fake randomness

Constraints:

- All presenter messaging must derive from:
  - `cast_margin`
  - `final_spell_power`
  - `effective_env_mana`
  - `safe_mana`
- Do not add random flavor selection.

Acceptance:

- The same payload always produces the same message sequence.

#### MANA-138 - Build final message assembler

Implementation target:

```python
messages = []

messages.append(env_msg)
messages.append(overprep_msg)
messages.append(cast_msg)
messages.append(power_msg)
messages.append(instability_msg)

if backlash_msg:
    messages.append(backlash_msg)

return [message for message in messages if message]
```

Acceptance:

- Ordered message assembly is explicit and easy to test.

#### MANA-139 - Integration test

File:

- `tests/presenters/test_mana_presenter.py`

Simulate payloads for:

- excellent
- partial
- failure
- backlash
- cyclic unstable

Assert:

- correct ordering
- no duplication
- all expected layers present

Acceptance:

- Presenter sequencing is locked down by deterministic tests.

#### MANA-140 - Full system validation scenario

Run a focused scenario covering:

- low mana room
- high mana room
- overprep
- cyclic sustain
- forced backlash

Verify:

- tension is visible
- risk is communicated
- reward is visible

Acceptance:

- The player-facing loop exposes control, danger, temptation, and consequence without weakening the current architecture.

### Final rule for this phase

Do not expand spell content before this phase lands.

This phase exists to make the existing casting engine legible and emotionally readable to the player without compromising the current service/domain split.