# DireSim As Built

This file records every DireSim-related code or spec change with enough detail for another developer to recreate the result.

## Entry Format

Use this format for each change:

### YYYY-MM-DD HH:MM:SS
Summary: one-line description of the change

Files touched:
- path/to/file

Why:
- brief rationale for the change

What changed:
- brief implementation notes

Recreation snippet:
```text
paste the key commands, patch excerpt, or code snippet needed to reproduce the result
```

Validation:
- what was checked

---

### 2026-04-15 05:57:06
Summary: created the initial DireSim as-built log and established the required entry format for future DireSim work

Files touched:
- diresimAsbuilt.md

Why:
- preserve a chronological implementation record for the DireSim migration
- make future kernel, cache, handler, and rollout changes reproducible by another developer

What changed:
- added a dedicated as-built markdown log for DireSim work
- defined a fixed entry structure with timestamp, rationale, implementation notes, recreation snippet, and validation section

Recreation snippet:
```text
Create a new file named diresimAsbuilt.md at the repo root.
Add a header, an entry template, and an initial timestamped record documenting file creation.
```

Validation:
- file created successfully in the workspace

---

### 2026-04-15 06:09:39
Summary: implemented DireSim Phase 2 shell with kernel, budgets, guard zone service, startup bootstrap, and per-guard execution gate disabled

Files touched:
- world/simulation/__init__.py
- world/simulation/budgets.py
- world/simulation/kernel.py
- world/simulation/metrics.py
- world/simulation/registry.py
- world/simulation/service.py
- world/simulation/zones/__init__.py
- world/simulation/zones/guard_zone_service.py
- typeclasses/scripts.py
- typeclasses/npcs/guard.py
- server/conf/settings.py
- server/conf/at_server_startstop.py
- diresimAsbuilt.md

Why:
- stand up the Phase 2 kernel shell without introducing new guard AI behavior
- replace per-guard execution ownership with a bounded zone-service scaffold
- make existing guards register into the new service model while leaving processing as a no-op stub

What changed:
- created the new `world/simulation` package and added the Phase 2 shell files
- implemented `SimulationKernel`, `ZoneSimulationService`, `TickBudget`, stub metrics, and a minimal `GuardZoneService`
- added registry helpers to create zone services and register active guards by zone
- added `GlobalSimulationKernelScript` to tick the kernel through one persistent global script
- registered newly created guards into the DireSim registry from `GuardNPC.at_object_creation()`
- added startup bootstrap code to ensure the global simulation script exists and register existing guards on server start
- set `ENABLE_PER_GUARD_GUARD_BEHAVIOR = False` and `ENABLE_DIRESIM_KERNEL = True` in settings so the old per-guard owner stays gated off while the new shell is present

Recreation snippet:
```text
Create these files under world/simulation/:
- kernel.py
- service.py
- budgets.py
- registry.py
- metrics.py
- zones/guard_zone_service.py

Implement the shell objects:
- SimulationKernel with register/unregister/tick_fast/tick_normal/tick_slow
- TickBudget with start/exceeded/increment
- ZoneSimulationService with npc_ids, event_queue, and queues for fast/normal/slow/deep
- GuardZoneService with add_guard(), rebuild_queues_if_needed(), process_cycle(), process_guard_stub(), get_guard()

Wire runtime integration:
- add GlobalSimulationKernelScript in typeclasses/scripts.py
- register guards in GuardNPC.at_object_creation()
- add startup helper in server/conf/at_server_startstop.py that ensures the global simulation script and calls register_existing_guards()
- set ENABLE_PER_GUARD_GUARD_BEHAVIOR = False and ENABLE_DIRESIM_KERNEL = True in server/conf/settings.py
```

Validation:
- no static errors in the new simulation files or touched integration files
- Django import check succeeded for `world.simulation.kernel` and `world.simulation.registry`
- `register_existing_guards()` returned `registered=24` and `service_count=1`
- no guard behavior logic was added; `process_guard_stub()` remains a no-op

---

### 2026-04-15 06:19:53
Summary: replaced the guard stub with a controlled read/decide/commit pipeline and added a pure decision contract plus legacy adapter seam

Files touched:
- world/simulation/resolvers/__init__.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/resolvers/legacy_guard_adapter.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- prevent old guard behavior from being reintroduced as an unbounded blob inside the new kernel shell
- enforce a NOOP-first decision model under zone-service control
- create a safe seam for later legacy reuse without directly calling the old guard tick path

What changed:
- added `GuardDecision` and `GuardContext` dataclasses for the new resolver contract
- added `resolve_guard_decision()` with pure `NOOP`, `OBSERVE`, `WARN`, and `MOVE` placeholder branches only
- added `legacy_guard_adapter()` that currently returns `NOOP` and does not invoke old guard behavior
- refactored `GuardZoneService` into explicit `read_guard_context()`, `decide_guard_action()`, and `commit_guard_decision()` methods
- kept READ phase side-effect free and limited it to current-room local counts plus a minimal incident flag
- kept DECIDE phase pure and unsupported-case safe by logging and returning `NOOP`
- kept COMMIT phase bounded to one action at most, with current placeholder behavior limited to transient metrics and no player-facing messaging
- added transient per-cycle metrics on the service for chosen action, decision reason, and whether a direct room scan was used

Recreation snippet:
```text
Create resolver files under world/simulation/resolvers/:
- guard_decision.py
- guard_resolver.py
- legacy_guard_adapter.py

Define:
- GuardDecision dataclass with action_type, target_id, destination_id, message_key, state_updates, events_to_emit
- GuardContext dataclass with minimal room/zone observation fields plus temporary awareness/movement and direct-scan flags

Refactor GuardZoneService:
- replace process_guard_stub() usage with read_guard_context() -> decide_guard_action() -> commit_guard_decision()
- default every unsupported branch to GuardDecision(action_type="NOOP")
- keep READ pure, DECIDE pure, and COMMIT bounded to one action
- do not call process_guard_behavior_tick() or any old guard scheduling path
```

Validation:
- no static errors in the resolver files or updated `guard_zone_service.py`
- Django pipeline check succeeded with `services=1` and `registered=24`
- sampled guard location stayed unchanged across `tick_fast()`, `tick_normal()`, and `tick_slow()` during this placeholder phase
- sample decision output remained `NOOP`, confirming controlled reintroduction without behavior inflation

---

### 2026-04-15 06:32:00
Summary: sealed legacy guard scheduler surfaces behind DireSim runtime blocks, startup cleanup, and an explicit test-only legacy adapter

Files touched:
- world/systems/guards.py
- typeclasses/scripts.py
- server/conf/settings.py
- server/conf/at_server_startstop.py
- diresimAsbuilt.md

Why:
- move from legacy guard execution being merely disabled by flags to being structurally unreachable in production while DireSim owns scheduling
- eliminate hidden reentry through per-guard scripts, global guard scripts, and startup fallback/ticker/reactor paths
- preserve one explicit migration/test-only adapter without allowing it onto a production scheduler path

What changed:
- added `is_diresim_enabled()` and shared `LEGACY_GUARD_RUNTIME_BLOCK_MSG` in `world/systems/guards.py`
- marked `process_guard_behavior_tick()` as legacy-only with an explicit header comment
- hard-blocked `process_guard_tick()` under DireSim and moved the old loop behind `_run_legacy_guard_tick_loop()` plus `run_legacy_guard_tick_for_test()`
- added `ENABLE_LEGACY_GUARD_TEST_ADAPTER = False` and `STRICT_DIRESIM_LEGACY_GUARD_SEAL = False`
- made `GuardBehaviorScript.at_repeat()` and `GlobalGuardPatrolScript.at_repeat()` return early under DireSim with the shared block message
- blocked new per-guard script attachment and added cleanup of existing `GuardBehaviorScript` instances via `cleanup_legacy_guard_behavior_scripts()`
- changed startup and reload wiring to skip legacy sync/registration when DireSim is enabled, clean up legacy scripts, and validate the seal
- added `get_diresim_guard_lock_report()` as a fast runtime report of DireSim state, legacy script/fallback presence, and registered guard-zone counts

Formal seal-off checklist:
- `process_guard_behavior_tick()` callers before seal-off:
	- `typeclasses/scripts.py` via `GuardBehaviorScript.at_repeat()`
	- `world/systems/guards.py` via `process_guard_tick()`
- `process_guard_tick()` production callers before seal-off:
	- `typeclasses/scripts.py` via `GlobalGuardPatrolScript.at_repeat()`
	- `server/conf/at_server_startstop.py` via `status_fallback`
	- `server/conf/at_server_startstop.py` via `_run_guard_ticker_tick()`
	- `server/conf/at_server_startstop.py` via `_schedule_guard_reactor_tick()` / `reactor_fallback`
- legacy script surfaces:
	- `typeclasses/scripts.GuardBehaviorScript`
	- `typeclasses/scripts.GlobalGuardPatrolScript`

Recreation snippet:
```text
In world/systems/guards.py:
- add is_diresim_enabled() and LEGACY_GUARD_RUNTIME_BLOCK_MSG
- block ensure/sync of GuardBehaviorScript when DireSim is on
- add cleanup_legacy_guard_behavior_scripts()
- move old process_guard_tick() loop into _run_legacy_guard_tick_loop()
- make process_guard_tick() return immediately under DireSim
- add run_legacy_guard_tick_for_test() behind ENABLE_LEGACY_GUARD_TEST_ADAPTER

In typeclasses/scripts.py:
- GuardBehaviorScript.at_repeat() returns before process_guard_behavior_tick() when DireSim is enabled
- GlobalGuardPatrolScript.at_repeat() returns before process_guard_tick() when DireSim is enabled

In server/conf/at_server_startstop.py:
- skip legacy guard script creation/sync when DireSim is enabled
- run per-guard cleanup after DireSim bootstrap
- block ticker/reactor/status-fallback legacy guard execution paths
- add get_diresim_guard_lock_report() and startup validation
```

Validation:
- legacy per-guard and global scheduler paths are blocked in production when `ENABLE_DIRESIM_KERNEL = True`
- only `run_legacy_guard_tick_for_test()` can reach the legacy bulk loop, and only when `ENABLE_LEGACY_GUARD_TEST_ADAPTER = True`
- startup validation now reports whether legacy per-guard scripts, global legacy scripts, or fallback registration remain present

---

### 2026-04-15 09:24:00
Summary: implemented Phase 12 arrest resolution with player-owned custody, owner-only escort, static jail transfer, and jailed-state suppression in guard logic

Files touched:
- world/simulation/custody.py
- world/simulation/handlers/guard_state.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- world/systems/justice.py
- typeclasses/characters.py
- diresimAsbuilt.md

Why:
- turn arrest from a warning-only branch into a bounded persistent world-state consequence
- keep arrest resolution deterministic and single-target with no combat, no pathfinding, and no unbounded jail subsystem
- prevent jailed or custody-bound players from re-entering normal guard suspicion and movement loops

What changed:
- added player-side custody and jail helpers with `JAIL_ROOM_ID = 9999`, custody entry/clear helpers, jail entry, and a release stub
- extended `GuardStateHandler` and `GuardContext` so guards can preserve custody-owned targets and project custody/jail state into the pure resolver
- updated the pure resolver to block repeat arrests, noop for non-owner guards, return `ESCORT` for the custody owner, and suppress further action for jailed targets
- finished COMMIT-side arrest resolution so successful `ARREST` enters custody, applies the arrest cooldown, clears confrontation/pursuit, and emits `PLAYER_ARRESTED`
- finished COMMIT-side escort resolution so only the custody owner can escort, the guard performs one bounded move toward the static jail room, the target is transported with `allow_custody_transport=True`, jail entry emits `PLAYER_JAILED`, and custody is cleared on arrival
- connected the existing jail release path to the new jailed-state stub so release clears DireSim jail state and enqueues `PLAYER_RELEASED`
- added custody/jail metrics (`arrests_successful`, `escorts_started`, `escorts_completed`, `jail_entries`) to service metrics and per-cycle guard metrics
- blocked manual movement and legacy `call_guards(...)` reentry while a player is in custody or jailed
- excluded custody and jailed players from active room player counts so jailed targets stop driving guard relevance after arrival

Recreation snippet:
```text
Create world/simulation/custody.py with:
- JAIL_ROOM_ID = 9999
- enter_custody(player, guard_id, room_id, now)
- clear_custody(player)
- enter_jail(player, now)
- release_player(player)

Extend the guard contract:
- add target_in_custody, custody_guard_id, target_is_jailed, escort_due to GuardContext
- add can_arrest_target(ctx) and should_escort(ctx)
- return ESCORT only for the custody-owning guard

In GuardZoneService.commit_guard_decision():
- resolve ARREST by entering custody, setting arrest_until = now + 10, clearing confrontation/pursuit, and enqueueing PLAYER_ARRESTED
- resolve ESCORT by moving the guard toward JAIL_ROOM_ID, transporting the target with allow_custody_transport=True, entering jail on arrival, clearing custody, and enqueueing PLAYER_JAILED

In Character movement hooks:
- block manual movement while jailed/in custody unless allow_custody_transport=True
- suppress legacy guard summon logic while jailed/in custody
```

Validation:
- no static errors in `world/simulation/custody.py`, `world/simulation/handlers/guard_state.py`, `world/simulation/resolvers/guard_decision.py`, `world/simulation/resolvers/guard_resolver.py`, `world/simulation/zones/guard_zone_service.py`, or `typeclasses/characters.py`
- focused Django runtime validation confirmed the full bounded loop:
	- `ARREST` resolved with decision reason `arrest_threshold`
	- target entered custody under the arresting guard
	- next decision became `ESCORT`
	- escort moved guard and target to room `9999`
	- custody cleared and jailed state became stable after arrival
	- jailed target no longer counted as an active room player for guard logic

---

### 2026-04-15 10:05:00
Summary: added phased guard reactivation controls with legacy tripwires, dry-run and partial-commit modes, and runtime caps for safe stepwise re-enable

Files touched:
- world/systems/guards.py
- typeclasses/scripts.py
- world/simulation/zones/guard_zone_service.py
- server/conf/settings.py
- diresimAsbuilt.md

Why:
- make guard reactivation testable one layer at a time instead of requiring code edits between every checkpoint
- ensure any accidental fallthrough into sealed legacy scheduling surfaces is immediately visible in logs
- allow controlled rollout from registration only, to read/decide only, to state-only commit, to limited movement, to full-scale activation

What changed:
- added an explicit legacy tripwire message `🚨 LEGACY GUARD PATH EXECUTED 🚨` and emitted it from `process_guard_behavior_tick()`, `process_guard_tick()`, `GlobalGuardPatrolScript.at_repeat()`, and `GuardBehaviorScript.at_repeat()` when those sealed paths fire under DireSim
- added `ENABLE_LEGACY_GUARD_TRIPWIRE` to keep the tripwire reversible while leaving the default enabled
- turned `ENABLE_GUARD_SYSTEM = True` while keeping `ENABLE_PER_GUARD_GUARD_BEHAVIOR = False` and `GUARD_PER_GUARD_ROLLOUT_COUNT = 0` so reactivation starts from zone-service ownership only
- added `DIRESIM_COMMIT_MODE` with modes:
	- `none`: read/decide only, no commit mutation
	- `state_only`: allow non-movement state transitions while blocking `MOVE`, `PURSUE`, and `ESCORT`
	- `full`: allow full bounded DireSim commit behavior
- added `ENABLE_DIRESIM_DECISION_LOGGING` so `[DECISION] guard=... action=...` logs can be enabled for read/decide verification without code edits
- added `MAX_ACTIVE_GUARDS` and settings-backed `MAX_EVENT_WAKE_NPCS` support in `GuardZoneService` so limited-scale movement tests can be done by configuration instead of patching constants
- set safe defaults for reactivation:
	- `DIRESIM_COMMIT_MODE = "none"`
	- `ENABLE_DIRESIM_DECISION_LOGGING = False`
	- `MAX_ACTIVE_GUARDS = 0`
	- `MAX_EVENT_WAKE_NPCS = 10`

Recreation snippet:
```text
In world/systems/guards.py:
- add LEGACY_GUARD_TRIPWIRE_MSG = "🚨 LEGACY GUARD PATH EXECUTED 🚨"
- add emit_legacy_guard_tripwire(surface)
- call it from process_guard_behavior_tick() and process_guard_tick() when DireSim blocks legacy execution

In typeclasses/scripts.py:
- call emit_legacy_guard_tripwire(...) from GlobalGuardPatrolScript.at_repeat() and GuardBehaviorScript.at_repeat() when DireSim blocks them

In world/simulation/zones/guard_zone_service.py:
- add settings-backed helpers for decision logging, commit mode, active-guard cap, and event-wake cap
- log decisions when ENABLE_DIRESIM_DECISION_LOGGING is on
- return immediately for DIRESIM_COMMIT_MODE = "none"
- block MOVE/PURSUE/ESCORT and keep ARREST state-only for DIRESIM_COMMIT_MODE = "state_only"

In server/conf/settings.py:
- ENABLE_GUARD_SYSTEM = True
- ENABLE_PER_GUARD_GUARD_BEHAVIOR = False
- GUARD_PER_GUARD_ROLLOUT_COUNT = 0
- ENABLE_LEGACY_GUARD_TRIPWIRE = True
- ENABLE_DIRESIM_DECISION_LOGGING = False
- DIRESIM_COMMIT_MODE = "none"
- MAX_ACTIVE_GUARDS = 0
- MAX_EVENT_WAKE_NPCS = 10
```

Validation:
- no static errors in `world/systems/guards.py`, `typeclasses/scripts.py`, `world/simulation/zones/guard_zone_service.py`, or `server/conf/settings.py`
- Django runtime import check confirmed `GuardZoneService` reads `DIRESIM_COMMIT_MODE = none` and returns the expected active guard and event wake defaults
- server restart and idle/walk pass-fail verification could not be executed here because `evennia stop` and `evennia reboot` are currently failing in this environment

---

### 2026-04-15 07:07:41
Summary: hardened the DireSim lock report lookup path and verified startup cleanup leaves no legacy guard scheduler surfaces active

Files touched:
- server/conf/at_server_startstop.py
- diresimAsbuilt.md

Why:
- make the new guard lock report work in both full Evennia runtime and bare Django validation contexts
- verify the actual startup/bootstrap path clears any pre-existing attached legacy guard scripts instead of only blocking future execution

What changed:
- added `_find_scripts_by_key()` with a fallback from `search_script(...)` to `ScriptDB.objects.filter(...)`
- switched global guard script and simulation kernel lookup sites used by the seal report/startup helpers to the new lookup helper
- reran the same DireSim bootstrap and validation path used at startup to confirm cleanup and registration outcomes

Recreation snippet:
```text
In server/conf/at_server_startstop.py:
- add _find_scripts_by_key(script_key)
- use it in global_guard_patrol/global_simulation_kernel lookup helpers and the DireSim seal report

Validation command:
- call _bootstrap_diresim_kernel('validation')
- call _validate_diresim_guard_lock('validation')
- inspect get_diresim_guard_lock_report()
```

Validation:
- static errors remained clear after the lookup helper change
- `process_guard_tick(source='validation')` returned `skipped='blocked_by_diresim'`
- `run_legacy_guard_tick_for_test(source='validation_adapter')` returned `skipped='legacy_test_adapter_disabled'` with default settings
- after `_bootstrap_diresim_kernel('validation')`, the lock report showed `legacy_per_guard_scripts_found=0`, `legacy_global_guard_script_active=False`, `legacy_fallback_registered=False`, `guard_zone_service_count=1`, and `guard_zone_registered_count=24`

---

### 2026-04-15 07:09:10
Summary: blocked direct public access to legacy guard behavior under DireSim so only the explicit opt-in test adapter can reach the old logic

Files touched:
- world/systems/guards.py
- diresimAsbuilt.md

Why:
- close the last remaining gap where an accidental direct call to `process_guard_behavior_tick()` could still execute legacy logic under DireSim
- align the code with the stricter seal requirement that only the explicit test/migration adapter may touch legacy behavior

What changed:
- moved the old `process_guard_behavior_tick()` body into `_process_guard_behavior_tick_legacy()`
- made public `process_guard_behavior_tick()` return `blocked_by_diresim` unless the call arrives through a `legacy_test_adapter:*` source and `ENABLE_LEGACY_GUARD_TEST_ADAPTER = True`
- updated `run_legacy_guard_tick_for_test()` to stamp the required `legacy_test_adapter:` source prefix before entering the old loop

Recreation snippet:
```text
In world/systems/guards.py:
- move the old process_guard_behavior_tick implementation into _process_guard_behavior_tick_legacy()
- gate public process_guard_behavior_tick() with is_diresim_enabled(), ENABLE_LEGACY_GUARD_TEST_ADAPTER, and a legacy_test_adapter-prefixed source
- have run_legacy_guard_tick_for_test() call the loop with source=f"legacy_test_adapter:{source}"
```

Validation:
- static errors remained clear after the final guard gate change
- direct `process_guard_behavior_tick(first_guard, source='validation_direct')` returned `blocked_by_diresim`
- `process_guard_tick(source='validation')` returned `skipped='blocked_by_diresim'`
- `run_legacy_guard_tick_for_test(source='validation_adapter')` still returned `skipped='legacy_test_adapter_disabled'` with default settings
- post-bootstrap seal report remained clean with `legacy_per_guard_scripts_found=0`, `legacy_global_guard_script_active=False`, `legacy_fallback_registered=False`, `guard_zone_service_count=1`, and `guard_zone_registered_count=24`

---

### 2026-04-15 07:18:00
Summary: added RoomFacts cache, movement/crime event emission, and cache-preferred local READ phase for guard zone services

Files touched:
- world/simulation/cache/__init__.py
- world/simulation/cache/room_facts.py
- world/simulation/events.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/registry.py
- world/simulation/zones/guard_zone_service.py
- typeclasses/characters.py
- world/systems/justice.py
- diresimAsbuilt.md

Why:
- replace repeated `room.contents` counting in the guard READ phase with a local cache that can be updated on room changes
- introduce queued movement/crime events that wake only relevant guards instead of making guards discover every change by scanning
- keep the migration safe by preserving a fallback room scan path until cache population is proven reliable

What changed:
- created `RoomFacts` with counts, crime flag, timestamps, versioning, clamp-safe increment/decrement helpers, invalidate/touch helpers, and debug summaries
- added `ROOM_FACTS`, `get_room_facts()`, and `get_or_create_room_facts()`
- created `SimEvent` and reused the existing zone-service event queue rather than executing work immediately in emitters
- updated `Character.at_after_move()` to maintain RoomFacts for players, guards, and generic NPCs and enqueue enter events into the owning guard zone service
- updated justice crime flagging to mark the current room’s RoomFacts as criminal and enqueue a queued crime event
- changed `GuardZoneService.read_guard_context()` to prefer RoomFacts, fall back to one direct local room scan only when cache is cold, and record `used_cache` / `used_direct_room_scan`
- added bounded event wake processing in `GuardZoneService` with `MAX_EVENT_WAKE_NPCS = 10`, same-room wake targeting, and normal-queue prioritization

Recreation snippet:
```text
Create:
- world/simulation/cache/room_facts.py
- world/simulation/events.py

Wire movement hooks:
- in Character.at_after_move(), update source/destination RoomFacts counts and enqueue SimEvent("*_ENTER", room.id)

Wire crime hooks:
- when actor.db.crime_flag becomes True, mark RoomFacts.crime_flag and enqueue SimEvent("CRIME_OCCURRED", room.id)

Update GuardZoneService:
- process queued events at the start of each cycle
- wake same-room guards up to MAX_EVENT_WAKE_NPCS
- use RoomFacts in read_guard_context()
- fall back to one direct local room scan only when RoomFacts is cold
```

Validation:
- static errors were clear in RoomFacts, event, registry, guard-zone, character, justice, and as-built files
- forced cold-cache first read returned `used_cache=False` and `used_direct_room_scan=True`
- second read of the same guard context returned `used_cache=True` and `used_direct_room_scan=False`
- a queued movement event remained deferred until `process_pending_events()` and then woke same-room guards without immediate execution
- RoomFacts counts remained non-negative during the hook validation path

---

### 2026-04-15 07:43:01
Summary: added transient significance tiers and tier-aware queue shaping so guards are processed by relevance instead of flat peer scheduling

Files touched:
- world/simulation/significance.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- make HOT guards preempt COLD guards under fixed budgets without widening behavior scope
- separate awareness responsiveness from movement cadence so frequent wake-ups do not become frequent room churn
- allow lower-relevance guards to wait gracefully instead of forcing fairness-at-all-costs scheduling

What changed:
- created `world/simulation/significance.py` with `HOT`, `WARM`, `COLD`, `DORMANT`, and `normalize_tier()`
- added transient service-owned tier state in `GuardZoneService`: `guard_significance`, `awareness_due_guard_ids`, `movement_due_guard_ids`, `recent_wake_timestamps`, and `recent_relevance_timestamps`
- defaulted newly seen guards to `COLD` without persisting tier to `.db`
- implemented significance evaluation rules: `HOT` for players/incident/awareness due, `WARM` for recent wake window, `COLD` as steady state, and `DORMANT` after longer inactivity with no due flags or incidents
- replaced flat ring queues with tier-aware queues and ring eligibility mapping:
	- fast -> HOT
	- normal -> HOT/WARM
	- slow -> WARM/COLD
	- deep -> COLD/DORMANT
- made `process_cycle()` iterate `HOT`, `WARM`, `COLD`, `DORMANT` in priority order and stop immediately when budget is exceeded
- added per-ring processed counts by tier in transient metrics and a queue debug snapshot helper
- reinforced cadence split so movement is only eligible in `normal`/`slow`, while `fast` remains awareness-only and `DORMANT` defaults to `NOOP`
- updated event wake handling so queued room events mark awareness due, stamp recent wake timestamps, and promote guards before queue rebuild

Recreation snippet:
```text
Create world/simulation/significance.py:
- HOT = "hot"
- WARM = "warm"
- COLD = "cold"
- DORMANT = "dormant"
- normalize_tier(value)

In GuardZoneService:
- add transient significance maps and recent wake/relevance timestamps
- replace flat queues with nested ring->tier queues
- rebuild queues from current tier with HOT/WARM/COLD/DORMANT eligibility per ring
- evaluate/update significance after read and before resolver
- process tiers in HOT->WARM->COLD->DORMANT order
- keep movement due independent from awareness due and only allow movement from normal/slow
```

Validation:
- static errors were clear in `significance.py` and the updated `guard_zone_service.py`
- queue rebuild honored transient wake state: `fast_hot=1`, `fast_cold=0`, `normal_hot=1`, `slow_cold=23`
- budgeted `fast` processing recorded `processed_hot=1` and `processed_cold=0`, confirming HOT-before-COLD degradation
- ring shaping kept movement disabled in `fast` and allowed it only in `normal` when `movement_due_guard_ids` was set
- queued event stimulus produced tier transitions `HOT -> WARM -> COLD` without requiring movement, and `event_woken=1`

---

### 2026-04-15 07:52:00
Summary: added ZoneFacts, adjacent-room wake fan-out, and zone-aware significance inputs without widening scans beyond one hop

Files touched:
- world/simulation/cache/zone_facts.py
- world/simulation/cache/__init__.py
- world/simulation/registry.py
- typeclasses/characters.py
- world/systems/justice.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- broaden guard awareness from room-local to immediate-neighborhood relevance without returning to NPC-led searching or polling
- let the simulation care about nearby active player rooms and incident heat through cached zone state instead of repeated world scans
- keep wake expansion bounded and ordered so same-room urgency stays higher than adjacent-room relevance

What changed:
- created `ZoneFacts` with hot-room, incident-room, and active-player-room sets plus timestamp/version helpers and debug summaries
- exported RoomFacts and ZoneFacts helpers through `world.simulation.cache`
- added `get_zone_facts_for_room()` to the registry layer so zone ownership comes from existing service wiring rather than fresh scans
- updated the existing movement hook to mark/clear active player rooms and hot rooms in ZoneFacts on player movement
- updated the existing crime hook to mark hot and incident rooms in ZoneFacts and count transient feed metrics on the owning service
- added bounded adjacent-room discovery in `GuardZoneService` using only direct exits from the current room
- expanded event wake handling so same-room guards are promoted HOT and adjacent-room guards are promoted WARM, still capped by `MAX_EVENT_WAKE_NPCS`
- added transient wake source recording and zone debug snapshots including queue state, zone hot/player/incident counts, and wake-source counts
- updated significance evaluation to use ZoneFacts as pure inputs for WARM transitions without any writes or event emission during evaluation

Recreation snippet:
```text
Create world/simulation/cache/zone_facts.py with:
- ZoneFacts
- ZONE_FACTS
- get_zone_facts()
- get_or_create_zone_facts()

Wire existing emitters:
- player movement marks/clears active player rooms and marks destination room hot
- crime events mark room hot and incident-active

Update GuardZoneService:
- add get_adjacent_room_ids(room) using direct exits only
- wake same-room guards as HOT and adjacent-room guards as WARM
- keep fan-out ordered and capped by MAX_EVENT_WAKE_NPCS
- use ZoneFacts in evaluate_guard_significance() as pure read-only inputs
```

Validation:
- static errors were clear in ZoneFacts, cache exports, registry, character hook, justice hook, guard-zone service, and as-built files
- player movement feed updated ZoneFacts with `zone_active_player_rooms=1` and `zone_hot_rooms=1` without introducing new world scans
- direct one-hop adjacency discovery returned bounded results (`adjacent_room_count=7`) from room-local exits only
- live queued same-room event wake preserved deferred execution and recorded `same_room_source=same_room_event` with bounded wake count
- synthetic bounded wake check confirmed ordering and promotion semantics:
	- same-room guard -> `same_room_event` / `hot`
	- adjacent-room guards -> `adjacent_room_event` / `warm`
- isolated ZoneFacts-only evaluation with cleared wake state returned `zonefacts_adjacent_eval=warm`, confirming adjacent hot-room awareness without same-room stimulus
- zone debug snapshot returned the expected keys for queue state, zone counts, and wake-source counts

---

### 2026-04-15 08:27:28
Summary: added GuardStateHandler ownership for persistent guard memory and confined migrated state mutation to the DireSim commit boundary

Files touched:
- world/simulation/handlers/__init__.py
- world/simulation/handlers/guard_state.py
- typeclasses/npcs/guard.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- move persistent guard memory out of scattered `guard.db.*` fields and into one handler-owned storage surface
- separate persistent guard state from transient service/runtime state without widening guard behavior scope
- enforce the Phase 7 rule that handlers own memory, services own time, and commit is the only persistent mutation surface in active DireSim code

What changed:
- created `GuardStateHandler` under `world/simulation/handlers/guard_state.py` with one storage key/category pair: `diresim_guard_state` / `simulation`
- implemented `_load()`, `_save()`, `to_dict()`, `_dirty`, `mark_dirty()`, and `save_if_needed()` so all persistent state is loaded/saved as one dict
- defined persistent handler fields for patrol state, warning count, suspicion map, current target, cooldowns, home room, and `last_significant_event_at`
- added transient-only handler fields plus `reset_transient()` and `validate()` so transient metrics/caches never serialize
- added suspicion helpers (`get_suspicion`, `set_suspicion`, `add_suspicion`, `clear_suspicion`) and cooldown helpers (`get_cooldown`, `set_cooldown`, `clear_cooldown`, `is_cooldown_active`)
- attached the handler to `GuardNPC` as `@lazy_property def sim_state(self)`
- extended `GuardContext` with read-only handler-owned fields: `warning_count`, `current_target_id`, `patrol_index`, `home_room_id`, and `behavior_state`
- updated `GuardZoneService.read_guard_context()` to read handler state but not mutate it
- kept `resolve_guard_decision()` structural-only for this phase; it now receives handler state input through the existing call path but does not mutate it or widen behavior
- updated `GuardZoneService.commit_guard_decision()` so the migrated persistent fields are mutated and saved only at commit: `behavior_state`, `warning_count`, `current_target_id`, `patrol_index`, `home_room_id`, `cooldowns`, and `last_significant_event_at`

Recreation snippet:
```text
Create world/simulation/handlers/guard_state.py with:
- STORAGE_KEY = "diresim_guard_state"
- STORAGE_CATEGORY = "simulation"
- _load(), _save(), to_dict(), mark_dirty(), save_if_needed(), reset_transient(), validate()
- persistent fields: patrol_route_id, patrol_index, behavior_state, warning_count, suspicion_targets, current_target_id, cooldowns, last_significant_event_at, home_room_id
- transient-only fields: last_cycle_metrics, last_known_room_fact_version, last_decision_reason, cached_candidates

In typeclasses/npcs/guard.py:
- import lazy_property and GuardStateHandler
- add @lazy_property def sim_state(self): return GuardStateHandler(self)

In world/simulation/resolvers/guard_decision.py:
- extend GuardContext with warning_count, current_target_id, patrol_index, home_room_id, behavior_state

In world/simulation/zones/guard_zone_service.py:
- READ: pull migrated persistent fields from guard.sim_state only
- DECIDE: pass guard.sim_state into resolve_guard_decision()
- COMMIT: mutate/save handler-owned persistent state only here via save_if_needed()
```

Validation:
- static errors were clear in `guard_state.py`, `guard.py`, `guard_decision.py`, `guard_resolver.py`, `guard_zone_service.py`, and `diresimAsbuilt.md`
- focused handler round-trip validation succeeded with persisted values restored after reload:
	- `warning_count=3`
	- `current_target_id=777`
	- `patrol_index=4`
	- `behavior_state=warn`
	- `suspicion_999=6`
	- `cooldown_warn_until=123.5`
	- `last_significant_event_at=456.5`
- transient fields did not persist across reload (`transient_persisted=False`)
- READ remained pure: comparing the handler attribute payload before and after `read_guard_context()` returned `read_storage_unchanged=True`
- COMMIT was the only persistent mutation surface in the focused validation path; a synthetic `WARN` commit persisted:
	- `commit_behavior_state=warn`
	- `commit_warning_count=4`
	- `commit_current_target_id=321`
	- `commit_has_warn_cooldown=True`
	- `commit_last_significant_event_at_positive=True`
- the sampled guard’s original handler payload was restored after validation (`restored_original=True`)

---

### 2026-04-15 08:43:12
Summary: added static patrol routes and handler-owned movement intent so guards patrol one waypoint at a time from persisted route state

Files touched:
- world/simulation/patrol_routes.py
- world/simulation/handlers/guard_state.py
- world/simulation/registry.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- move guard patrol movement from per-cycle recomputation to persisted handler intent
- keep READ and DECIDE pure while making COMMIT the only place that performs movement or advances patrol state
- add a minimal patrol-route foundation without introducing pathfinding, rerouting, or neighbor-search movement logic

What changed:
- created `world/simulation/patrol_routes.py` with a simple static registry (`PATROL_ROUTES`), route lookup, route creation, and route-length helpers
- extended `GuardStateHandler` with persistent movement fields `movement_target_room_id` and `movement_progress_index`, plus helper methods for patrol lookup/progression and cooldown-based movement gating
- updated guard registration to ensure each registered guard has a default one-room loop patrol route anchored to its home room and to reconstruct that simple route if only the route id persists across reload
- extended `GuardContext` with `significance_tier` and updated the pure resolver so patrol movement is suppressed when `HOT`, allowed for empty-room `WARM`/`COLD` guards when movement is due, and short-circuits to `NOOP` when the handler has no valid patrol route
- changed `GuardZoneService.read_guard_context()` to derive `movement_due` from the handler cooldown instead of transient queue state, and changed ring shaping to carry the current significance tier into DECIDE
- refactored `GuardZoneService.commit_guard_decision()` so `MOVE` resolves the next room only from handler-owned route state, moves at most one step, advances the patrol index only on success, updates the persisted next target, sets a move cooldown, and records move metrics (`move_attempted`, `move_success`, `move_failed`, `route_progress`)

Recreation snippet:
```text
Create world/simulation/patrol_routes.py with:
- PATROL_ROUTES = {}
- get_patrol_route(route_id)
- ensure_patrol_route(route_id, room_ids, loop=True)
- get_route_length(route)

In GuardStateHandler:
- add movement_target_room_id and movement_progress_index to persistent state
- add get_next_patrol_room(), advance_patrol_index(), and is_movement_due(now)

In registry.register_guard():
- ensure a simple default one-room loop route for each guard home room
- persist patrol_route_id and initial movement target through the handler

In GuardZoneService:
- READ movement_due from sim_state.is_movement_due(now)
- keep resolver route-agnostic except for checking whether a handler-owned next patrol room exists
- perform MOVE only in COMMIT, one route waypoint at a time, and advance route state only after successful movement
```

Validation:
- static errors were clear in `patrol_routes.py`, `guard_state.py`, `registry.py`, `guard_decision.py`, `guard_resolver.py`, `guard_zone_service.py`, and `diresimAsbuilt.md`
- focused synthetic patrol validation confirmed loop progression and persisted target advancement:
	- `loop_move_history=[102, 103]`
	- `loop_progress=[1, 2, 0]`
	- `next_target_after_loop=101`
- movement cooldown pacing held after a successful move (`cooldown_due_after_move=False` immediately after commit)
- tier interaction matched Phase 8 rules in the focused validation path:
	- `hot_action=NOOP`
	- `warm_action=MOVE`
	- `dormant_action=NOOP`
- missing patrol routes now fail safely in DECIDE without entering COMMIT movement:
	- `missing_route_action=NOOP`
	- `missing_route_reason=missing_patrol_route`

---

### 2026-04-15 09:06:31
Summary: added event-driven suspicion memory, lazy decay, single-target tracking, and target-aware patrol suppression for guards

Files touched:
- world/simulation/handlers/guard_state.py
- typeclasses/characters.py
- world/systems/justice.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- make guards remember event-driven suspicion over time instead of reacting only to immediate room state
- keep suspicion accumulation bounded to event feeds and existing same-room/adjacent wake semantics without adding scan-driven target discovery
- preserve the DireSim ownership model by staging suspicion updates transiently during event processing and persisting them only at COMMIT

What changed:
- extended `GuardStateHandler` with a structured suspicion model `{value, last_seen_at}`, clamp helpers, threshold helpers, lazy decay, explicit cleanup, and single-target selection/update helpers
- added Phase 9 constants for decay and targeting: `SUSPICION_DECAY_PER_TICK`, `MIN_TARGET_THRESHOLD`, and hostility/suspicion thresholds
- updated movement and crime emitters so DireSim events carry `target_id` and standardized the crime event to `CRIME_COMMITTED`; player movement now also emits `PLAYER_LEAVE`
- extended `GuardContext` with `target_suspicion_level`
- updated the pure resolver to prioritize tracked targets over patrol: moderate suspicion returns `OBSERVE`, higher suspicion returns `WARN`, and patrol movement remains suppressed while a target is active
- changed guard-zone event processing so suspicion is not persisted immediately; instead, event processing records transient per-guard pending suspicion deltas for same-room and adjacent guards already selected by the bounded wake path
- changed `read_guard_context()` to project target state from handler memory plus pending event deltas without mutating persisted handler state
- changed `commit_guard_decision()` to apply pending suspicion deltas, update `current_target_id`, perform explicit cleanup/decay-driven target drop, and record suspicion metrics (`suspicion_added`, `suspicion_targets_count`, `suspicion_events_processed`)
- emitted `GUARD_WARNED` from the warning commit stub so suspicion escalation can continue through the standardized event feed

Recreation snippet:
```text
In GuardStateHandler:
- replace flat suspicion ints with {value, last_seen_at}
- add clamp_suspicion(), get_effective_suspicion(), touch_target(), add_suspicion_from_event(), cleanup_suspicion(), get_primary_target(), update_primary_target()

In the event emitters:
- include target_id in PLAYER_ENTER / PLAYER_LEAVE payloads
- rename the justice event to CRIME_COMMITTED and include target_id

In GuardZoneService:
- stage per-guard suspicion deltas during process_pending_events()
- project target state in READ from handler state plus pending deltas only
- persist staged suspicion deltas and current_target_id in COMMIT only
- return WARN / OBSERVE based on target_suspicion_level and suppress patrol while a target is active
```

Validation:
- static errors were clear in the updated handler, character, justice, resolver, guard-zone service, and as-built files
- focused handler validation confirmed lazy decay without mutation:
	- `stored_value_101=22`
	- `effective_101_later=7`
	- `raw_after_lazy_decay=22`
	- explicit cleanup later removed zeroed targets only when requested
- focused end-to-end event validation confirmed READ stayed pure and COMMIT owned persistence:
	- before commit: `stored_target_before_commit=None`
	- projected in READ: `projected_target_same=7001 22`
	- after commit: `stored_target_after_commit_same=7001`
- event-driven suspicion remained bounded to relevant guards only and used payload-supplied target ids:
	- same-room effective suspicion `22`
	- adjacent effective suspicion `11`
	- no target scan logic was introduced in the validation path
- patrol suppression and resolver targeting behaved as intended:
	- first decision after enter+crime: `OBSERVE target_tracked`
	- after `GUARD_WARNED`: projected suspicion `27` and decision `WARN target_high_suspicion`
- decay eventually cleared the target cleanly:
	- `final_target_after_decay=None`
	- `final_suspicion_after_decay=0`

---

### 2026-04-15 09:22:09
Summary: added staged pursuit state, target-driven PURSUE decisions, and bounded one-step interception movement under the existing DireSim movement limits

Files touched:
- world/simulation/handlers/guard_state.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- turn remembered suspicion into spatial pressure without reintroducing scans, pathfinding, or free-roaming chase logic
- keep pursuit target/location intent persistent and handler-owned while preserving READ purity and COMMIT-only world mutation
- reuse the existing bounded movement model so pursuit remains one-step, cooldown-gated, and budget-safe

What changed:
- extended `GuardStateHandler` with persistent pursuit fields: `pursuit_target_id`, `pursuit_last_known_room_id`, `pursuit_state`, `pursuit_started_at`, and `intercept_room_id`
- added pursuit helpers in the handler: `begin_pursuit()`, `update_last_known_room()`, `set_intercept_room()`, `clear_pursuit()`, `set_pursuit_state()`, `is_pursuit_due()`, and `has_valid_pursuit()`
- added `MIN_PURSUIT_THRESHOLD = 20` and kept pursuit state normalization limited to `none`, `tracking`, and `intercepting`
- extended `GuardContext` with pursuit projection fields: `pursuit_target_id`, `pursuit_last_known_room_id`, `pursuit_state`, `intercept_room_id`, and `pursuit_due`
- added transient staged pursuit deltas in `GuardZoneService` (`pending_pursuit_updates`) plus pursuit metrics (`pursuit_events_processed`, `pursuit_started`, `pursuit_refreshed`, `pursuit_cleared`)
- updated event processing so `CRIME_COMMITTED`, `PLAYER_LEAVE`, `PLAYER_ENTER`, `PLAYER_FLED`, and `GUARD_WARNED` can stage pursuit updates from payload-supplied `target_id` and room ids only
- kept same-room guards primary: same-room events can start pursuit at threshold, while adjacent guards only refresh existing pursuit on low suspicion and require a higher threshold for automatic pursuit start
- added READ-time pursuit projection with no handler mutation by overlaying staged pursuit data on top of persisted handler state and deriving a minimal intercept room heuristic from the last known room
- added pure resolver support for `PURSUE` and made patrol yield when pursuit intent is active above the pursuit threshold
- added COMMIT-only `PURSUE` execution that reuses the existing movement limits: one move max, no fast-ring movement, one cooldown key (`pursuit_until`), no recursion, and no pathfinding
- updated COMMIT to persist pursuit state only after staged updates are applied and to clear pursuit only when target decay has actually removed the projected target

Recreation snippet:
```text
In GuardStateHandler:
- add pursuit_target_id, pursuit_last_known_room_id, pursuit_state, pursuit_started_at, intercept_room_id
- add begin_pursuit(), clear_pursuit(), set_pursuit_state(), is_pursuit_due(), has_valid_pursuit()

In GuardZoneService:
- add pending_pursuit_updates and pursuit metrics
- stage pursuit deltas in process_pending_events() from event payloads only
- project pursuit state in READ without mutating the handler
- apply pending pursuit state in COMMIT and execute PURSUE as one bounded move

In the resolver:
- allow action_type="PURSUE"
- return PURSUE only when target, threshold, last-known room, and pursuit_due all line up and no current-room player handling is higher priority
```

Validation:
- static errors were clear in the updated handler, context, resolver, guard-zone service, and as-built files
- focused handler validation confirmed pursuit state normalization and cooldown gating:
	- `pursuit_fields 9001 123 tracking 10.0 124`
	- `has_valid_pursuit=True`
	- `is_pursuit_due_now=False`
	- `is_pursuit_due_later=True`
- focused end-to-end pursuit validation confirmed staged-only pursuit before commit:
	- before commit: `stored_pursuit_before_commit None None`
	- projected in READ for same-room guard: `8001 401 tracking 401 20 True`
	- adjacent low-suspicion guard did not auto-start pursuit: `phase1_projected_adj None None 10`
- resolver and commit followed the phase gate rules:
	- same-room guard: `PURSUE target_pursuit_due`
	- adjacent guard remained on non-pursuit handling: `OBSERVE`
	- immediate follow-up pursue was cooldown-blocked (`pursuit_due=False`)
- later `PLAYER_ENTER` refresh updated last-known room and produced one bounded pursuit move into the adjacent room:
	- projected refresh: `8001 402 402 True`
	- decision: `PURSUE 402 target_pursuit_due`
	- move history: `[402]`
- decay eventually cleared pursuit alongside the target:
	- `cleared_after_decay None none None`

---

### 2026-04-15 09:36:36
Summary: added same-room warning and arrest escalation with persistent confrontation state, cooldown-gated resolver priorities, and commit-only consequence events

Files touched:
- world/simulation/handlers/guard_state.py
- world/simulation/resolvers/guard_decision.py
- world/simulation/resolvers/guard_resolver.py
- world/simulation/zones/guard_zone_service.py
- diresimAsbuilt.md

Why:
- turn pursuit into an actual confrontation loop players can feel without reintroducing scans, spam, combat, or multi-target behavior
- keep same-room warning/arrest logic pure in DECIDE and push all confrontation mutation to COMMIT
- preserve the phase constraints that warning/arrest are consequence skeletons only, not full justice resolution

What changed:
- extended `GuardStateHandler` with persistent confrontation memory: `confrontation_target_id`, `confrontation_state`, `warning_stage`, `last_warning_at`, and `arrest_attempted_at`
- added handler helpers `begin_warning()`, `advance_warning_stage()`, `begin_arrest()`, `clear_confrontation()`, `is_warning_due()`, and `is_arrest_due()` while keeping them state-only and side-effect free
- added `MIN_WARN_THRESHOLD = 15` and `MIN_ARREST_THRESHOLD = 30`
- extended `GuardContext` with confrontation and same-room gating fields: `confrontation_target_id`, `confrontation_state`, `warning_stage`, `warning_due`, `arrest_due`, and `target_present_in_room`
- added pure resolver helpers `should_warn()` and `should_arrest()` and reordered priorities to `ARREST > WARN > PURSUE > MOVE > NOOP` while suppressing patrol and pursue when the target is present in the current room
- changed READ to compute `target_present_in_room` via direct target lookup by id rather than room search and to project pending confrontation clears without mutating handler state
- added staged confrontation updates in the zone service for `PLAYER_COMPLIED`, along with compliance-driven pressure reduction and confrontation/pursuit clearing at COMMIT
- updated commit handling so `WARN` begins or advances warning state, sets `warn_until`, increments warning count, and emits `GUARD_WARNED`; `ARREST` begins arrest state, sets `arrest_until`, and emits `GUARD_ARREST_ATTEMPT`
- added transient metrics for `warn_emitted`, `arrest_emitted`, and `warning_stage` to the per-cycle service output

Recreation snippet:
```text
In GuardStateHandler:
- add persistent confrontation fields and helper methods for warning/arrest lifecycle

In GuardContext and resolver:
- add target_present_in_room, warning_due, arrest_due, confrontation_target_id, confrontation_state, warning_stage
- implement should_warn() and should_arrest()
- order actions as ARREST > WARN > PURSUE > MOVE > NOOP

In GuardZoneService:
- project same-room target presence by direct target lookup
- add staged confrontation clears for PLAYER_COMPLIED
- mutate confrontation state only in COMMIT
- emit GUARD_WARNED / GUARD_ARREST_ATTEMPT events from COMMIT only
```

Validation:
- static errors were clear in the updated handler, context, resolver, guard-zone service, and as-built files
- focused confrontation validation confirmed same-room warning threshold behavior:
	- decision: `WARN warn_threshold`
	- commit metrics: `warn_emitted=True`, `warning_stage=1`
	- persisted state: `confrontation_state=warning`, `warning_stage=1`
- cooldown handling prevented repeated WARN spam and allowed escalation through the resolver priority order:
	- post-warning decision on the same target advanced to `ARREST arrest_threshold` instead of repeating WARN
- arrest commit remained skeleton-only and emitted consequences without combat/jail logic:
	- commit metrics: `arrest_emitted=True`
	- persisted state: `confrontation_state=arresting`
	- emitted event queue included `GUARD_ARREST_ATTEMPT`
- compliance handling now reduces pressure and clears confrontation through staged event data rather than direct mutation:
	- projected after `PLAYER_COMPLIED`: `current_target_id=None`, `confrontation_state=none`, `target_suspicion_level=0`
	- commit metrics reported `current_target_id=None`
	- final persisted state: `confrontation_target_id=None`, `confrontation_state=none`, effective suspicion `0`
- all focused validation paths remained bounded: no broad searches, no recursive decisions, and no direct room-message spam loops


