# MT-516-mixed validation

Status: SHIPPED

## Phase A — Audit

Migration roster:

| Command | Resolution before | Scope | Decision | Notes |
| --- | --- | --- | --- | --- |
| `cmd_attack.py` | `resolve_numbered_candidate(room.contents)` | characters + room | migrated | narrowed to character scope for combat targeting |
| `cmd_target.py` | `caller.search()` fallback | characters | migrated | body-part targeting preserved |
| `cmd_whisper.py` | `caller.search()` | characters | migrated | speech-specific filters unchanged |
| `cmd_ask.py` | `caller.search()` | characters/NPCs | migrated | `handle_inquiry()` gate preserved |
| `cmd_teach.py` | `caller.search()` | characters | migrated | teaching logic unchanged |
| `cmd_diagnose.py` | `caller.search()` | characters | migrated | empathy diagnosis unchanged |
| `cmd_circle.py` invite/accept | `caller.search(location=caller.location)` | characters | migrated | module helper now uses centralized resolver |
| `cmd_bind.py` | `caller.search(location=caller.location)` | corpse-only | migrated | room-object resolution, corpse gate preserved |
| `cmd_capture.py` | `caller.search(location=caller.location)` | characters | migrated | bounty and custody filters preserved |
| `cmd_commune.py` | `caller.search(location=caller.location)` | both | migrated | optional target now resolves across characters + room objects |
| `cmd_consent.py` | `caller.search(location=caller.location)` | characters | migrated | consent duration logic unchanged |
| `cmd_heal_scars.py` | `caller.search(location=caller.location)` | characters/self | migrated | explicit self handling preserved |
| `cmd_link.py` | `caller.search(location=caller.location)` | characters | migrated | persistent/focus flows unchanged |
| `cmd_manipulate.py` | `caller.search(location=caller.location)` | characters | migrated | profession gate unchanged |
| `cmd_mark.py` | `caller.search(location=caller.location)` | characters | migrated | thief/ranger mark logic unchanged |
| `cmd_observe.py` | `caller.search(location=room)` | characters | migrated | stealth/awareness logic unchanged |
| `cmd_perceive.py` | `caller.search(location=caller.location)` | characters + corpse objects | migrated | cleric corpse path and empath character path preserved |
| `cmd_prepare.py` corpse branch | `caller.search(location=caller.location)` | corpse-only | migrated | spell preparation fallback unchanged |
| `cmd_rejuvenate.py` | `caller.search(location=caller.location)` | corpse-only | migrated | rite behavior unchanged |
| `cmd_restore.py` | `caller.search(location=caller.location)` | corpse-only | migrated | corpse gate preserved |
| `cmd_stabilize.py` | `caller.search(location=caller.location)` | both | migrated | corpse and living-target branches preserved |
| `cmd_talk.py` | `open_interaction_with(target_name)` | NPCs | migrated | direct NPC resolution added; fallback kept |
| `cmd_touch.py` | `caller.search(location=caller.location)` | characters | migrated | chargen mirror special case preserved |
| `cmd_uncurse.py` | `caller.search(location=caller.location)` | characters | migrated | cleric rite unchanged |
| `cmd_study_anatomy.py` | `caller.search()` | both | migrated | now resolves across characters, room objects, and inventory |
| `cmd_steal.py` | `caller.search(location=room)` + custom container search | both | migrated | main target path migrated; container parsing preserved |
| `cmd_throw.py` | `caller.search(location=caller.location)` | characters | migrated | tomato/stocks logic unchanged |
| `cmd_thug.py` | `caller.search(location=caller.location)` | characters | migrated | rough/intimidation flows unchanged |
| `cmd_tend.py` target branch | `caller.search()` | characters/self | migrated | self-tending preserved |
| `cmd_take.py` shock branch | `caller.search(location=caller.location)` | characters | migrated | only the explicit shock-target branch widened |
| `cmd_assess.py` | `resolve_numbered_candidate(corpses)` | corpse-only | excluded | already on a narrower corpse-specific path |
| `cmd_resurrect.py` | `resolve_numbered_candidate(corpses)` | corpse-only | excluded | already on corpse-specific ordinal logic |
| `cmd_sensesoul.py` | `resolve_numbered_candidate(corpses)` | corpse-only | excluded | already on corpse-specific ordinal logic |
| global/admin flows (`race`, `setrace`, `setcircle`, `deathinspect`, `decaycorpse`, `res`, etc.) | `caller.search(global_search=True)` | global/admin | excluded | out of scope for nearby mixed-target migration |

Audit result: mixed command patterns were not wildly inconsistent. Most local verbs still used a plain nearby `caller.search(...)`, which made resolver migration surgical rather than staged.

## Phase B — Resolver extension

Updated `world/helpers/target_resolver.py` to support:

- `characters` scope for visible nearby characters/NPCs excluding the caller
- `npcs` scope for visible nearby NPCs only
- combined scope resolution through `resolve_target(...)`
- recency sorting that handles both numeric and `datetime` `db_date_created` values

Updated `commands/command.py` with base-command wrappers:

- `resolve_target(...)`
- `msg_target_matches(...)`

## Phase C — Command migration

Migrated command logic is resolution-only. No combat, social, rite, or theft
outcome logic was changed beyond how the initial target is selected.

Representative scope choices:

- combat/social character verbs: `("characters",)`
- mixed character/object verbs: `("characters", "room")`
- corpse/object ritual verbs: `("room",)`
- NPC interaction verbs: `("npcs",)`
- study-style mixed verbs: `("characters", "room", "inventory")`

## Phase D — NPC aggregation decision

Chosen option: defer NPC aggregation.

Rationale from audit and runtime verification:

- room code already separates `get_display_characters()` from `get_display_things()`
- runtime output still lists nearby NPCs individually: `Characters: goblin, goblin`
- NPCs carry distinct combat and interaction state, so aggregation is a content/UI choice rather than a resolver requirement

Result: MT-516-mixed extends targeting to character scope without changing NPC listing behavior.

## Phase E — `target-N` elimination

Migrated command paths now use centralized ordinal resolution guidance instead of repo-local numbered-match prompts.

Known remaining gaps:

- corpse-specialized commands kept their existing narrowed resolution helpers
- global/admin search flows were intentionally not migrated in this dispatch
- default Evennia `look at`/admin examine surfaces were not changed because no project-local command implementation owned that path in the audited scope

## Phase F — Tests

Focused targeting tests:

```text
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_targeting
```

Result: `10` tests passed.

Coverage includes:

- newest-first resolution
- ordinal resolution for character scope
- mixed scope returning characters or room objects
- caller exclusion from character scope
- hidden character filtering
- explicit NPC-only scope behavior

Static validation:

- `py_compile` passed for all migrated command files in both migration batches
- editor diagnostics reported no errors in touched files

## Phase G — Live verification

Direct Django/Evennia runtime snippet created a temporary room, caller, two NPC goblins, and a dagger, then cleaned them up.

Observed output:

```text
{'auto_target_id': 27216, 'auto_scope': 'characters', 'newer_id': 27216}
{'ordinal_target_id': 27215, 'ordinal_scope': 'characters', 'older_id': 27215}
{'mixed_target': 'dagger', 'mixed_scope': 'room'}
Characters: goblin, goblin
```

Interpretation:

- `goblin` auto-targeted the most recently arrived NPC in character scope
- `second goblin` selected the older NPC via ordinal resolution
- `dagger` resolved through the same resolver call but won on room-object scope
- NPC room display remained separate and non-aggregated

Additional nearby validation:

- attempted `tests.scenarios.thief_counterplay`, but that module does not self-bootstrap Django settings under plain `unittest`, so it was not a useful regression signal for this dispatch

## Phase H — Docs

Updated documentation:

- `docs/architecture/object_presentation.md`

The document now covers mixed character/object scopes and records the explicit decision to defer NPC aggregation.

## Final state

MT-516-mixed completed the nearby mixed-target migration by extending the centralized resolver to character and NPC scope, migrating the local mixed command roster, preserving NPC display separation, and validating the new behavior with focused tests plus live runtime fixtures.

## Surfaced Gap And Fix

Post-ship smoke testing exposed a command-resolution miss that MT-516-mixed's audit
explicitly left out.

Observed symptom:

- `l twig` still produced default Evennia disambiguation using numbered suffixes
- `l first twig` and `l 1.twig` did not resolve through the centralized ordinal matcher

Audit conclusion:

- `look`/`l` were not on the migrated roster
- the project had no local `cmd_look.py`, so play still used Evennia's default
	`CmdLook`, which does a raw `caller.search(self.args)`
- the original artifact already called this out indirectly under known remaining gaps:
	default Evennia look/examine surfaces were not changed because no project-local
	command owned that path during the mixed migration

Fix shipped in MT-516-mixed-fix1:

- added a local `commands/cmd_look.py`
- wired it into `commands/default_cmdsets.py`
- preserved standard look rendering while resolving visible targets through the
	centralized resolver first, with fallback only for unmigrated search surfaces

Second surfaced gap from post-fix smoke testing:

- stack-aware commands could still hit ambiguity when fungible stack fragments coexisted
	in inventory, and ordinal drop forms on a healthy stack were not consistently treated
	as "drop one from this stack"

Fix shipped in MT-516-mixed-fix2:

- duplicate carried stacks now normalize before inventory-target resolution
- ordinal targeting against a single stack quantity is accepted by the resolver
- `CmdDrop` now interprets ordinal stack selection as a one-item stack split instead of
	moving the whole stack or falling into disambiguation