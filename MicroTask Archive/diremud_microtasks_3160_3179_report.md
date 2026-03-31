# DireMUD Microtasks 3160-3179 Report

## Scope

Reconciliation pass only. No new parallel systems were introduced.

## 3160-3163 Profession vs Guild Decision

- Guild storage today: `Character.db.guild` in `typeclasses/characters.py`.
- Guild command today: `commands/cmd_guild.py`.
- Guild usage before this pass: skill gating, spell gating, ability gating, character payload, and the `profession` command alias.
- Profession usage before this pass: design docs only, plus the `profession` alias on `guild`.
- Decision locked in: Profession = player identity. Guild = world structure, location, trainer, or NPC-facing affiliation.
- Code alignment completed in this pass:
  - Removed the `profession` alias from `guild`.
  - Added `db.profession` as the primary identity field with backward-compatible fallback from legacy `db.guild`.
  - Added a dedicated `profession` command instead of overloading `guild`.

## 3164-3167 Skill System Integration

- Actual learning application point: `Character.use_skill()` in `typeclasses/characters.py`.
- Learning storage: `Character.db.skills[skill_name]` with `rank` and `mindstate`.
- Learning helper path:
  - command or ability calls `Character.use_skill()`
  - `use_skill()` calls `get_learning_amount()`
  - resulting gain is capped via `get_mindstate_cap()`
  - learning is applied through `update_skill(..., mindstate=...)`
- Full traced flow example:
  - `commands/cmd_search.py` calls `self.caller.use_ability("search")`
  - `Character.use_ability()` resolves `SearchAbility`
  - `typeclasses/abilities_perception.py` executes `SearchAbility.execute()`
  - `SearchAbility.execute()` calls `user.use_skill("perception", apply_roundtime=False, emit_placeholder=False)`
  - `Character.use_skill()` computes and applies mindstate gain
  - resulting state changes include awareness updates and client syncs through existing character state methods
- Hook marker inserted at the actual learning application point:
  - `# profession weight hook here`
- Duplicate XP check:
  - No active `apply_xp`, `total_xp`, `advance_profession`, or `profession_rank` scaffolding exists in live Python code.
  - No duplicate XP system was introduced.

## 3168-3171 Ability System Reuse

- Existing ability base and registry: `typeclasses/abilities.py`.
- Registration model: each ability module imports `register_ability(...)` and registers concrete ability instances into `ABILITY_REGISTRY`.
- Current modules registering abilities:
  - `typeclasses/abilities_stealth.py`
  - `typeclasses/abilities_perception.py`
  - `typeclasses/abilities_survival.py`
- Invocation path:
  - command calls `Character.use_ability(key)` or a direct command wrapper
  - `Character.use_ability()` calls `get_ability(key)`
  - requirement checks run in `meets_ability_requirements()`
  - profession/guild-style access check runs in `passes_guild_check()`
  - ability-specific logic runs in `ability.can_use()` and `ability.execute()`
- Cooldown/resource attachment point today:
  - roundtime attaches in `Character.use_ability()` via `ability.roundtime`
  - cooldowns already attach through character state, for example spell cooldowns in `set_spell_cooldown()`
  - profession resources should attach through this existing state/payload path, not a new framework
- Decision locked in: profession abilities must plug into the existing ability system.
- Hook marker inserted at ability resolution:
  - `# profession ability injection here`

## 3172-3174 NPC / Trainer Structure

- NPC base type confirmed in `typeclasses/npcs.py`.
- NPC model today: `NPC` extends `Character` and adds AI behavior through methods like `ai_tick()`, `process_ai_decision()`, `ai_search()`, and `npc_combat_tick()`.
- Decision locked in: Trainer = specialized NPC type inside the existing NPC system.
- Constraint preserved: no `typeclasses/npcs/` package was created.

## 3175-3177 Client / UI Integration

- Active browser client listeners confirmed in `web/static/webclient/js/dragonsire-browser-v2.js`.
- Existing message types listened for there:
  - `text`
  - `prompt`
  - `map`
  - `character`
  - `combat`
  - `chat`
  - `logged_in`
  - `connection_open`
  - `connection_close`
  - `default`
- New message type required later: `subsystem`.
- Handler marker inserted in the live listener block:
  - `// subsystem handler goes here`

## 3178-3179 Stealth / Awareness Mapping

- Existing files involved:
  - `typeclasses/characters.py`
  - `typeclasses/abilities_stealth.py`
  - `typeclasses/abilities_perception.py`
  - `commands/cmd_hide.py`
  - `commands/cmd_search.py`
  - `commands/cmd_observe.py`
  - `commands/cmd_sneak.py`
  - `commands/cmd_stalk.py`
  - `commands/cmd_ambush.py`
  - `commands/cmd_attack.py`
  - `typeclasses/npcs.py`
  - `server/conf/at_server_startstop.py`
  - `utils/survival_messaging.py`
- Existing system to new intent mapping:
  - Current awareness states `normal`, `alert`, `searching`, `unaware` should map to a future numeric or hybrid awareness model, not be deleted first.
  - Current detection contests already run through `get_perception_total()` versus `get_stealth_total() + get_hidden_strength()` and should be extended, not replaced.
  - Current hidden state already lives in `states["hidden"]` with strength metadata and should remain the stealth anchor.
  - Current awareness changes already propagate through commands, abilities, combat reactions, NPC AI, and survival messaging, so future profession behavior must layer onto these transitions instead of branching around them.

## Result

- One identity field now exists: `db.profession`.
- Guild remains available as a separate world-facing field.
- Learning still uses one pipeline.
- Abilities still use one registry and one resolution path.
- NPCs still use one type hierarchy.
- Stealth and awareness still use one system.