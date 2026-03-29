# DireMUD Microtasks 601-700 Report

## Scope

This report tracks implementation of MT 601-700 from [MT 601 - 700.md](c:/Users/gary/dragonsire/MT%20601%20-%20700.md), adapted to the current Evennia codebase.

Implementation rule used for this batch:
- When the document conflicts with an existing repo system, the document is treated as the source of truth.
- When the document assumes a new system that overlaps an existing repo system, the existing system is brought into line instead of creating a duplicate subsystem.

Current progress in this report:
- Completed MT 601-700

## Implemented

### MT 601-620
- Replaced the flat starter-skill list in `typeclasses/characters.py` with a metadata-backed `SKILL_REGISTRY` so survival skills can carry category, visibility, description, and starter-rank data.
- Added the missing survival skills:
  - `athletics`
  - `evasion`
  - `locksmithing`
  - `outdoorsmanship`
  - `skinning`
  - `perception`
  - `stealth`
  - `backstab`
  - `instinct`
  - `thanatology`
  - `thievery`
- Tagged survival skills with `category = survival` and marked `backstab`, `instinct`, `thanatology`, and `thievery` as `guild_locked`.
- Added survival skill descriptions directly in the registry for both shared and guild-linked survival skills.
- Implemented visibility-aware skill helpers on `Character`:
  - `get_available_skills()`
  - `is_skill_visible()`
  - `get_skill_metadata()`
  - `get_skill_detail_entry()`
  - `get_survival_skills()`
  - `get_shared_survival_skills()`
  - `get_hidden_survival_skills()`
- Updated starter skill baselines so:
  - `athletics` starts at rank `1`
  - `perception` starts at rank `1`
  - `evasion` starts at rank `1`
- Left `outdoorsmanship`, `locksmithing`, and `skinning` available through the shared-skill path without granting starter training.
- Added `SURVIVAL_TRAINING_HOOKS` placeholder mappings for future survival verb integration.
- Extended `commands/cmd_skills.py` so:
  - `skills <name>` shows name, rank, mindstate, description, and category
  - `skills all` groups output by category, including `Survival`
  - guild-locked survival skills remain hidden unless already learned
- Added admin-only `survivaldebug` in `commands/cmd_survivaldebug.py` to inspect shared visible, hidden, and learned survival skills.
- Registered the new admin/debug command in the default character cmdset.

## Validation

Validated outcomes for MT 601-620:
- Survival skills are present in the registry and `mechanical_lore` was not introduced.
- `skills all` can now include visible shared survival skills with zero rank while ordinary `skills` still only shows skills at rank `>= 1`.
- `skills <name>` detail output works for survival skills.
- Guild-locked survival skills remain hidden until manually learned.
- Starter baselines for `athletics`, `perception`, and `evasion` migrate safely through the existing default-normalization path.

### MT 621-640
- Added shared survival messaging helpers in `utils/survival_messaging.py` for actor, room, observer-conditional, and player-target-vs-NPC reactions.
- Added `get_detecting_observers()` plus new survival verb helpers in `typeclasses/characters.py`.
- Standardized stealth/perception messaging across `hide`, `search`, `observe`, `stalk`, ambush execution, and sneaking movement.
- Added `ForageAbility` in `typeclasses/abilities_survival.py` and registered it in the main ability registry.
- Added direct survival commands for `forage`, `skin`, `climb`, and `swim`, and registered them in the default cmdset.
- Implemented placeholder material creation for successful foraging and skinning outcomes.
- Added dead/skinnable validation for `skin` and graceful unsupported-terrain failure for `climb` and `swim`.

Validated outcomes for MT 621-640:
- Survival messaging helpers import cleanly and are reused across ability and combat paths.
- `hide` is quiet unless observer-specific detection occurs.
- `search` gives the actor reveal feedback, gives player targets spotted text, and pushes NPCs to alert awareness instead.
- `observe` is actor plus room only.
- `stalk` stays quiet unless target detection occurs.
- Ambush setup stays quiet; ambush execution is actor plus room plus player-target, while NPCs react through state.
- Sneaking movement suppresses general room broadcasts and only emits observer-specific detection text.
- `forage` works, creates placeholder bundles on success, and trains outdoorsmanship on meaningful attempts.
- `skin` only works on dead skinnable targets and trains skinning on valid attempts.
- `climb` and `swim` exist as athletics verbs and fail gracefully when unsupported.

### MT 641-660
- Added a repo-compatible box typeclass in `typeclasses/box.py` rather than the document's `typeclasses/objects/box.py` path, because this codebase already uses `typeclasses/objects.py` as a module.
- Added box helpers for lock/open/trap state:
  - `is_locked()`
  - `is_open()`
  - `has_active_trap()`
  - `can_be_opened()`
- Added `spawnbox` in `commands/cmd_spawnbox.py` with support for:
  - `spawnbox`
  - `spawnbox trap`
  - `spawnbox hard`
  - `spawnbox trap hard`
- Added locksmithing commands:
  - `inspect`
  - `disarm`
  - `pick`
  - `open`
- Registered those commands in the default character cmdset.
- Added new `Character` helpers in `typeclasses/characters.py`:
  - `is_box_target()`
  - `describe_lock_difficulty()`
  - `inspect_box()`
  - `locksmith_contest()`
  - `disarm_box()`
  - `trigger_box_trap()`
  - `apply_box_trap_effect()`
  - `has_lockpick()` placeholder
  - `pick_box()`
  - `open_box()`
- Kept box messaging aligned with the survival messaging model:
  - detailed actor feedback
  - light room activity text
  - no player-target messaging
- Added trap effects for `needle`, `blade`, `gas`, `explosive`, and fallback generic damage.
- Updated player-target detection in `utils/survival_messaging.py` so survival hostile/reveal text treats non-NPC `Character` objects as player targets instead of relying only on `target.account`.

Validated outcomes for MT 641-660:
- The full locksmithing loop works in smoke coverage:
  - `inspect box`
  - `disarm box`
  - `pick box`
  - `open box`
- Variants validated:
  - successful disarm of a trapped box
  - critical trap trigger on hard disarm failure
  - partial and successful pick results
  - blocked open on locked box
  - blocked open on active trap
  - successful open on unlocked safe box
  - already-unlocked and already-open guard paths
  - `spawnbox trap hard` spawning correct flags
- Smoke testing for MT 621-640 also passed after fixing player-target detection to match this repo's character model.

### MT 661-680
- Added a repo-compatible lockpick typeclass in `typeclasses/lockpick.py` rather than the document's nested `typeclasses/items/lockpick.py` path.
- Replaced the placeholder `has_lockpick()` path with a real carried-tool model:
  - `get_active_lockpick()`
  - `has_lockpick()` now checks for an actual carried lockpick
- Updated `pick_box()` so lockpicks now:
  - reduce durability on each attempt
  - break and delete themselves on zero durability
  - apply quality as a pick bonus during the contest
- Added `analyze` in `commands/cmd_analyze.py` and `harvest` in `commands/cmd_harvest.py`.
- Added `analyze_trap()`, `harvest_trap()`, and `create_trap_component()` in `typeclasses/characters.py`.
- Implemented one-time trap harvesting by clearing `box.db.last_disarmed_trap` after successful or partial harvest.
- Added `generate_box_loot()` and wired it into `open_box()` so opened boxes now create difficulty-scaled loot with light randomness.
- Extended `utils/survival_loot.py` with `create_simple_item()` for generic trap components and box loot.
- Added builder/debug `spawnlockpick` in `commands/cmd_spawnlockpick.py` so the new real-tool requirement is immediately testable in-game before any broader acquisition loop exists.
- Registered `analyze`, `harvest`, and `spawnlockpick` in the default character cmdset.

Validated outcomes for MT 661-680:
- The advanced locksmithing loop works in smoke coverage:
  - `spawnbox trap hard`
  - `spawnlockpick fine`
  - `inspect box`
  - `disarm box`
  - `analyze box`
  - `harvest box`
  - `pick box`
  - `open box`
- Variants validated:
  - active carried pick selection
  - pick durability reduction
  - pick breakage and deletion
  - analyze only after a disarmed trap exists
  - harvest only once per disarmed trap
  - trap component creation
  - difficulty-scaled loot creation on open
  - room messaging for loot spill events

### MT 681-700
- Upgraded lockpicks from a pure numeric-quality model to a grade-backed system in [typeclasses/lockpick.py](typeclasses/lockpick.py):
  - `grade` values: `rough`, `standard`, `fine`, `master`
  - internal quality mapping via `GRADE_VALUES`
  - display names now reflect grade directly
- Updated [commands/cmd_spawnlockpick.py](commands/cmd_spawnlockpick.py) to support grade spawning and the requested `spawnpick` alias:
  - `spawnpick rough`
  - `spawnpick standard`
  - `spawnpick fine`
  - `spawnpick master`
- Extended [commands/cmd_pick.py](commands/cmd_pick.py) to support explicit targeted tool selection:
  - `pick <box>`
  - `pick <box> with rough`
  - `pick <box> with master`
- Added `get_lockpick_by_grade()` in [typeclasses/characters.py](typeclasses/characters.py).
- Updated `pick_box()` in [typeclasses/characters.py](typeclasses/characters.py) so:
  - it accepts an optional explicit `pick`
  - the chosen pick grade is echoed to the actor
  - break chance scales by lock difficulty, locksmithing skill, and pick grade quality
  - durability wear scales by difficulty
  - a soft warning appears before break when durability is low
- Expanded trap effects in [typeclasses/characters.py](typeclasses/characters.py):
  - `alarm` alerts room actors through awareness state
  - `smoke` applies a temporary perception penalty attribute
  - `barb` causes direct injury plus bleed on an arm using the current injury model
- Improved harvest output in [typeclasses/characters.py](typeclasses/characters.py):
  - low / standard / high component tiers
  - rare component chance
  - tiered component naming keyed off trap type and outcome quality

Validated outcomes for MT 681-700:
- The targeted-pick flow works in smoke coverage:
  - `spawnpick rough`
  - `spawnpick master`
  - `pick <box> with rough`
  - `pick <box> with master`
- Variants validated:
  - first matching grade pick is selected
  - explicit grade selection overrides default active-pick selection
  - scaled wear reduces durability by lock difficulty
  - low-durability warning appears before break
  - scaled breakage can snap and delete a pick
  - `alarm`, `smoke`, and `barb` trap effects all apply correctly
  - strong harvest can yield rare high-tier components
