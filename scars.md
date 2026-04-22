# Scar Mechanics Research

## Executive Summary

The live game does implement scars as a first-class stored wound property, but scars are currently much narrower than the rest of the wound system.

What scars do today:

- persist per body part as a stored integer
- increase when a wound crosses specific external/internal trauma thresholds
- show up in wound descriptions and wound event messaging
- determine which body part is targeted by empath scar healing

What scars do not do today:

- directly affect combat penalties
- directly affect spellcasting
- passively heal through normal wound recovery
- clear through ordinary wound-healing commands or HP healing

The only live scar-removal path I found is empathic `heal scars`, which removes exactly one scar from the subject's most-scarred body part per successful use.

## Where Scars Live

The authoritative runtime path is:

- `domain/wounds/constants.py`
- `domain/wounds/rules.py`
- `engine/services/injury_service.py`
- `typeclasses/characters.py`
- `commands/cmd_heal_scars.py`

Each body part includes a stored `scar` field in the default injury schema.

Tracked body parts are:

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

So scars are not just flavor text. They are persistent wound-state data stored alongside:

- `external`
- `internal`
- `bruise`
- `bleed`
- `tended`
- `tend`
- `max`
- `vital`

Character injury normalization preserves the `scar` integer when injury state is merged back onto the character.

## Scar Gain Rules

Scar gain is handled in `domain.wounds.rules.apply_scar_progress(...)`.

Important detail:

- scar gain uses only `external` and `internal`
- `bruise` does not contribute directly to scar math

The function computes:

- `previous_peak = max(previous_external, previous_internal)`
- `previous_trauma = previous_external + previous_internal`
- `current_peak = max(current_external, current_internal)`
- `current_trauma = current_external + current_internal`

Configured scar thresholds are:

- `severity_threshold = 45`
- `trauma_threshold = 70`
- `repeat_gate = 25`
- `repeat_threshold = 15`
- `max_scars = 10`

Scar gain starts at `0` and increases by these rules:

1. Add `1` scar if `previous_peak < 45` and `current_peak >= 45`
2. Add `1` scar if `previous_trauma < 70` and `current_trauma >= 70`
3. Add `1` scar if `previous_trauma >= 25` and `(current_trauma - previous_trauma) >= 15`

Then the stored scar count becomes:

- `scar = min(10, existing_scar + scar_gain)`

That means a single wound application can add more than one scar if it crosses multiple gates at once.

## When Scar Gain Happens

Scar progression is only checked after a wound is actually applied.

That means the hit must first pass the normal wound-application gate in `apply_hit_to_part(...)`:

- damage at or above the type threshold
- or critical hit
- or the body part already has trauma
- or the target is at low HP and the reduced threshold rule applies

Once the wound is applied and the body part's `external` / `internal` values are updated, `apply_scar_progress(...)` runs immediately.

So scars are tied to wound severity progression, not to healing or to a separate periodic scar pass.

## Damage Types And Scar Interaction

Scars do not look at damage type directly. They only care about the resulting `external` and `internal` totals.

That still means damage type matters indirectly because different attack types fill those fields differently:

- `impact` mainly builds `bruise`
- large or critical `impact` can add `internal`
- `slice`, `pierce`, and `stab` add `external` more directly

In practice:

- slicing and piercing wounds are more naturally aligned with scar gain because they build `external` faster
- impact can still contribute to scars when it pushes `internal` high enough
- pure bruising by itself does not create scars unless it also causes enough `internal` or `external` damage

## What Scars Affect Right Now

### 1. Wound Description Text

`get_body_part_wound_descriptions(...)` adds:

- `marked by old scarring` if `scar == 1`
- `marked by heavy scarring` if `scar > 1`

That is the primary descriptive use of scars in the current runtime.

### 2. Wound Event Messaging

When `scar_gain > 0`, `InjuryService.apply_hit_wound(...)` emits an `apply_wound` event with kind `scar_gain`.

The injury presenter renders that event as:

- `The hurt leaves lasting damage in your <part>.`

So the player gets immediate feedback when a hit creates lasting scarring.

### 3. Empath Target Selection

`get_most_scarred_part()` scans all body parts and returns the one with the highest stored scar count.

That function is used by empath scar healing to decide what gets treated.

## What Scars Do Not Affect

Scars are not currently part of the active wound penalty math.

`domain.wounds.rules.derive_penalties(...)` only uses current trauma values from:

- head
- chest / abdomen
- arms
- hands
- legs

Its outputs are:

- `arm_penalty`
- `hand_penalty`
- `leg_penalty`
- `attack_accuracy_penalty`
- `attack_control_penalty`
- `evasion_penalty`
- `balance_penalty`
- `movement_cost_mult`
- `fatigue_recovery_mult`

Scar count is not read anywhere in those formulas.

That means scars currently do not:

- reduce accuracy
- reduce damage
- slow movement
- worsen balance
- worsen fatigue recovery
- weaken magic control
- alter defense rolls

They are persistent state, but not an active penalty source.

## Normal Healing And Scars

### Direct Wound Healing

`InjuryService.heal_wound(...)` calls `domain.wounds.rules.heal_part(...)`.

`heal_part(...)` heals in this order:

1. `external`
2. `bruise`
3. `internal`

It never reduces `scar`.

### Natural Recovery

`apply_natural_recovery(...)` performs slow periodic recovery when not in combat.

Its live behavior is:

- `bruise` decreases by `1`
- `external` decreases by `1` only if the part is not bleeding and is stabilized or tended
- `internal` decreases by `1` only if stabilized
- tending state is cleared once trauma and bleed are gone

Again, it never changes `scar`.

### Bleeding / Stabilization / Tending

These systems also do not remove scars.

- `stop_bleeding(...)` only clears bleed and resets tend state
- `stabilize_wound(...)` only affects tending, stabilization strength, and optional ordinary wound healing
- `tend` is a wound-management and recovery aid, not a scar-removal mechanic

### HP Healing

Structured spell healing routes through HP restoration, not body-part scar changes.

So HP can recover while the scar count on body parts stays untouched.

## Confirmed Persistence Behavior

The repo's gameplay harness explicitly verifies that normal healing does not remove scars.

In `diretest.py`, a patient is wounded badly enough to scar, then receives normal body-part healing, and the test asserts that the scar count remains unchanged.

That matches the live code path exactly.

## Scar Healing

The only live scar-healing mechanic I found is empathic `heal scars`.

Command entry:

- `heal scars`
- `heal scars self`
- `heal scars <target>`

### Requirements

The caller must:

- be an empath
- have the required empath unlock

Unlock rules:

- self-healing scars uses `internal_scar_transfer`
- healing another person's scars uses `external_scar_transfer`

Additional target rule:

- if healing another character, they must be in the same room

### Resolution Logic

`heal_empath_scars(...)` does the following:

1. resolve the subject
2. choose the subject's most-scarred body part
3. fail if no part has scars
4. pass a life-mana gate with parameter `8`
5. reduce that part's scar count by exactly `1`
6. add empath fatigue by `12`
7. add empath shock by `3`
8. set roundtime to `3.5`
9. award empathy experience for `scar_heal`

The actual scar update is:

- `scar = max(0, scar - 1)`

So scar healing is discrete, not scaled. One successful use removes one scar.

### Messaging

If healing another target:

- target sees: `The old pull in your <part> eases a little.`
- healer sees: `You work at the old scarring in <target>'s <part>.`

If healing self:

- healer sees: `You work at the old scarring in your <part>.`

### Experience Award

The empathy XP award uses:

- action key: `scar_heal`
- difficulty: `18`
- amount: effectively the pre-heal scar count on that part

So more heavily scarred parts grant a larger training amount when treated.

## Practical Mechanics Summary

If the question is "how do scars work right now?", the live answer is:

- scars are stored per body part
- scars are gained when external/internal wound severity crosses lasting-damage thresholds
- scars persist through ordinary healing and recovery
- scars mainly affect description and empath scar-treatment targeting
- scars do not currently feed combat or magic formulas
- scars are removed only through empath `heal scars`, one scar at a time

## Bottom Line

Scars are implemented as persistent wound history, not as an active debuff layer.

The runtime treats them as lasting marks that can accumulate from serious trauma and that require specialized empathic treatment to reduce. Ordinary wound care heals current damage, but it does not erase the lasting scar record.