# Magic System With Backlash

This document is a developer-facing overview of the current structured magic system in Dragonsire, with emphasis on failure resolution and backlash math.

## High-Level Architecture

The live magic system is split into four layers:

1. Spell data: spell definitions, safe mana, base difficulty, targeting, spell family, acquisition metadata.
2. Access and orchestration: whether a character can use a spell, prepare it, cast it, and clear prepared state.
3. Mana math: environmental mana, preparation cost, cast margin, success band, backlash chance, backlash severity.
4. Effect application: healing, warding, augmentation, targeted magic, debilitation, utility, and cyclic spell behavior.

Primary source files:

- [domain/spells/spell_definitions.py](domain/spells/spell_definitions.py)
- [engine/services/spell_access_service.py](engine/services/spell_access_service.py)
- [engine/services/mana_service.py](engine/services/mana_service.py)
- [domain/mana/backlash.py](domain/mana/backlash.py)
- [domain/mana/rules.py](domain/mana/rules.py)
- [typeclasses/characters.py](typeclasses/characters.py)
- [engine/services/spell_effect_service.py](engine/services/spell_effect_service.py)
- [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py)
- [engine/services/state_service.py](engine/services/state_service.py)
- [engine/presenters/mana_presenter.py](engine/presenters/mana_presenter.py)

## Spell Data Model

Structured spell definitions live in [domain/spells/spell_definitions.py](domain/spells/spell_definitions.py).

Each spell defines at least:

- `mana_type`: one of `holy`, `life`, `elemental`, `lunar`
- `spell_type`: `healing`, `augmentation`, `warding`, `targeted_magic`, `debilitation`, `cyclic`, `aoe`, or `utility`
- `cast_style`
- `allowed_professions`
- `min_circle`
- `min_skill`
- `safe_mana`
- `base_difficulty`
- `target_type`
- `effect_profile`

Example fields are declared on the `Spell` dataclass in [domain/spells/spell_definitions.py](domain/spells/spell_definitions.py#L7).

## Access Rules

Before mana math starts, the player must be allowed to use the spell. That logic lives in [engine/services/spell_access_service.py](engine/services/spell_access_service.py#L35).

The access checks are:

1. The caster belongs to one of the spell's allowed professions.
2. The caster has learned the spell.
3. The caster meets the spell's minimum circle.
4. The caster meets each minimum skill requirement.

Character-side spell lookup and alias resolution live in [typeclasses/characters.py](typeclasses/characters.py#L15714).

## Realms And Environmental Mana

The default mana realm is profession-driven in [typeclasses/characters.py](typeclasses/characters.py#L11408):

- `cleric`, `paladin` -> `holy`
- `empath`, `ranger` -> `life`
- `warrior_mage`, `bard` -> `elemental`
- `moon_mage` -> `lunar`

Mana realms are declared in [domain/mana/constants.py](domain/mana/constants.py#L1).

Effective environmental mana is computed in [engine/services/mana_service.py](engine/services/mana_service.py#L352).

At a high level:

`effective env mana = room mana * environmental modifier * profession modifier`

That value is clamped by `calculate_effective_env_mana` in [domain/mana/rules.py](domain/mana/rules.py#L58).

Notable profession modifiers:

- Clerics get stronger holy environmental scaling from devotion in [engine/services/mana_service.py](engine/services/mana_service.py#L268).
- Moon mages use a special lunar environment path in [engine/services/mana_service.py](engine/services/mana_service.py#L315).
- Empath healing later gets an empath-shock modifier in [engine/services/mana_service.py](engine/services/mana_service.py#L328).

## Preparation Flow

The player-facing preparation entry point is [typeclasses/characters.py](typeclasses/characters.py#L11444).

The prepare path does the following:

1. Resolve spell metadata.
2. Validate mana input against `mana_min` and `mana_max`.
3. Call `ManaService.prepare_spell(...)` in [engine/services/mana_service.py](engine/services/mana_service.py#L574).
4. Write prepared state into `ndb.prepared_mana`.
5. Write spell-facing state into `prepared_spell` on the character.

### Ambient Floor Gate

Preparation fails if the room cannot support the spell's minimum shaping threshold.

The ambient floor requirement from [domain/mana/rules.py](domain/mana/rules.py#L62) is:

`ambient floor required = ceil(0.10 * min prep)`

The gate is applied in [engine/services/mana_service.py](engine/services/mana_service.py#L490).

### Preparation Cost

Preparation cost is computed in [domain/mana/rules.py](domain/mana/rules.py#L72):

`prep cost = ceil(mana input / (0.75 + 0.25 * effective env mana))`

Implications:

- Stronger environmental mana lowers preparation cost.
- Poor environments make preparation more expensive.
- The cost is paid immediately as attunement in [engine/services/mana_service.py](engine/services/mana_service.py#L578).

### Prepared State

Prepared spell state is normalized and stored in `ndb.prepared_mana` in [engine/services/mana_service.py](engine/services/mana_service.py#L112).

The live system preserves these fields if present:

- `realm`
- `mana_input`
- `prep_cost`
- `held_mana`
- `min_prep`
- `max_prep`
- `safe_mana`
- `tier`
- `base_difficulty`
- `spell_category`

That preservation matters because the cast-band and cyclic-instability math read from those fields later. See normalization in [engine/services/mana_service.py](engine/services/mana_service.py#L112).

## Charge / Extra Power Sources

There are two related but distinct power concepts in the code.

### Held Mana / Harnessing

ManaService supports additional `held_mana` in [engine/services/mana_service.py](engine/services/mana_service.py#L606). When present:

`cast mana = mana input + held mana`

The harness formulas are:

Harness efficiency from [domain/mana/rules.py](domain/mana/rules.py#L77):

`harness efficiency = clamp(0.60 + 0.0015 * attunement skill + 0.0010 * arcana skill, 0.60, 0.95)`

Harness cost from [domain/mana/rules.py](domain/mana/rules.py#L82):

`harness attunement cost = ceil(requested harness / efficiency)`

### Luminar Charge

The active player `charge` command currently routes through `charge_luminar` in [typeclasses/characters.py](typeclasses/characters.py#L11352), not through the held-mana API.

Important luminar rules:

- Luminar safe charge is defined in [typeclasses/characters.py](typeclasses/characters.py#L15813):

`luminar safe charge = capacity + floor(arcana skill / 2)`

- If charge exceeds the safe limit, there is a flat 30% destabilization chance in [typeclasses/characters.py](typeclasses/characters.py#L11389).
- On destabilization, the luminar charge is reset to zero.
- When invoked, luminar power adds a flat bonus to final spell power after cast resolution in [typeclasses/characters.py](typeclasses/characters.py#L11535) and [typeclasses/characters.py](typeclasses/characters.py#L11571).

## Cast Resolution

The player-facing cast entry point is [typeclasses/characters.py](typeclasses/characters.py#L11515).

The mana-resolution math happens inside `ManaService._cast_spell(...)` in [engine/services/mana_service.py](engine/services/mana_service.py#L637).

### Control Context

The control context is assembled in [engine/services/mana_service.py](engine/services/mana_service.py#L364).

Inputs include:

- primary magic skill for the spell family
- attunement skill
- arcana skill
- intelligence
- discipline
- profession
- current attunement
- max attunement

### Spell Difficulty

Spell difficulty comes from [domain/mana/backlash.py](domain/mana/backlash.py#L13):

`difficulty = base difficulty + mana pressure + complexity pressure + environment pressure`

Where:

`mana pressure = max(0, cast mana - safe mana) * 1.25`

`complexity pressure = tier * 6`

`environment pressure = max(0, 1 - effective env mana) * 12`

If `effective_env_mana < 0.50`, the system adds another `8.0` difficulty in [domain/mana/backlash.py](domain/mana/backlash.py#L20).

### Control Score

Control score is computed in [domain/mana/backlash.py](domain/mana/backlash.py#L26):

`control score = 0.55 * primary magic + 0.30 * attunement + 0.10 * arcana + 0.35 * intelligence + 0.30 * discipline + focus bonus + profession control bonus`

Default profession control bonuses:

- Empath: `+2`
- Cleric: `+2`
- Moon Mage: `+4`
- Others: `+0`

### Strain Penalty

Low remaining attunement makes the cast harder. Strain penalty from [domain/mana/backlash.py](domain/mana/backlash.py#L55) is:

`strain penalty = (1 - (attunement current / attunement max)) * 18`

### Cast Margin

The final cast margin from [domain/mana/backlash.py](domain/mana/backlash.py#L62) is:

`cast margin = control score - difficulty - strain penalty + random roll`

The random roll is uniform on `[-10, 10]` in [engine/services/mana_service.py](engine/services/mana_service.py#L657).

## Success Bands

Success bands are resolved in [domain/mana/backlash.py](domain/mana/backlash.py#L71):

- `excellent` if margin >= 20
- `solid` if margin >= 8
- `partial` if margin >= 0
- `failure` if margin >= -10
- `backlash` if margin < -10

Band multipliers are defined in [engine/services/mana_service.py](engine/services/mana_service.py#L48):

- `excellent`: `1.15`
- `solid`: `1.00`
- `partial`: `0.65`
- `failure`: `0.0`
- `backlash`: `0.0`

That means:

- `excellent`, `solid`, and `partial` are all successful casts.
- `partial` still resolves, but with reduced power.
- `failure` and `backlash` both stop the spell before effect application.

## Final Spell Power

Raw final power is computed in [domain/mana/rules.py](domain/mana/rules.py#L85):

`final power = cast mana * skill factor * env factor * control factor * profession cast modifier`

Where:

`skill factor = 1 + (primary magic skill / 1000)`

`env factor = 0.75 + 0.35 * effective env mana`

`control factor = 0.85 + 0.25 * (attunement current / attunement max)`

Then the success-band multiplier is applied in [engine/services/mana_service.py](engine/services/mana_service.py#L669).

Cleric holy spells also get an extra devotion-based boost in [engine/services/mana_service.py](engine/services/mana_service.py#L675):

`1 + 0.25 * devotion ratio`

## Failure Model

There are three distinct failure layers in the live system.

### 1. Preparation / Mana Gate Failure

The spell never gets prepared because:

- ambient mana is too weak
- the caster lacks attunement
- mana input is outside allowed range

This path lives in [engine/services/mana_service.py](engine/services/mana_service.py#L459).

### 2. Cast-Band Failure

The spell was prepared, but mana-resolution failed. This is the important failure path for backlash.

If the band is:

- `failure`: the spell fizzles
- `backlash`: the spell breaks violently and always backlashes

Character-side handling is in [typeclasses/characters.py](typeclasses/characters.py#L11561), and messages come from [engine/presenters/mana_presenter.py](engine/presenters/mana_presenter.py#L45).

### 3. Post-Cast Contest Failure

This is not mana failure. The cast itself succeeded, but the target avoided or resisted the effect.

Examples:

- Targeted magic can miss because the target wins the evasion/reflex contest in [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L48).
- Debilitation can fail to apply because the target wins warding/discipline plus magic-resistance checks in [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L144).

This distinction matters when explaining logs and training outcomes to another developer.

## Backlash Math

The authoritative live backlash math is in [domain/mana/backlash.py](domain/mana/backlash.py) and used by [engine/services/mana_service.py](engine/services/mana_service.py#L679).

### Backlash Chance

Backlash chance is:

`overprep ratio = cast mana / safe mana`

`backlash chance = clamp_0_75(((overprep ratio - 1) * 18) + (max(0, -cast margin) * 1.5) + (max(0, 1 - effective env mana) * 10) + high-env bonus)`

Where `high-env bonus = 6` if:

- `effective_env_mana > 1.30`, and
- `overprep_ratio > 1.0`

Source: [domain/mana/backlash.py](domain/mana/backlash.py#L91).

Interpretation:

- Overprepping above `safe_mana` pushes backlash chance up quickly.
- Negative cast margins push backlash chance up even more.
- Weak ambient conditions add extra backlash pressure.
- Very strong ambient conditions do not make overprepping free; they add a bonus backlash term when the spell is overdriven.

### Backlash Severity

Severity is computed in [domain/mana/backlash.py](domain/mana/backlash.py#L107):

`severity = clamp_1_5(ceil((max(0, -cast margin) + 0.8 * max(0, cast mana - safe mana)) / 6))`

Severity rises with:

- how badly the cast margin failed
- how far the cast exceeded safe mana

### When Backlash Actually Applies

The decision point is in [engine/services/mana_service.py](engine/services/mana_service.py#L700).

Rules:

1. If the success band is `backlash`, backlash always applies.
2. If the success band is `failure`, backlash still has a secondary chance to trigger:

`trigger backlash if random(0,100) < backlash chance`

So:

- not every failure backlashes
- every backlash-band result does backlash

## Backlash Payload By Profession

Profession-specific backlash payload generation is in [domain/mana/backlash.py](domain/mana/backlash.py#L124).

### Empath

- `shock_gain = severity * 8`
- `attunement_burn_ratio = 0.03 * severity`

### Cleric

- `devotion_loss_ratio = 0.04 * severity`
- `attunement_burn_ratio = 0.03 * severity`

### Moon Mage

- `focus_penalty_duration = severity * 2`
- `attunement_burn_ratio = 0.02 * severity`

### Warrior Mage

- `vitality_loss = round(severity * (4 + mana_input * 0.15))`
- `attunement_burn_ratio = 0.02 * severity`

### Generic Fallback

Fallback payloads use severity tables for attunement burn and vitality loss in [domain/mana/backlash.py](domain/mana/backlash.py#L160).

## Applying Backlash Consequences

Payload application happens in [engine/services/mana_service.py](engine/services/mana_service.py#L396).

### Attunement Burn

Attunement burn becomes a real attunement loss of:

`attunement loss = ceil(max attunement * attunement burn ratio)`

### Other Profession-Specific Consequences

- Empath backlash increases empath shock.
- Cleric backlash reduces devotion.
- Warrior mage backlash directly reduces HP.
- Moon mage backlash applies a `mana_focus_penalty` state.

The applied values are attached back into the cast payload in [engine/services/mana_service.py](engine/services/mana_service.py#L707).

## Contest Layer After A Successful Cast

If the cast-band phase succeeds, the spell routes into the structured effect layer in [engine/services/spell_effect_service.py](engine/services/spell_effect_service.py#L8).

Important distinction:

- Cast success means the mana formed correctly.
- Effect success still depends on spell family and target contests.

### Targeted Magic

Targeted magic uses [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L48).

It contests:

- attack side: final spell power plus `targeted_magic`
- defense side: `evasion` plus `reflex`

The spell can therefore be a successful cast but still miss.

### Debilitation

Debilitation uses [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L144).

It contests:

- attack side: final spell power plus `debilitation`
- defense side: `warding` plus `discipline` plus magic resistance

The spell can therefore be a successful cast but fail to apply the debuff.

## Cyclic Spells

Cyclic spells are applied through [engine/services/spell_effect_service.py](engine/services/spell_effect_service.py#L334) and maintained by [engine/services/state_service.py](engine/services/state_service.py#L340).

The current live cyclic maintenance model is mostly collapse-driven, not repeated backlash-driven.

Per tick, cyclics can collapse because:

- the caster died
- a configured debilitation interruption occurred
- a room-anchored cyclic lost its room context
- the caster lacks enough attunement for `mana_per_tick`

Source: [engine/services/state_service.py](engine/services/state_service.py#L340).

There is a helper for cyclic control margin in [domain/mana/rules.py](domain/mana/rules.py#L107), but it does not appear to be the main live per-tick failure driver right now.

## Legacy / Non-Authoritative Helpers

There is an older helper in [typeclasses/characters.py](typeclasses/characters.py#L15847) named `resolve_spell_backlash`.

That helper uses older categories like `stable`, `fizzle`, `backlash`, and `wild`, but it is not the authoritative live cast path anymore. The live path for structured spells is:

- [typeclasses/characters.py](typeclasses/characters.py#L11515)
- [engine/services/mana_service.py](engine/services/mana_service.py#L637)
- [domain/mana/backlash.py](domain/mana/backlash.py)

If a developer is debugging current cast behavior, they should treat the ManaService/domain.mana path as authoritative.

## Practical Summary For Another Developer

If you need a fast explanation of how the live system works:

1. A spell is a structured data definition with safe mana and base difficulty.
2. The caster must know the spell and satisfy profession/circle/skill gates.
3. Preparation spends attunement immediately, with cost reduced by stronger ambient mana.
4. Casting compares control against difficulty, subtracts strain from low remaining attunement, and adds a random roll.
5. That produces a cast margin, which maps to `excellent`, `solid`, `partial`, `failure`, or `backlash`.
6. `failure` means the pattern fizzles. `backlash` means it collapses violently and always applies self-punishment.
7. A `failure` result can still escalate into actual backlash using the backlash-chance formula.
8. Even after a successful cast, targeted and debilitation spells still have to win their own target contests.
9. The authoritative backlash math is in [domain/mana/backlash.py](domain/mana/backlash.py), and the authoritative live cast orchestration is in [engine/services/mana_service.py](engine/services/mana_service.py).