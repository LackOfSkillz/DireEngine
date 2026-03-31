# DireMUD Microtasks 481-600 Report

## Scope

This report tracks implementation of MT 481-600 from [MT 481 - 600.md](c:/Users/gary/dragonsire/MT%20481%20-%20600.md), adapted to the current Evennia codebase.

Implementation rule used for this batch:
- When the document conflicts with an existing repo system, the document is treated as the source of truth.
- When the document assumes a new system that overlaps an existing repo system, the existing system is brought into line instead of creating a duplicate subsystem.

Current progress in this report:
- Completed MT 481-600
- Stabilization Pass v2 applied for post-implementation combat/healing tuning

## Implemented

### MT 481-485
- Added shared `Character.is_dead()` in `typeclasses/characters.py` so NPC AI can follow the document's dead-check flow without duplicating death logic in `NPC`.
- Reworked `typeclasses/npcs.py` around the document's new AI chain:
  - `ai_tick()`
  - `process_ai_decision()`
  - `evaluate_combat_state()`
  - `ai_attack()`
  - `ai_retreat()`
- Preserved existing repo combat timing by keeping roundtime and surprise gating in the new `ai_tick()` path.
- Updated `server/conf/at_server_startstop.py` to call `ai_tick()` for active NPCs instead of the older hard-coded NPC combat routine.
- Adjusted the status-tick idle gate so NPCs with a current target are still processed even if they would otherwise look idle.

### MT 486-490
- Added shared `Character.is_engaged_with()` in `typeclasses/characters.py`.
- Added `NPC.ai_advance()` in `typeclasses/npcs.py`.
- Updated `evaluate_combat_state()` so NPCs now:
  - `advance` when they have a target but are not yet engaged
  - `retreat` when below the MT threshold
  - `attack` otherwise
- Updated `ai_retreat()` to follow the MT spec:
  - 60% chance to attempt retreat
  - otherwise emits `You fail to break away!`
- Added retreat follow behavior so an in-combat target immediately attempts `advance` after the NPC tries to retreat.

### MT 491-495
- Updated `process_ai_decision()` so hidden targets trigger stealth-aware behavior instead of normal combat evaluation.
- Added `NPC.ai_search()`.
- Added target memory via `last_seen_target` state storage in `ai_attack()`.
- Added lost-target reacquisition in `process_ai_decision()` by matching `last_seen_target` against current room contents.
- Added stealth aggression behavior so hidden targets push NPC awareness to `searching` before the NPC uses `search`.

### MT 496-500
- Added an explicit NPC ambush-reaction safeguard in `Character.apply_damage()` so surprised NPCs shift to `alert` awareness as part of taking damage, matching the task document instead of relying on indirect combat side effects.
- Updated `NPC.evaluate_combat_state()` with the MT panic branch:
  - below 20% HP: emits `The creature panics!` and retreats
  - below 30% HP: retreats
  - otherwise: attacks
- Added healthy-NPC aggression scaling in `NPC.ai_attack()` by setting a temporary `ai_accuracy_bonus` state when HP is above 70%.
- Hooked the temporary `ai_accuracy_bonus` into the live hit calculation in `commands/cmd_attack.py`.
- Added `combat_timer` persistence handling in `NPC.ai_tick()`:
  - initializes to `5` while a target is active
  - decays by `1` per AI tick when the target is no longer available

### MT 501-520
- Aligned the existing `typeclasses/weapons.py` typeclass with the document's weapon profile shape instead of replacing the repo's current weapon system.
- Added explicit weapon-profile fields used by the task document:
  - `type`
  - `damage`
  - `balance`
  - `speed`
- Added default weapon unlock tiers on the typeclass:
  - rank 20 -> `damage_bonus`
  - rank 40 -> `flavor`
- Added shared `Character.get_wielded_weapon()` in `typeclasses/characters.py` as the document's public accessor, mapped to the repo's existing equipped-weapon system.
- Updated `commands/cmd_attack.py` to use `get_wielded_weapon()` when available.
- Aligned attack resolution with the document's weapon expectations:
  - low-skill accuracy penalty below rank 10
  - high-skill flat damage bonus above rank 30
  - unlock-based `damage_bonus`
  - speed-driven roundtime via weapon `speed`
- Extended `commands/cmd_spawnweapon.py` training weapons so their profiles now include the document's weapon fields and unlock definitions.
- Fixed weapon unlock evaluation to accept Evennia mapping-backed attribute values, not only plain Python dicts.

### MT 521-540
- Aligned the existing armor typeclass in `typeclasses/armor.py` with the document's armor profile model:
  - `armor_type`
  - `protection`
  - `hindrance`
  - `coverage`
- Added `ARMOR_PRESETS` and preset application on armor creation.
- Added default armor unlock tiers:
  - rank 20 -> `protection_bonus`
  - rank 40 -> `hindrance_reduction`
- Added `Armor.get_armor_profile()`.
- Added shared aliases on `Character` so the current repo equipment system matches the task document's API:
  - `get_worn_armor()`
  - `get_armor_for_bodypart()`
- Updated coverage lookup so armor can use either legacy `covers` or document-style `coverage`.
- Added armor helper methods on `Character` for document-style scaling:
  - `get_armor_protection_value()`
  - `get_armor_hindrance_value()`
- Updated `get_total_hindrance()` so hindrance now derives from the document-style armor model with skill mitigation and unlock reduction.
- Updated `commands/cmd_attack.py` so armor now applies document-style flat protection reduction and armor-absorption messaging.
- Updated `commands/cmd_spawnwearable.py` armor builders to use document-style armor type names, coverage fields, hindrance fields, and unlock definitions.

### MT 541-560
- Kept the repo's existing `db.injuries` model as the canonical body-part injury store and aligned it to the document instead of introducing a second `db.body` structure.
- Added `Character.ensure_body_state()` as a compatibility wrapper around the current injury-default initialization path.
- Added document-style injury helpers in `typeclasses/characters.py`:
  - `get_injury_severity()`
  - `describe_bodypart()`
- Added direct functional-penalty helpers:
  - `get_arm_penalty()`
  - `get_leg_penalty()`
  - `get_hand_penalty()`
- Updated `get_perception_total()` so head injuries now reduce perception.
- Updated `apply_damage()` so external/internal values are capped at 100, severe-injury messaging is emitted, and high internal chest damage warns about critical condition.
- Updated `commands/cmd_attack.py` so arm damage reduces accuracy and hand damage reduces outgoing damage.
- Updated `commands/cmd_retreat.py` so leg damage reduces retreat effectiveness.
- Updated `process_bleed()` so internal injuries above the MT threshold worsen bleeding, bleeding emits explicit bleed-pressure messaging, and bleedout can mark the target dead.

### MT 561-580
- Extended the existing injury records with document-style tend state instead of replacing the repo's injury model:
  - `tend.strength`
  - `tend.duration`
- Updated injury default-copy and migration logic so older characters gain a valid tend state automatically.
- Added first-aid/tending helpers on `Character`:
  - `is_tended()`
  - `get_tend_strength()`
  - `get_tend_duration()`
  - `apply_tend()`
- Reworked `commands/cmd_tend.py` so successful tending now applies temporary suppression instead of permanently zeroing bleed.
- Preserved the existing repo improvement where `tend self` and `tend <target>` auto-select the first bleeding part when the input is not an explicit body part.
- Updated `process_bleed()` so tend suppression now:
  - reduces effective bleed while active
  - decays duration over time
  - decays faster for severe wounds
  - decays faster during combat
  - emits reopen messaging when a tended wound starts bleeding freely again
- Updated `Character.at_post_move()` so movement also degrades active tending.
- Updated tend success messaging so it now reflects bandaging/tending rather than claiming the wound is permanently healed.

### MT 581-600
- Added the `empathy` skill to the shared starter-skill/default skill pipeline in `typeclasses/characters.py`.
- Added empath capability helpers on `Character`:
  - `is_empath()`
  - `get_empath_load()`
  - `is_overloaded()`
- Added injury-transfer helpers aligned to the current injury model instead of the document's unused `db.body` pseudocode:
  - `transfer_bodypart()`
  - `transfer_wounds()`
- Added overload messaging and overload failure behavior to the wound-transfer path.
- Added empath backlash damage when accumulated empath load exceeds the high-risk threshold.
- Added `commands/cmd_diagnose.py` for per-body-part wound assessment and overall condition reporting.
- Added `commands/cmd_heal.py` for empath wound transfer.
- Registered `diagnose` and `heal` in the default character cmdset.

### Stabilization Pass v2
- Updated `commands/cmd_attack.py` so weapon balance contributes less aggressively to accuracy, reducing the oversized effect of modest balance differences.
- Removed the temporary `ai_accuracy_bonus` state flow. Healthy-NPC aggression is now applied directly in attack resolution based on current HP ratio.
- Added aggregate armor protection handling in `typeclasses/characters.py` so overlapping armor pieces contribute through a combined protection pool with a single averaged skill modifier instead of multiplying each layer independently.
- Softened limb injury penalties by changing arm, leg, and hand penalties to a nonlinear square-root curve.
- Strengthened bleed pressure in `process_bleed()` so HP loss scales above the raw bleed total.
- Strengthened repeat-tend diminishing returns by halving tend strength when a wound is already tended or was just recently bandaged.
- Added recent-tend timestamp tracking to the injury tend state for spam-resistant rebinding behavior.
- Added empath transfer budget limits so each heal action only moves a capped total amount of wound load.
- Added empath instability so some transfers introduce extra internal strain on the empath, making the system less deterministic and safer to tune.

### Stabilization Follow-Up
- Refined armor skill blending to weight skill modifiers by coverage significance instead of using a flat average, reducing mixed-armor optimization edge cases.
- Added explicit `RECENT_TEND_WINDOW = 10` so repeat-tend timing is defined in code rather than implied by a magic number.
- Softened heavy bleed HP loss using a taper above 10 total bleed so stacked bleeds remain dangerous without producing as many sudden death cliffs.
- Updated empath instability to scale with current empath load, capping at 50% risk.
- Changed empath transfer budgeting to distribute per-action healing proportionally across wounded body parts rather than draining parts strictly in body-order.
- Adjusted NPC retreat follow-up so the opponent's auto-advance chance now shifts based on relative HP ratios instead of always being symmetric.
- Added explicit 25-point hard caps around injury-derived limb penalties when applied in combat calculations.
- Preserved the separately-added 2 minute minimum tend duration; this follow-up did not shorten that rebleed window.

## Validation

Validated via `evennia reload` plus controlled `evennia shell` checks against the live `training dummy` NPC and disposable in-room temporary targets.

Validated outcomes for MT 481-485:
- NPCs expose `ai_tick()`.
- non-NPC Characters do not expose `ai_tick()`.
- `process_ai_decision()` safely no-ops with no target.
- `evaluate_combat_state()` routes to `ai_attack()` above the threshold.
- `evaluate_combat_state()` routes to `ai_retreat()` below the threshold.

Representative validation result:

```python
{
    'npc_has_ai_tick': True,
    'char_has_ai_tick': False,
    'events': [('attack', 'jekar'), ('retreat', 'jekar'), ('attack', 'jekar')]
}
```

Validated outcomes for MT 486-490:
- NPCs attempt `advance` when they have a target but are not engaged.
- NPC retreat path issues `retreat` on success-chance pass.
- retreat follow behavior makes the target attempt `advance`.
- failed retreat chance emits the expected failure message.

Representative validation result:

```python
{
    'events': [('npc', 'advance jekar'), ('npc', 'retreat'), ('char', 'advance training dummy')],
    'msgs': ['You fail to break away!']
}
```

Validated outcomes for MT 491-495:
- hidden targets trigger `search`
- NPC awareness shifts to `searching`
- successful attack-path evaluation stores `last_seen_target`
- lost targets are reacquired from memory if still present in the room

Representative validation result:

```python
{
    'hidden_event': ['search'],
    'awareness': 'searching',
    'remembered': True,
    'reacquired': True,
    'events': [('attack', 'ai_tmp_target'), ('attack', 'ai_tmp_target')]
}
```

  Validated outcomes for MT 496-500:
  - healthy NPC attack path applies the +5 aggression bonus
  - panic branch triggers below 20% HP
  - surprised NPCs shift to `alert` when damaged
  - combat persistence timer starts at `5` and decays on later ticks

  Representative validation result:

## Stabilization Validation

Validated outcomes for the stabilization pass:
- `commands/cmd_attack.py`, `typeclasses/characters.py`, and `typeclasses/npcs.py` compile successfully with `python -m py_compile`.
- Static analysis reports no new errors in the touched files beyond the pre-existing Pylance Evennia import-resolution warning in `typeclasses/characters.py`.
- Live Evennia runtime validation could not be executed from this workspace because the configured virtual environment is missing Django/Evennia runtime packages.

Validated follow-up outcomes:
- `RECENT_TEND_WINDOW` resolves to `10` in the live game environment.
- Bleed loss at total bleed `12` now resolves to `13` HP instead of continuing to scale more sharply.
- A fresh tend still records a `120` second minimum active window after the follow-up stabilization changes.

Representative validation command:

```powershell
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m py_compile commands/cmd_attack.py typeclasses/characters.py typeclasses/npcs.py
```

Representative follow-up validation result:

```python
{
  'recent_tend_window': 10,
  'bleed_hp_loss_at_12': 13,
  'tend_min_seconds': 120.0,
}
```

  ```python
  {
    'high_hp_bonus': ('attack jekar', 5),
    'panic_msg': True,
    'ambush_alert': 'alert',
    'timer_start': 5,
    'timer_after_one': 4
  }
  ```

  Validated outcomes for MT 501-520:
  - weapon profiles expose the document-required fields
  - `get_wielded_weapon()` resolves the equipped weapon correctly
  - unlock tiers now apply at the expected skill thresholds
  - speed-based roundtime path remains valid

  Representative validation results:

  ```python
  {
    'profile_keys': {
      'type': 'light_edge',
      'damage': 5,
      'balance': 55,
      'speed': 2.5,
      'skill': 'light_edge'
    },
    'wielded_accessor': True
  }
  ```

  ```python
  {
    'effects_35': {'damage_bonus': 2},
    'effects_45': {'damage_bonus': 2, 'flavor': True}
  }
  ```

  Validated outcomes for MT 521-540:
  - armor profiles expose the document-required fields
  - body-part coverage lookup resolves worn armor correctly
  - low skill reduces protection effectiveness
  - higher skill improves protection and reduces hindrance
  - total hindrance aggregates from the aligned armor model

  Representative validation result:

  ```python
  {
    'profile': {
      'type': 'light_armor',
      'protection': 2,
      'hindrance': 1,
      'coverage': ['chest', 'abdomen', 'back']
    },
    'covering': ['mt540_test_armor'],
    'low_prot': 1.6,
    'high_prot': 3.4,
    'low_hind': 1.0,
    'high_hind': 0.8,
    'totals': (0.8, 0.8)
  }
  ```

  Validated outcomes for MT 541-560:
  - body-part injury descriptions now expose document-style severity wording
  - head injuries reduce perception total
  - arm, leg, and hand injuries now produce direct combat penalties
  - severe-value thresholds resolve through the document-style severity helper
  - bleed processing now emits active bleed-pressure messaging and escalates with internal damage

  Representative validation result:

  ```python
  {
    'desc': 'Your right arm is light wounded and minor internally injured.',
    'severity_31': 'severe',
    'arm_penalty': 3,
    'leg_penalty': 4,
    'hand_penalty': 2,
    'perception_total': 17,
    'bleed_hp': 1,
    'bleed_dead': False,
    'msgs': ['You bleed from your wounds.']
  }
  ```

  Validated outcomes for MT 561-580:
  - tending now stores strength and duration per body part
  - tended wounds count as actively tended while duration remains above 0
  - bleed processing uses the suppression state instead of permanent bleed removal
  - tended wounds reopen after the tend duration expires

  Representative validation result:

  ```python
  {
    'tend_state': {'strength': 6, 'duration': 15},
    'tended_now': True,
    'after_first': (100, {'strength': 6, 'duration': 14}, True),
    'reopened': True
  }
  ```

  Validated outcomes for MT 581-600:
  - empath-marked characters can transfer wounds using the current injury model
  - target external, internal, and bleed values decrease during transfer
  - empath external, internal, and bleed values increase during transfer
  - empath load is computed from accumulated transferred injuries
  - overload state is exposed through the new helper methods

  Representative validation result:

  ```python
  {
    'before': (12, 6, 2),
    'after_target': (6, 1, 0),
    'after_char': (6, 5, 2),
    'load': 11,
    'overloaded': False
  }
  ```

## Notes

- The repo already had `npc_combat_tick()` and range/pursuit helpers. For MT481-495, the decision flow was centralized into the new `ai_tick()` chain instead of creating a second competing AI system.
- Existing roundtime and surprise handling were preserved inside `ai_tick()` even though the task document's minimal pseudocode did not include them; removing them would have regressed current combat behavior.
- The only standing tool-reported issue during this batch remains the existing Pylance import warning for Evennia's `DefaultCharacter` import path in `typeclasses/characters.py`; it did not block reload or runtime validation.