# Nerve Damage Research

## Executive Summary

The live game does not currently implement a first-class nerve damage subsystem.

What is implemented today is:

- physical body-part trauma, bleeding, tending, scars, and derived combat penalties
- HP loss and recovery as a separate layer
- empath shock and empath strain as a profession-specific burden system that affects healing and some empath actions

The closest live equivalents to nerve damage are:

- head, arm, hand, leg, and core trauma penalties from the wound system
- empath shock lockouts and healing penalties for empaths
- debilitation effects in the spell system

The accessible Postgres database on port `5432` does contain canonical spell/spec data mentioning nerve damage, but that appears to be lore/design data in the `direlore` database, not the authoritative runtime implementation.

## What I Checked

I checked three sources:

1. Live runtime code in the repo.
2. The accessible Postgres databases using the provided credentials.
3. Existing research documents in `docs/research` and `docs/archive`.

### Database Reachability

Using the provided credentials against `127.0.0.1:5432`, I could connect to Postgres and enumerate:

- `direlore`
- `interq_db`
- `postgres`

Only `direlore` contained relevant tables. It looks like a canon/spec database, not the live Evennia object/attribute store. I did not find live Evennia runtime tables there.

That distinction matters:

- `direlore` can tell us what the design intends.
- the Python runtime tells us what is actually implemented.

## Live Physical Injury Model

The authoritative live injury path is:

- `engine/services/injury_service.py`
- `domain/wounds/constants.py`
- `domain/wounds/rules.py`

### Current Stored Wound Schema

Each body part stores:

- `external`
- `internal`
- `bruise`
- `bleed`
- `scar`
- `tended`
- `tend`
- `max`
- `vital`

Body parts are:

- `head`
- `chest`
- `abdomen`
- `back`
- `left_arm`
- `right_arm`
- `left_hand`
- `right_hand`
- `left_leg`
- `right_leg`

There is no live wound field for:

- `nerve`
- `neurological`
- `numbness`
- `paralysis`
- `cripple`
- `casting_disruption`

So in the current runtime, nerve damage is not a stored injury type.

## How Injuries Happen In The Live Runtime

The main application path is `InjuryService.apply_hit_wound(...)`, which delegates to `domain.wounds.rules.apply_hit_to_part(...)`.

### Wound Application Thresholds

From `domain/wounds/constants.py`:

- `impact = 8`
- `slice = 4`
- `pierce = 4`
- `stab = 4`
- `default = 9`

Additional application rules:

- critical hits force easier wound application
- if a body part already has trauma, follow-up wounds apply more easily
- low HP lowers the effective bar through `LOW_HP_WOUND_RATIO = 0.35`

### Damage-Type Behavior

From `domain/wounds/rules.py`:

- `impact` mainly increases `bruise`
- large `impact` hits also add `internal`
- critical `impact` adds more `internal`
- head impacts can add bleed and some external damage once bruise thresholds are crossed
- `slice`, `pierce`, and `stab` add `external` damage and bleeding more directly

### Worsening / Deep Injury Behavior

The closest live equivalent to a deep worsening injury is this rule:

- if a body part has `internal > 20`, bleed ticks can add more bleeding over time

That is still not nerve damage. It is worsening internal trauma.

## How Physical Injuries Affect Combat

The canonical penalty math lives in `domain.wounds.rules.derive_penalties(...)`.

### Derived Penalties

The function computes:

- `arm_penalty`
- `hand_penalty`
- `leg_penalty`
- `attack_accuracy_penalty`
- `attack_control_penalty`
- `evasion_penalty`
- `balance_penalty`
- `movement_cost_mult`
- `fatigue_recovery_mult`

### Penalty Math

Regional penalties are based on square roots of the highest relevant trauma values and then capped:

- `arm_penalty = min(25, int(sqrt(max(left_arm_trauma, right_arm_trauma))))`
- `hand_penalty = min(25, int(sqrt(max(left_hand_trauma, right_hand_trauma))))`
- `leg_penalty = min(25, int(sqrt(max(left_leg_trauma, right_leg_trauma))))`
- `head_penalty = min(20, int(sqrt(head_trauma)))`
- `core_penalty = min(18, int(sqrt(max(chest_trauma, abdomen_trauma))))`

Derived totals:

- `attack_accuracy_penalty = hand_penalty + max(0, head_penalty // 2)`
- `attack_control_penalty = arm_penalty + hand_penalty`
- `evasion_penalty = leg_penalty + max(0, core_penalty // 2)`
- `balance_penalty = leg_penalty + max(0, core_penalty // 2)`
- `movement_cost_mult = 1.0 + (leg_penalty / 40.0)`
- `fatigue_recovery_mult = max(0.5, 1.0 - (core_penalty / 40.0))`

### Where Combat Actually Consumes Them

The live combat resolver is `domain/combat/resolution.py`.

Confirmed live uses:

- `calculate_hit(...)` adds `attacker.get_arm_penalty()` into the attack penalty path
- `calculate_damage(...)` subtracts `attacker.get_hand_penalty()` directly from damage

That means the wound system already affects combat in real ways, but not under a nerve-specific label.

### What Nerve-Like Combat Effects Exist Only Indirectly

The closest current approximations are:

- arm trauma reducing accuracy/control
- hand trauma reducing damage output
- head trauma contributing to attack accuracy loss
- leg trauma harming movement, balance, and evasion
- chest/abdomen trauma slowing fatigue recovery and worsening balance/evasion

### What Is Not Implemented In Combat

There is no explicit live logic for:

- numb hands
- limb paralysis
- loss of grip from nerve damage
- spell interruption caused by nerve damage
- willpower defense degradation from nerve damage
- persistent neurological impairment on a body part

## How Injuries Affect Magic Casting In The Live Runtime

### Short Version

Physical wounds do not appear to directly feed into the live spell-control or cast-success math.

The main live spell path is:

- `engine/services/mana_service.py`
- `domain/mana/backlash.py`
- `engine/services/spell_effect_service.py`

### What Mana Control Uses

`ManaService._build_control_context(...)` uses:

- primary magic skill
- attunement skill
- arcana skill
- intelligence
- discipline
- profession
- attunement current and max

It does not read:

- wound penalties from `InjuryService.get_active_penalties(...)`
- `arm_penalty`
- `hand_penalty`
- `head_penalty`
- `leg_penalty`

### Live Conclusion For Casting

In the current runtime:

- physical wounds affect combat directly
- physical wounds do not appear to affect cast control directly
- any nerve-damage style effect on casting is therefore absent unless implemented indirectly through another subsystem

## The One Real Magic-Side Burden System: Empath Shock

The live magic-adjacent impairment system is empath shock, not nerve damage.

### Shock Thresholds

From `typeclasses/characters.py`:

- `clear = 0`
- `strained = 20`
- `dull = 50`
- `disconnected = 80`

### Shock Modifier Math

From `get_empath_shock_modifier()`:

- below `20`: `1.0`
- `20+`: `0.85`
- `50+`: `0.6`
- `80+`: `0.35`
- if overdrawn: multiply again by `0.8`

`get_empath_healing_modifier()` then multiplies:

- shock modifier
- recovery modifier from disease

The disease-side recovery rule is:

- `max(0.35, 1.0 - disease / 140.0)`

### Where Empath Shock Matters

Confirmed live effects:

- empath healing power is reduced by shock
- high shock can lock out or degrade empath actions
- `disconnected` breaks empath connections
- backlash can add shock through `ManaService._apply_backlash_payload(...)`
- circle sharing and vitality transfer can distribute or add shock

The structured spell service also scales healing power for empaths through `get_empath_healing_modifier()`.

### Important Distinction

Empath shock is not nerve damage.

It is a profession-specific burden/state system that happens to be the main live way that “internal strain hurts magical effectiveness.”

## How Healing Works Today

There are several distinct healing layers.

### 1. Physical Wound Treatment

Handled through `InjuryService` and wound rules.

Supported actions:

- `heal_wound(...)`
- `stop_bleeding(...)`
- `stabilize_wound(...)`
- scheduled bleed ticks
- natural recovery ticks

Recovery behavior from `domain/wounds/rules.py`:

- bruises recover over time
- external trauma recovers when not actively bleeding and under proper treatment
- internal trauma recovers more slowly and benefits from stabilization
- active combat impairs recovery timing

### 2. Tending / First Aid

`commands/cmd_tend.py` is the live physical treatment flow.

It:

- checks a bleeding body part
- rolls success from `first_aid` and mental stats
- applies a `tend` state
- heals a small amount immediately

This is a wound-management tool, not a generic magical heal.

### 3. Structured Healing Spells

`SpellEffectService._apply_healing_spell(...)` ultimately calls `StateService.apply_healing(...)`.

Important limitation:

- `StateService.apply_healing(...)` restores HP only

It does not directly reduce body-part fields like:

- `external`
- `internal`
- `bruise`
- `bleed`
- `scar`

So a structured healing spell can restore HP without actually clearing physical wound state.

### 4. Empath Self-Healing And Transfer

Empaths use a parallel wound vocabulary:

- `vitality`
- `bleeding`
- `poison`
- `disease`
- `fatigue`
- `trauma`

Important live behaviors:

- `heal self` routes to `mend_empath_self()`
- `heal wounds` routes to `take_empath_wound("bleeding")`
- `heal vitality` routes to `take_empath_wound("vitality")`

The archived Empath design notes also explicitly say:

- `heal wounds` reduces wound severity only
- `heal vitality` restores survivability only

That split matches the current system philosophy.

### 5. Shock Recovery / Centering

`center_empath_self()` is the main direct shock-reduction tool.

Current config values:

- `shock_reduction = 15`
- `fatigue_cost = 10`
- `roundtime = 2.5`
- recovery-zone bonus: `+8` shock reduction
- triage-zone bonus: `+3` shock reduction
- in combat: reduction is halved, fatigue cost increases, and roundtime increases

This is healing for empath burden, not treatment for body-part nerve trauma.

## Database Findings From `direlore`

The database did surface canonical/spec references to nerve damage.

### Canon Spell Rows Found

In `public.canon_spells`:

- `Mind Shout`
	- effect: `Nerve damage, AoE stun, sleep, disarm`
- `Sidhlot's Flaying`
	- effect: `Puncture damage, Slice damage, Targets damage to skin and nerves. Worsens bleeding wounds and interferes with tending`
- `Paralysis`
	- present as a spell name
- `Heal Wounds`
	- present as a spell name

### What That Means

The canon/spec layer clearly expects nerve-related gameplay to exist.

But the current runtime code does not implement a matching physical nerve channel, nerve-derived willpower penalty, or nerve-specific healing path.

So there is a real gap between:

- canon/spec intent in `direlore`
- current live implementation in the game server

## Research Docs That Support The Same Conclusion

Existing docs in the repo reinforce that intended design and current gap.

### `docs/research/combatV2.md`

The research note says Willpower defense is affected by:

- nerve damage
- stuns
- unconsciousness
- `Khri Serenity`
- `Cunning`

I did not find that willpower-vs-nerve rule implemented in the current live mana/combat path.

### `docs/research/spells.md`

The spell research note explicitly calls out:

- `Electrostatic Eddy (EE)`: cyclic AoE nerve damage / anti-hide pressure
- empath spellbook entries including `Heal Wounds` and `Paralysis`

Again, this supports that nerve damage exists as design intent and canon vocabulary, but not as a complete runtime subsystem yet.

## Bottom-Line Findings

### Implemented Now

- body-part trauma and bleeding
- combat penalties from wounds
- scar progression
- tending and stabilization
- empath shock and strain
- healing effectiveness reduction from empath shock

### Not Implemented Now

- explicit nerve-damage wound state
- nerve-damage math for targeted magic defense
- nerve-damage penalties to cast control
- nerve-specific recovery/healing procedures
- direct runtime bridge from canon nerve spells to wound/penalty state

### Spec / Canon Says Should Exist

- spells and research docs mention nerve damage, paralysis, skin-and-nerve damage, and wound-healing distinctions

## Implementation Suggestions

The important design decision is whether nerve damage should be:

- a brand-new stored wound channel
- or a derived status computed from existing trauma and selected spell effects

### Recommendation: Start Derived, Not Schema-Heavy

The cleanest first implementation is a derived nerve-status layer on top of existing wound state.

Why:

- the current wound model already has body locations
- the combat system already consumes derived penalties
- the mana/debilitation system already has hooks for target penalties and lockouts
- a derived layer avoids forcing a full migration of every wound record immediately

### Suggested Phase 1: Derived Nerve Trauma

Add a helper in the wound domain such as:

- `derive_nerve_penalties(injuries, effects=None)`

Suggested derivation rules:

- head trauma contributes to concentration / willpower disruption
- hand trauma contributes to fine-control penalties
- arm trauma contributes to manipulation penalties
- existing debilitation spells can directly add nerve severity to a target state
- certain spell effects can mark a temporary nerve injury state without editing stored body-part schema yet

Suggested derived outputs:

- `fine_motor_penalty`
- `willpower_penalty`
- `casting_integrity_penalty`
- `grip_failure_risk`
- `numbness_state`
- `paralysis_state`

### Suggested Phase 2: Hook It Into Combat And Magic

Combat hooks:

- increase attack penalties for hand/arm nerve injury beyond raw trauma
- add grip-drop or reload penalties for ranged weapons
- add occasional action degradation when severe nerve states are active

Magic hooks:

- subtract `casting_integrity_penalty` inside `ManaService._build_control_context(...)`
- subtract `willpower_penalty` in relevant spell contest defense contexts
- let high nerve severity increase backlash chance or failure-band downgrade only for affected spell classes

Important guardrail:

- do not reuse empath shock as the physical nerve-damage stat

Empath shock should remain its own profession burden system.

### Suggested Phase 3: Healing Model

If nerve damage is added, healing should stay split by responsibility.

Recommended treatment split:

- `tend` / stabilization: slows worsening but does not fully clear nerve injury
- `heal wounds`: reduces physical wound severity and can partially reduce associated nerve severity
- a dedicated advanced spell or ability: restores nerve function directly
- rest / long recovery: slowly clears mild derived nerve states when underlying trauma is gone

That keeps nerve damage dangerous without turning every heal into a full reset.

### Suggested Math Shape

If you want a minimal math model that matches the current code style, use square-root scaling plus caps, just like existing wound penalties.

Example:

- `fine_motor_penalty = min(20, int(sqrt(hand_trauma + nerve_bonus_hand)))`
- `willpower_penalty = min(20, int(sqrt(head_trauma + nerve_bonus_head)))`
- `casting_integrity_penalty = fine_motor_penalty + max(0, willpower_penalty // 2)`

That keeps the mechanic consistent with the existing wound system instead of introducing a completely alien formula.

### Suggested Spell Bridge

The strongest missing bridge right now is from canonical spell effects to runtime injury state.

For example:

- `Mind Shout` should probably apply a temporary nerve/willpower debilitation state
- `Sidhlot's Flaying` should probably add bleeding plus a temporary nerve-injury modifier that worsens tending efficiency
- `Paralysis` should probably route through the same debilitation/nerve framework rather than being a disconnected one-off

### Suggested Data Ownership

Keep the authority lines clean:

- wound domain owns physical trauma and recovery math
- combat resolver consumes combat penalties
- mana service consumes cast/control penalties
- spell effects apply temporary nerve states or debilitation payloads
- empath shock remains separate and profession-specific

That avoids mixing physical nerve injury with empath burden.

## Practical Conclusion

If the question is "does the live game currently have nerve damage?", the answer is:

- not as a first-class runtime mechanic

If the question is "does the design/canon expect nerve damage to exist?", the answer is:

- yes, definitely

If the question is "what should be implemented next?", the best next step is:

- add a derived nerve-status layer that bridges existing wound trauma and debilitation effects into combat and casting penalties, then add targeted healing hooks after that foundation is stable
