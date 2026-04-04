# Script Usage Audit

This document satisfies PH1-017 by classifying each live custom Script as `controller`, `poller`, or `mixed` based on current code behavior.

Classification rules used here:

- `controller`: the script primarily orchestrates persistent state, multi-step flow, or actor coordination
- `poller`: the script mainly repeats to discover elapsed timestamps or state that should ideally be handled by explicit expiry/callbacks
- `mixed`: the script currently combines orchestration/controller work with polling or expiry discovery

Phase 1 constraint reminder:

- this audit does not move authoritative ownership out of timestamps
- `mixed` is a diagnosis, not an automatic migration order
- `invalid` legacy script paths are still classified here by behavior so they can be retired deliberately

## Live Custom Script Classes

| Script | Behavior Class | Timing Primitive Class | Attachment Site | File | Reasoning |
| --- | --- | --- | --- | --- | --- |
| `typeclasses.scripts.BleedTicker` | `poller` | `INVALID` | legacy only; deleted during server start | `typeclasses/scripts.py` | Repeats every second only to call `process_bleed()` on its attached object. It is already invalidated via `is_valid() -> False` and exists only as legacy cleanup surface. |
| `typeclasses.scripts.CorpseDecayScript` | `mixed` | `CONTROLLER` | `typeclasses/characters.py` attaches it to new corpses | `typeclasses/scripts.py` | `at_start()` re-arms scheduler-backed corpse decay, which is controller/reload behavior, but `at_repeat()` still polls for condition decay, devotional protection, and memory-loss timing. |
| `typeclasses.scripts.GraveMaintenanceScript` | `mixed` | `CONTROLLER` | `typeclasses/corpse.py` attaches it to graves | `typeclasses/scripts.py` | The script still polls for warning and expiry boundaries on `grave.db.expiry_time`, but it also owns recurring grave wear progression and notification state such as `expiry_warned` and `last_grave_damage_tick`. |
| `typeclasses.onboarding_scripts.OnboardingRoleplayScript` | `mixed` | `CONTROLLER` | tutorial mentor/gremlin NPCs in `server/conf/at_server_startstop.py` | `typeclasses/onboarding_scripts.py` | It is attached to persistent onboarding actors and coordinates nudges and NPC lines, but it also polls prompt-spacing, idle-delay, and scene-trigger timing windows every 5 seconds. |
| `typeclasses.onboarding_scripts.OnboardingInvasionScript` | `controller` | `CONTROLLER` | tutorial Breach Corridor room in `server/conf/at_server_startstop.py` | `typeclasses/onboarding_scripts.py` | This is a stage-based scenario controller. The repeating loop drives a persistent invasion state machine, spawns enemies, tracks stabilization, and coordinates the onboarding flow rather than serving as simple expiry discovery. |

## Script Attachment Inventory

| Attachment Site | Script | Notes |
| --- | --- | --- |
| `typeclasses/characters.py` | `CorpseDecayScript` | Added when a corpse is created after death. |
| `typeclasses/corpse.py` | `GraveMaintenanceScript` | Added when a grave is created from corpse decay. |
| `server/conf/at_server_startstop.py` | `OnboardingRoleplayScript` | Attached to tutorial mentor and gremlin NPCs. |
| `server/conf/at_server_startstop.py` | `OnboardingInvasionScript` | Attached to the tutorial Breach Corridor room. |

## Classification Notes By Script

### `BleedTicker`

- behavior: `poller`
- current status: legacy invalid
- why: it repeats only to notice a recurring damage tick on the attached object
- Phase 1 implication: keep removed; do not reintroduce as a timing mechanism

### `CorpseDecayScript`

- behavior: `mixed`
- controller responsibilities:
  - reload/start re-arming of scheduler-backed corpse-to-grave decay
  - persistent corpse-state ownership over long-lived death/remains behavior
- polling responsibilities:
  - devotional protection checks
  - condition decay every interval
  - memory-loss discovery when `memory_time` elapses
- Phase 1 implication: keep as a controller, but the memory-loss and similar one-shot discovery paths are good PH1-018 split candidates

### `GraveMaintenanceScript`

- behavior: `mixed`
- controller responsibilities:
  - persistent grave maintenance state such as warning flags and wear progression
- polling responsibilities:
  - checks `expiry_time` and warning thresholds on every repeat
  - deletes the grave when the expiry timestamp has elapsed
- Phase 1 implication: likely keep a controller only if grave wear remains recurring; grave warning/deletion boundaries are the obvious split candidates

### `OnboardingRoleplayScript`

- behavior: `mixed`
- controller responsibilities:
  - persistent NPC onboarding presence and roleplay coordination
  - per-character prompt suppression cache via `last_prompt_by_character`
- polling responsibilities:
  - idle checks
  - prompt-spacing checks
  - room-delay scene triggers for gear/training nudges
- Phase 1 implication: onboarding orchestration should stay controller-driven, but isolated nudges/reminders could eventually move to explicit expiry scheduling

### `OnboardingInvasionScript`

- behavior: `controller`
- controller responsibilities:
  - invasion stage machine (`idle`, `warning`, `first_contact`, `breach`, `active`, `stabilization`)
  - breach goblin spawning and stabilization messaging
  - coordination across all onboarding characters in tutorial rooms
- why not `mixed`: even though it checks elapsed stage windows, those checks are part of a multi-step orchestrated scenario, not hidden one-shot cleanup living on an otherwise stateless loop
- Phase 1 implication: this is the reference example of a valid Script controller in the current codebase

## Phase 1 Outcome

PH1-017 conclusions:

- `controller`: `OnboardingInvasionScript`
- `mixed`: `CorpseDecayScript`, `GraveMaintenanceScript`, `OnboardingRoleplayScript`
- `poller`: `BleedTicker` (legacy invalid path)

The main PH1-018 split-rule pressure points are now explicit:

- corpse memory-loss discovery inside `CorpseDecayScript`
- grave warning/deletion boundaries inside `GraveMaintenanceScript`
- onboarding idle/prompt reminder deadlines inside `OnboardingRoleplayScript`