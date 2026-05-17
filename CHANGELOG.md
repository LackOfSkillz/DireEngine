# Changelog

## 2026-05-17

### DRG-RANGER-CLOSEOUT

- Closed the Ranger program as a shippable canonical playable profession after final local validation, live runtime smoke, and provenance cleanup review. No new canonical feature scope was added in closeout; the only production fix in this pass was a bounded robustness repair in `world/systems/ranger/companion.py` so dismiss now retries transient SQLite lock failures instead of failing the live companion removal path.
- Final executable validation stayed green on the recovered workspace task path: `Ranger Adjacent Regression` passed `102 passed, 138 subtests passed`, and the exact documented preservation batch passed `314 passed, 153 subtests passed`.
- Live runtime closeout smoke completed against the installed Crossing Ranger guildhall and persistent smoke fixtures after switching from noisy browser transport to direct Evennia/Django object-state proof. `ensure_crossing_ranger_guildhall()` re-established the canonical anchors in the live runtime, proving `Ranger Guild` plus Kalika presence and the off-class teaching refusal (`Only Rangers may train here.`).
- SAF closeout smoke reconfirmed the shipped gates and provenance boundaries in the live runtime: spellcasting modifier `-2` at SAF `-100`, off-class Ranger-spell penalty `+2`, bow load thresholds `1.1` / `0.9`, wilderness-only tease gate, howl `enhanced` / `trapped` split, multi-tier threshold at `-33`, display percent `(0 - saf)`, canonical SKIN scaling, drift bounds, guild-commitment clear to `0`, and the preserved forage-harm helper decrement as `directengine_canon` rather than canonical Ranger authority.
- Companion and sniping closeout seams both passed direct runtime proof on the persistent Ranger fixture. Wolf and raccoon call/dismiss paths succeeded, raccoon tease succeeded under the canonical wilderness + SAF threshold + bait conditions, and the shared sniping gate prepared successfully under `prepared_snipe` with overlay `ranger_directengine_canon` while the legacy `ranger_snipe` state remained absent.
- Final Ranger spell smoke covered all 23 shipped canonical `gsl_2004` rows across Animal Abilities, Wilderness Survival, and Wilderness Defense. At representative live smoke power, all 23 spells prepared, cast, and executed their effect path successfully; 17/23 also proved immediate target/room state at that standard smoke target. Follow-up disambiguation showed the remaining two utility-target spells (`swarm`, `plague_of_scavengers`) prove through their utility payload path, and the four contest-based debilitation spells (`mesmerize`, `haraweps_bonds`, `hobble`, `branch_break`) do apply struck target state when run at high power against a low-defense target. Closeout classification: no Tier 1 Ranger defect remains.
- Tier 2 carry-forwards remain documentation and future-expansion items rather than ship blockers: unresolved exact verb identity for S02847, optional full S01265 forage-table enumeration, future Thief rollout onto the already-shared sniping seam, and optional future Langenfirth/Tolle expansion once non-Crossing world growth is in scope.

## 2026-05-16

### DRG-RANGER-SNIPE-SHARED-MECHANIC-001

- Closed as a final Tier 1 Ranger reconciliation dispatch on the verified **B-path** rather than the earlier simplified `shared guild1` framing. Direct DireLore re-verification confirmed the controlling sniping canon remains real (`S10073`, `S10728`, `S11364`), but the learned-state gate is profession-specific: Rangers use `guild1` bit `0` for learned / bit `1` for revoked, while Thieves use `thieftrix` bit `31` for learned and `thieftrix2` bit `0` for revoked.
- The live repo had already been migrated to that shared-mechanic seam before this closeout pass. `typeclasses/characters.py` now routes sniping through profession-aware `prepare_snipe(...)`, enforces the canonical hidden/invisible requirement, and stores prepared state under the shared `prepared_snipe` key instead of the old Ranger-only `ranger_snipe` slot.
- Downstream combat consumers in `engine/services/combat_service.py` and `domain/combat/resolution.py` now read the shared prepared-snipe state first while preserving `ranger_snipe` fallback only as compatibility scaffolding. The canonical shared gate is therefore live for Rangers today and structurally ready for Thief integration later without another combat-state rename.
- Ranger-specific bond/focus and aim-retention math survived the audit as preserved `directengine_canon` augmentation layered on top of the canonical shared gate, not as contradictory canon to remove. The dispatch therefore kept the Ranger overlay behavior while correcting the gating/state model to the verified shared mechanic.
- Thief profession rollout remains explicitly deferred as a cross-program dependency, but the shipped gate is already profession-neutral at the decision point: future Thief work only needs to expose the profession/runtime surfaces, not redesign sniping preparation or combat-state consumption.

Validation:
- Focused sniping slice: `45 passed` in `tests/test_snipe_shared_mechanic.py` plus the touched combat regression slice.
- Ranger-adjacent batch: `95 passed, 138 subtests passed`.
- Exact documented preservation batch: `314 passed, 153 subtests passed`.

Live smoke:
- Completed a direct-runtime 8-scenario smoke against live fixtures after refining the harness away from a transient typeclass-instantiation issue. Verified hidden Ranger success, non-hidden rejection, off-class rejection, prepared accuracy math, prepared damage multiplier path, Ranger overlay preservation, shared-state naming (`prepared_snipe` present, `ranger_snipe` absent at prep), and no SAF interaction. Final matrix passed `8/8`.

### DRG-RANGER-GATE3-PROVENANCE-CLEANUP-001

- Small bounded provenance-cleanup dispatch per `DRG-RANGER-FORAGE-CANON-AUDIT-001` Option B. `RangerSafService.apply_forage_harm_cost(...)` remains in place and behavior is unchanged, but its stale `S00340` / `gsl_2004` claim was removed.
- `engine/services/ranger_saf_service.py` now classifies `apply_forage_harm_cost(...)` as `directengine_canon` and documents the audit finding directly in the method docstring: no canonical Ranger SAF authority for forage was found in the indexed DireLore corpus, and `S00340` is hide mechanics with a Paladin SAF branch.
- `tests/services/test_ranger_saf_service.py` now carries the matching provenance note on the focused Gate 3 regression test so the preserved decrement behavior no longer implies false GSL authority.
- Broader repo scan found other `S00340` mentions only in historical changelog and audit text that already record the negative finding; no additional forward-going code provenance sites required correction in this dispatch.
- Dispatch outcome: Gate 3 remains callable, tested, and unwired, but is now explicitly documented as DireEngine design machinery rather than canonical forage SAF wiring.

Validation:
- Focused Ranger SAF slice: `13 passed` in `tests/services/test_ranger_saf_service.py`.
- Exact documented preservation batch: `314 passed, 153 subtests passed`.
- Ranger-adjacent batch: `63 passed, 138 subtests passed`.

### DRG-RANGER-FORAGE-CANON-AUDIT-001

- Closed as a pure investigation dispatch with **Option B**: no verified canonical Ranger forage SAF authority was found in the available DireLore corpus, so no production code or test changes were made.
- Re-verified the previously cited `S00340` and confirmed it is `Hide mechanics`, not forage. Its only relevant `np0:saf` mutation is a Paladin hide-in-combat penalty, so it cannot support Ranger forage harm or Gate 3.
- Re-audited the actual forage scripts. `S00261` (Forage Utility #1), `S01265` (Forage Utility #2), and `S02456` (Generic Forage) all expose noun matching, item-table/profile data, and forage selection logic, but none contain SAF state, SAF mutation, or a harm-bearing classification model.
- Checked adjacent Ranger forage surfaces outside the forage utilities. `S00486` and `S03009` do contain forage branches, but the only verified SAF behavior there is `clear np0:saf` on Ranger guild commitment, not forage harm cost.
- Queried promoted and raw canon surfaces in DireLore (`canon_mechanics`, `facts`, `raw_pages`, `sections`, `canon_professions`). No forage+SAF mechanic was found; the only fact matches were false positives on `saffron` text, and the raw-page/section matches were generic content noise rather than a mechanical authority.
- Audit implication: the repo forage subsystem remains structurally ready for bounded future wiring, but current Gate 3 forage provenance in `RangerSafService.apply_forage_harm_cost(...)` and its unit test is unverified. Until a real forage SAF authority is found, that seam should be treated as `directengine_canon` or later deprecated rather than expanded.

Validation:
- Read-only investigation only. Executable validation was limited to DireLore query probes and repo reads; no repo tests or live smoke were run.

### DRG-RANGER-FORAGE-CANON-MODEL-001

- Halted in Step 0 as **Classification C**. No code changed, no tests ran, and no live smoke ran.
- The controlling canon citation from the prior halt did not survive re-verification. DireLore shows `S00340` is a hide-mechanics script with a Paladin SAF branch, not a forage script, so it cannot serve as authority for a Ranger forage harm-bearing model or Gate 3 wiring.
- Read-only audit of the owning repo surfaces confirmed the implementation is otherwise structurally ready for bounded wiring: `typeclasses/abilities_survival.py` carries the selected forage catalog entry all the way to the success branch, and `world/builder/content/forage_catalog.yaml` can absorb a bounded schema extension if canon support exists.
- DireLore verification of the actual forage surfaces (`S00261`, `S01265`, `S02456`) did confirm the resource-selection mechanics and item tables, but did **not** surface any Ranger SAF mutation, harm-bearing branch, or renewable-versus-harm-bearing classification model that could justify per-entry Gate 3 wiring. With the cited authority invalidated and no replacement forage+SAF script identified in this dispatch, shipping a harm-bearing model here would invent canon.
- Dispatch outcome: halt cleanly rather than fabricate `harm_bearing` classifications. The next forage follow-up must first re-establish the real canonical authority for forage-related Ranger SAF behavior before any schema or code changes proceed.

Validation:
- Read-only Step 0 audit only. No executable validation was run because the dispatch halted before edits.

### DRG-RANGER-COMPANION-LIFECYCLE-001b

- Second substantive companion implementation dispatch from the `DRG-RANGER-COMPANION-CANON-AUDIT-001` follow-up plan. Step 0 classified the work as **B**: the `001a` entity foundation was sufficient, but 001b still needed bounded owner-side hooks for movement, combat engagement, and death notification so the canonical behavior layer could ship without changing `RangerSafService`.
- `typeclasses/npcs.py` now gives `RangerCompanion` the missing behavior layer: canonical control verbs (`follow`, `stay`/`stop`, `return`, `whistle`, `find`, `sit`, `stand`, `hide`, `unhide`, `hunt`), bounded object handling (`get`, `drop`, `give`), bounded combat assistance, rescue/search-on-owner-death, and species-specific messaging keyed off the canonical raccoon/wolf split.
- `typeclasses/characters.py` now provides additive owner hooks rather than foundation rewrites. Rangers can route command verbs through `command_ranger_companion(...)`, companion follow state is honored on owner movement, companion assistance is triggered when the Ranger engages or is attacked, and owner death now notifies the active companion for the rescue/search flow.
- `commands/cmd_companion.py` now exposes the canonical 001b command surface in the existing verb wrapper instead of introducing a parallel command family. The command still supports inspect/call/dismiss, and now also routes `follow`, `stay`, `return`, `whistle`, `find`, `attack`, `get`, `drop`, `give`, `sit`, `stand`, `hide`, `unhide`, `hunt`, and `tease`.
- Gate 5 wiring remains additive and local. `RangerSafService.is_companion_tease_enabled(...)` stays untouched, while the behavior layer now applies the missing canonical context at the decision point: wilderness plus `SAF < -25` is required, and the tease path now also checks companion identity and bait item (`corn` for raccoon, `meat` for wolf) with species-specific messaging.
- Added focused behavior coverage in `tests/world/test_ranger_companion_behavior.py` for follow/stay/whistle flows, owner-driven combat assistance, death-triggered rescue/search, Gate 5 tease behavior, and companion object handling.

Validation:
- Focused 001b slice: `16 passed` across `tests/world/test_ranger_companion.py` and `tests/world/test_ranger_companion_behavior.py`.
- Adjacent seam batch: `42 passed` across `tests/world/test_ranger_companion.py`, `tests/world/test_ranger_companion_behavior.py`, `tests/services/test_ranger_saf_service.py`, and `tests/test_npc_aggro.py`.
- Editor diagnostics on all touched files returned clean.

Live smoke:
- Completed a direct-runtime 9-scenario smoke against temporary wilderness/urban fixtures. Verified raccoon summon, owner-follow movement, stay blocking follow, whistle recall, companion item get/give flow, Gate 5 raccoon tease success, wolf combat assist on offense, wolf combat assist on defense, and death-triggered rescue/search. All 9 scenarios passed.

### DRG-RANGER-COMPANION-LIFECYCLE-001a

- First substantive companion implementation dispatch from the `DRG-RANGER-COMPANION-CANON-AUDIT-001` follow-up plan. Step 0 classified the work as **B**: the repo's existing NPC base and persistence seams were sufficient, but the live Ranger API still consumed a dict-shaped companion view, so the bounded implementation included a compatibility layer while moving storage to a real entity model.
- `world/systems/ranger/companion.py` now owns the canonical companion entity foundation: the registry enforces Gap 4's only-valid types (`101 = raccoon`, `102 = wolf`), owner records now persist entity-backed companion state (`type_id`, `state`, `bond`, `entity_id`, `owner_id`), summon/dismiss lifecycle is entity-based, and invalid species are rejected explicitly instead of silently collapsing to wolf.
- `typeclasses/npcs.py` now defines `RangerCompanion`, a real NPC typeclass with constructor-level type enforcement, owner linkage, persisted companion state, species assignment, and bounded lifecycle hooks. This ships the real actor foundation that the canon audit required without pulling 001b control-surface or combat behavior into the slice.
- `typeclasses/characters.py` preserved the existing Ranger public API while changing the backing model. `get_ranger_companion()` now returns a normalized dict proxy built from the live entity when present, `get_ranger_companion_entity()` exposes the owning actor directly, and `call_ranger_companion(...)` / `dismiss_ranger_companion()` now summon and remove a real `RangerCompanion` entity instead of toggling a virtual `{type, state, bond}` blob.
- `commands/cmd_companion.py` now supports canonical species selection at the summon entry point via `companion call wolf` and `companion call raccoon`, while preserving the existing inspect and dismiss surface.
- Added focused coverage in `tests/world/test_ranger_companion.py` for registry enforcement, constructor enforcement, wolf/raccoon summon, invalid-species refusal, dismiss cleanup, persisted record rehydration, owner-link symmetry, and off-class refusal.

Validation:
- Focused 001a slice: `28 passed` across `tests/world/test_ranger_companion.py`, `tests/services/test_ranger_saf_service.py`, `tests/services/test_ranger_identity_migration.py`, and `tests/world/test_crossing_ranger_guild_build.py`.
- Ranger-adjacent batch: reconstructed explicit slice passed at `63 passed, 138 subtests passed` across `tests/world/test_ranger_companion.py`, `tests/services/test_ranger_saf_service.py`, `tests/services/test_ranger_identity_migration.py`, `tests/world/test_crossing_ranger_guild_build.py`, `tests/learning/test_guild_progression_commands.py`, `tests/learning/test_guildhall_locator.py`, and `tests/domain/test_spell_registry.py`.
- Exact documented preservation batch: `314 passed, 153 subtests passed`.
- Editor diagnostics on all touched files returned clean.

Live smoke:
- Completed the planned 8-scenario direct-runtime smoke against `SmokeRangerLive` and `SmokeClericLive` after temporarily relocating the Ranger fixture from `Limbo` into live non-urban rooms. Verified wolf summon, raccoon summon, Gap 4 enforcement at command entry and constructor layers, dismiss cleanup, persisted linkage across room movement, bidirectional owner linkage, and off-class summon refusal. All 8 scenarios passed, and both fixtures were restored afterward.

Not implemented in 001a:
- Control verbs (`find`, `get`, `sit`, `stand`, `follow`, `stay`, `return`) remain for `001b`.
- Combat assistance, whistle/recall flow, rescue/search behavior, rich species-specific messaging, and Gate 5 wiring remain for `001b`.

Next: `DRG-RANGER-COMPANION-LIFECYCLE-001b`.

### DRG-RANGER-COMPANION-CANON-AUDIT-001

- Pure investigation dispatch. No code changed, no tests ran, and no live smoke ran.
- Completed the canonical companion behavioral-model investigation that `DRG-RANGER-RECONCILE-COMPANION-001` deliberately deferred. The work stayed read-only and used DireLore to characterize the subsystem end to end before drafting implementation scope.
- Mapped the canonical companion script surface beyond the initial halt audit: the core Ranger companion model is not just `S02779`, `S05642`, `S03005`, `S11848`, `S00682`, and `S01034`, but also the surrounding lifecycle/support scripts `S02780`, `S02798`, `S02805`, `S02806`, `S02807`, `S02808`, and `S00554`.
- Confirmed the canonical command surface is materially richer than the current repo seam. `find`, `return`, and `follow/stay` are mechanically essential lifecycle verbs; `get/drop/give`, `hunt` versus raccoon scavenging, `hide`, and attack-oriented control hooks are also part of the companion actor model rather than flavor-only text.
- Characterized the canonical behavioral model: companions are real controlled actors with owner linkage, off-room movement, destination state, return/search flows, login/offline handling, rescue behavior, and type-specific messaging. Pure in-room virtual flavor state is not canonically sufficient.
- Refined Gate 5 from the earlier halt note: `S00682` confirmed wilderness (`urbanclass < 8`) plus `SAF < -25`, but the actual behavior is more specific than the current service helper. The tease path also depends on companion identity and held-item context, with distinct raccoon and wolf branches.
- High-level DireEngine infrastructure check found reusable NPC combat/movement seams already exist in `typeclasses/npcs.py`, including AI ticks, pursuit/retreat, combat targeting, and movement-related state. That means companion implementation likely does not need a separate generic NPC-AI foundation program.
- Scope recommendation synthesized from the investigation: **two** bounded lifecycle implementation dispatches, not one and not three. `DRG-RANGER-COMPANION-LIFECYCLE-001a` should cover entity representation, type registry, summon/return/dismiss, and persistence scaffolding; `001b` should cover the essential control surface, species-specific messaging, bounded combat/rescue behavior, and the fully contextual Gate 5 wiring.
- Findings were cached in `/memories/repo/repo-memory-ranger-canon-mechanic.md`, and the dispatch report was written to `/mnt/user-data/outputs/DRG-RANGER-COMPANION-CANON-AUDIT-001-report.md`.

### DRG-RANGER-RECONCILE-COMPANION-001

- Halted at Step 0 as **Classification C**. No code changed, no tests changed, and no live smoke ran.
- Audited the live companion seam before assuming bounded scope. `commands/cmd_companion.py` is only a thin wrapper over `call_ranger_companion()` / `dismiss_ranger_companion()`, while the owning data model in `world/systems/ranger/companion.py` and `typeclasses/characters.py` is only a persisted `{type, state, bond}` dictionary with `active/inactive` toggles.
- DireLore re-verification confirmed canonical companion mechanics are materially richer: canonical Ranger companions are only `101 = Raccoon` and `102 = Wolf`, and the corpus exposes companion control/return/follow lifecycle surfaces through `S02779`, `S05642`, `S03005`, `S11848`, plus SAF-linked verbs in `S00682` and `S01034`.
- The live owning seam is therefore not a bounded Gate 5 wire-up problem. It currently supports only `wolf`, has no verified raccoon path, no real companion entity lifecycle, and no canonical `find/get/sit/stand/return/follow` control surface.
- `RangerSafService.is_companion_tease_enabled(...)` still exists and remains preserved, but it is only a partial authority helper inside a broader subsystem that is not canonically represented end to end.
- Audit findings were cached in `/memories/repo/repo-memory-ranger-canon-mechanic.md`, and the halt report was written to `/mnt/user-data/outputs/DRG-RANGER-RECONCILE-COMPANION-001-HALT-report.md`.
- Recommended follow-up dispatch: `DRG-RANGER-COMPANION-LIFECYCLE-001`. Companion now joins forage-canon-model and snipe-shared-mechanic in the deferred Ranger Polish mini-program scope.

### DRG-RANGER-04-DEFENSE

- Implemented the canonical Ranger 407xxx Wilderness Defense Book in `domain/spells/spell_definitions.py` as 7 new `gsl_2004` rows: `compost`, `swarm`, `haraweps_bonds`, `awaken_forest`, `hobble`, `branch_break`, and `plague_of_scavengers`.
- Step 0 classified the dispatch as **B** after live DireLore verification. Gap 2 was re-verified live: raw `gsl.spells.effect_code IN (407007, 407008, 407009)` returned no rows and the promoted Ranger roster also surfaced no `407007-009` entries. The Ranger canon cache now carries the verified 407xxx CASTMOD table, the raw targeting corrections, and the promoted-name / effect-code mismatch notes for `Harawep's Bonds` and `Plague of Scavengers Ranger`.
- Preserved the bounded runtime plan without touching `engine/services/mana_service.py` or `engine/services/ranger_saf_service.py`: `engine/services/spell_effect_service.py` now routes `compost`, `swarm`, `awaken_forest`, and `plague_of_scavengers` through a bounded `ranger_room_effect` utility seam, while `haraweps_bonds`, `hobble`, and `branch_break` reuse the existing debilitation path with bounded post-hit state and damage handling.
- Extended `engine/presenters/spell_effect_presenter.py` with dedicated Wilderness Defense self/target/room/expiration messaging for all 7 new spells.
- Added focused regression coverage for the 407xxx registry metadata, Kalika's registry-derived Ranger teaching surface, the new room-state and debilitation runtime seams, the structured `compost` and `haraweps_bonds` pipeline slices, and the Defense-book SAF regression. Focused validation passed at `162 passed, 138 subtests passed` across `tests/services/test_mana_service.py`, `tests/services/test_spell_effect_service.py`, `tests/services/test_structured_spell_pipeline.py`, `tests/domain/test_spell_registry.py`, and `tests/learning/test_guild_progression_commands.py`.
- Broader validation remained green: the exact documented preservation batch passed at `314 passed, 153 subtests passed`, and the reconstructed Ranger-adjacent batch passed at `53 passed, 23 subtests passed`.
- Direct live runtime smoke on the persistent `SmokeRangerLive` fixture confirmed the live Ranger teaching and casting seams at temporary circle `10`: Kalika's canonical teaching allowlist still reports `23` spells, all 7 Wilderness Defense spells taught successfully in-band, off-class teaching refusal remained `Only Rangers may train here.`, and `compost`, `swarm`, `awaken_forest`, and `plague_of_scavengers` each prepared, cast, and persisted bounded room-state proof on the live `Ranger Guild` room. `branch_break` also proved SAF Gate 1 in live runtime without SAF service edits: Ranger SAF `-100` reported `spell_difficulty_modifier = -2` / `base_difficulty_modified = 11.0`, Ranger SAF `150` reported `0` / `13.0`, and off-class `SmokeClericLive` reported `+2` / `15.0`. The three debilitation spells (`haraweps_bonds`, `hobble`, `branch_break`) cast successfully on the live fixtures at representative prep, but the direct contest outcomes landed as misses during smoke, so live proof for those entries is cast-path and SAF-path coverage rather than struck-state application.

### DRG-RANGER-03-SURVIVAL

- Implemented the canonical Ranger 406xxx Wilderness Survival Book in `domain/spells/spell_definitions.py` as 6 new `gsl_2004` rows: `hands_of_lirisa`, `earth_meld`, `mesmerize`, `blend`, `breathe_water`, and `water_purification`.
- Step 0 classified the dispatch as **B** after live DireLore verification: `Hands of Lirisa` resolved directly from `effect_code = 406001`, while Earth Meld, Breathe Water, and Water Purification required script-name fallback, and Mesmerize / Blend needed explicit correction for mismatched promoted raw effect codes. The Ranger canon cache now carries the verified 406xxx CASTMOD table and the `S05692` versus `S08228` Water Purification split.
- Wired Ranger SAF Gate 1 into the structured casting path in `engine/services/mana_service.py` when a real `spell_id` is present, exposing the applied difficulty modifier in cast payloads so Earth Meld now proves the canonical `-2` Ranger bonus at SAF `-100` and the `+2` off-class penalty without touching `RangerSafService` itself.
- Extended `engine/services/spell_effect_service.py` with the bounded Survival-book runtime seams: Mesmerize now pacifies a struck target through the existing debilitation path, Water Purification now records a bounded room-state purification effect, and the remaining non-combat Survival spells ride the existing Ranger utility-boon seam with capability flags and raw CASTMOD provenance preserved on live effect state.
- Extended `engine/presenters/spell_effect_presenter.py` with dedicated Wilderness Survival self/target/room/expiration messaging for the new utility effects and Mesmerize's pacification messaging.
- Added focused regression coverage for the 406xxx registry metadata, Kalika's registry-derived Ranger teaching surface, the structured Hands of Lirisa utility path, Mesmerize pacification, Water Purification room-state mutation, and the SAF-cast difficulty plumbing. Focused validation passed at `154 passed` across `tests/services/test_mana_service.py`, `tests/services/test_spell_effect_service.py`, `tests/services/test_structured_spell_pipeline.py`, `tests/domain/test_spell_registry.py`, and `tests/learning/test_guild_progression_commands.py`.
- Direct live runtime smoke on the persistent `SmokeRangerLive` fixture confirmed the new Survival seams on real objects. The fixture was temporarily uplifted from circle `2` to circle `8` for this dispatch. `hands_of_lirisa` prepared, cast, and persisted a live utility effect with `castmod_a3 = 064167002`; `earth_meld` cast at SAF `-100` reported `spell_difficulty_modifier = -2` and at SAF `150` reported `0`; `SmokeClericLive` cast from the Ranger room reported the canonical off-class penalty `spell_difficulty_modifier = 2`; and `water_purification` persisted bounded room-state proof on the live `Ranger Guild` room.

### DRG-RANGER-02-ANIMAL

- Implemented the canonical Ranger 405xxx Animal Abilities Book in `domain/spells/spell_definitions.py` as 10 new `gsl_2004` rows: `wolf_scent`, `see_the_wind`, `spider_climb`, `eagle_vision`, `cheetah_swiftness`, `bear_strength`, `caiman_swim`, `grizzly_claw`, `senses_of_the_tiger`, and `wisdom_of_the_pack`.
- Step 0 classified the dispatch as **B** after live DireLore verification: raw CASTMOD detail and script numbers were recoverable for all 10 spells, but 405004-405010 required script-name fallback because the raw `gsl.spells.effect_code` index is incomplete for several Animal Abilities rows. The repo canon cache was updated with the verified `a0`/`a1`/`a3` table and raw targeting evidence.
- Preserved the existing canon-policy exclusion for `Claws of the Cougar` and corrected the raw naming divergence for `Grizzly Claw` versus promoted modern `Grizzly Claws`.
- Extended `engine/services/spell_effect_service.py` with generic self-only / other-only targeting guards for structured augmentation and utility spells, plus a bounded `ranger_boon` utility path so the non-combat Animal Abilities buffs persist through the existing structured state seam with capability flags and raw CASTMOD provenance attached to live effect state.
- Extended `engine/presenters/spell_effect_presenter.py` with dedicated Ranger Animal Abilities self/target/room messaging for the shipped utility and augmentation entries.
- Added focused regression coverage for the new spellbook metadata, Kalika's registry-derived Ranger teaching surface, the representative `wolf_scent` live utility effect state, and `grizzly_claw` other-target enforcement. Focused validation passed at `41 passed` across `tests/domain/test_spell_registry.py`, `tests/learning/test_guild_progression_commands.py`, and `tests/services/test_structured_spell_pipeline.py`.
- Direct live runtime smoke on the persistent `SmokeRangerLive` fixture confirmed the new state seam on real objects: `wolf_scent` prepared, cast, and persisted a live utility effect with `gsl_spell_id = 405001` and `castmod_a3 = 060182006`, and `grizzly_claw` rejected self-cast with `You need a valid target for that spell.` while applying successfully to Kalika as a live augmentation effect. Fixture limitation preserved: `SmokeRangerLive` is still circle `2`, so high-book Ranger NPC teaching and mana-gated cast proof for later-book entries remain partially constrained without temporary fixture uplift.

### DRG-INFRA-CANON-DISCIPLINE-DIRELORE

- Established DireLore as the program's primary canonical authority for GSL canon lookups and updated `/memories/repo/canon-authority-discipline.md` to treat repo memory as the cache of verified findings and architectural decisions rather than the sole transcription layer for raw canon detail.
- Step 0 verified live DireLore connectivity with `psycopg` against `localhost:5432`; `SELECT current_database(), current_user` returned the confirmed connection identity `direlore` / `user`, so the discipline note now records the verified connection parameters `host=localhost`, `port=5432`, `database=direlore`, `user=user`, `password=pass`.
- Documented the live schema discovery rule and the actual DireLore contract discovered during the audit: `108` non-system tables across contract/playbook views, promoted canon tables, raw GSL tables, map/room tables, and supporting entity/fact/page tables. The note now captures the key identifier mismatch that future dispatches must respect: promoted `public.canon_spells.id` is an internal row id, raw numeric spell ids live in `gsl.spells.effect_code`, and raw script numbers live in `gsl.scripts.script_number`.
- Verified representative query patterns and recorded them in the discipline note: `Wolf Scent` resolves through the promoted and raw spell surfaces as `public.canon_spells.id = 559`, `gsl.spells.effect_code = 405001`, and `gsl.scripts.script_number = 3366` / `origin/S03366.txt`; profession spell lookup works through `public.profession_spells`; area alias normalization works through `map.area_aliases`; room/area lookups work through `map.rooms`.
- Recorded the important operational caveat that promoted DireLore rows are not automatically final program canon: the verified Ranger promoted roster still surfaces entries like `Claws of the Cougar`, so dispatches must continue applying repo canon policy and prior memory decisions on top of DireLore results.
- Updated the durable provenance taxonomy so `gsl_2004` now means canonical 2004 GSL behavior verified either via DireLore or the legacy Claude sandbox, and narrowed the halt rule to only stop when required canon detail is absent from memory and DireLore is unreachable or lacks the needed detail.
- No code changed. No tests changed. Dispatch report written to `/mnt/user-data/outputs/DRG-INFRA-CANON-DISCIPLINE-DIRELORE-report.md`.

### DRG-RANGER-FOUNDATION-001b

- Restored the canonical Ranger guildhall as a dedicated builder module at `world/areas/crossing/ranger_guild/build.py`, following the existing Empath/Cleric Option C pattern while keeping the provisional Landing anchor at `Cracked Bell Alley, East Reach` and `region_name = "The Landing"`.
- Added `RangerGuildleader` for Kalika in `typeclasses/npcs.py`, wired canonical guild speech and bounded advancement feedback, restored Ranger registration in `engine/services/guildhall_locator.py`, and extended `engine/services/circle_service.py` so Ranger leader lookup works again in-room.
- Startup now restores Ranger after the preserved 001a teardown pass: `_ensure_new_player_tutorial()` still executes `_deprecate_ranger_guildhall_installation(...)`, then calls `ensure_crossing_ranger_guildhall()` so every startup rebuilds the canonical Kalika hall cleanly instead of reviving Elarion's retired bootstrap.
- Repaired the Ranger commitment seam in `typeclasses/characters.py` so joining through Kalika now clears canonical SAF to `0` via `RangerSafService.clear_on_guild_commitment(...)`.
- Added focused regression coverage for the restored locator, Kalika inquiry/teaching seam, the new builder module, and SAF-clear-on-join; focused validation passed at `23 passed`.
- Live runtime smoke completed green as a 14-scenario matrix using direct Evennia/Django object-state proof on the installed hall and the persistent `SmokeRangerLive` fixture: 5 foundation scenarios (`hall-and-route`, `locator-and-leader`, `join-commitment`, `guild-inquiry`, `advancement-feedback`) and 9 Ranger identity/SAF scenarios (`display-percent`, `payload-export`, `subsystem-state`, `ranger-spell-modifier`, `offclass-penalty`, `bow-load-thresholds`, `forage-harm-cost`, `companion-tease-gate`, `howl-threshold-skin-drift`) all passed `14/14`.
- Operational note preserved: synthetic orphan characters in this environment do not expose the `join` / `ask` command surface cleanly, so the live smoke was taken against the owning runtime seams (`join_profession(...)`, Kalika `handle_inquiry(...)`, locator lookup, and Ranger SAF/identity services) rather than the parser wrapper.

### DRG-RANGER-FOUNDATION-001a

- Deprecated the homegrown Landing Ranger Guild installation so the canonical `Ranger Guild` identity can be reclaimed by Kalika in 001b.
- `server/conf/at_server_startstop.py` no longer bootstraps Elarion's multi-room Ranger hall. Startup now actively removes the persisted Ranger hall rooms, alley access exit, and attached NPC/vendor contents, leaving an intentional no-Ranger-guildhall intermediate state.
- `typeclasses/npcs.py` no longer defines `RangerGuildmaster`, `RangerMentor`, or the four mentor subclasses. `engine/services/circle_service.py` no longer imports Ranger guildleader classes, and Ranger join fallback messaging in `typeclasses/characters.py` is now neutral rather than Elarion-specific.
- `engine/services/guildhall_locator.py` no longer registers `ranger -> Ranger Guild`; `tests/learning/test_guildhall_locator.py` now treats Ranger as intentionally unbuilt until 001b restores the canonical guildhall.
- Removed CLI/runtime exposure for the hall-dependent Ranger DireTest scenarios (`ranger-join`, Ranger advancement/inquiry, Ranger forage/skin hall scenarios, `ranger-high-hide-shop`) while keeping non-hall Ranger scenarios available.
- Validation green: preservation batch `302 passed, 107 subtests passed`, Ranger-adjacent batch `71 passed`, focused SAF + identity slice `16 passed`, focused locator slice `6 passed`, focused stat-trainer slice `9 passed`.
- Direct runtime smoke verified the intentional intermediate state: no `Ranger Guild` rooms remain, `find_guild_leader_for_profession(..., "ranger")` returns `None`, `get_guildhall_room_key("ranger")` returns `None`, Empath and Cleric guildhalls still exist, and no player characters are located or homed in the removed Ranger hall rooms.
- Full in-band Evennia reload was not executed during this dispatch; import/bootstrap safety was validated by direct Django runtime invocation of `_ensure_new_player_tutorial()` instead.

### DRG-INFRA-GUILDHALL-AUDIT

- Pure read-only audit answering whether current guildhall architecture is already reusable for multi-city deployment. No code changed and no tests ran.
- Audited 7 dimensions: Empath guildhall structure, Cleric guildhall structure, Landing Ranger startup bootstrap, guildleader typeclass pattern, guildhall locator service, cross-class duplication, and multi-city readiness.
- Findings: Empath and Cleric already follow a repeatable dedicated-builder-module pattern, but all current guildhalls are still city-coupled through hard-coded lane anchors, region tags, POI/access wiring, and profession-specific room keys. Ranger remains the outlier, still embedded in `server/conf/at_server_startstop.py` instead of a dedicated area builder.
- Evidence-based recommendation: **Option C**. `DRG-RANGER-FOUNDATION-001` should build Crossing Ranger as a dedicated builder module with explicit separation between canonical guild content and Crossing-specific placement, without extracting a generic guildhall template yet.
- Durable architecture note written to `/memories/repo/guildhall-architecture.md`.
- Audit report written to `/mnt/user-data/outputs/DRG-INFRA-GUILDHALL-AUDIT-report.md`.

### DRG-RANGER-RECONCILE-IDENTITY-001b

- Migrated Ranger identity state to canonical `RangerSafService` via compatibility adapter: `db.wilderness_bond` reads and writes now route through `db.canonical_saf` per S00264 environmental affinity model.
- Migrated outward consumers to canonical SAF reads: `typeclasses/characters.py` accessor seam, `domain/combat/resolution.py` snipe mastery, `typeclasses/rooms.py` trail strength, `world/professions/subsystems.py` subsystem snapshot, `commands/cmd_stats.py` status display, `world/area_forge/character_api.py` builder payload.
- Migrated `tick_ranger_state` drift logic to `RangerSafService.tick_drift(ranger, urbanclass)`.
- Added focused regression coverage at `tests/services/test_ranger_identity_migration.py`.
- Validation green: focused SAF + migration + combat slice `40 passed`, Ranger-adjacent batch `71 passed`, documented preservation batch `302 passed, 107 subtests passed`.

**Architectural finding (Step 0):** The remaining homegrown helpers (`nature_focus`, beseech math, trail strength, snipe accuracy/damage bonuses, keep-distance bonuses) are not vestigial — they implement real Ranger features without GSL canonical analog. Per DRG-CANON-POLICY-001 B-decision, these reclassify as `directengine_canon` and are preserved. Legacy helper deletion explicitly deferred — the canonical reconciliation program targets canonical-aligned identity + canonical spell content, not removal of DireEngine-specific Ranger features.

**Live smoke deferred:** 9-scenario matrix from 001b's Decision 7 will run after DRG-RANGER-FOUNDATION-001 creates a `SmokeRangerLive` fixture via Kalika's Crossing guildhall (or absorbed into FOUNDATION-001's own smoke scope).

### DRG-RANGER-RECONCILE-IDENTITY-001b-CLOSE

- Pure documentation closeout. No code changed.
- Appended `Remaining Homegrown Ranger Mechanics (post-001b)` to the Ranger canon memory note, classifying every remaining homegrown helper as `directengine_canon` with explicit reconciliation policy.
- Captured the architectural lesson that not every homegrown system is vestigial; behavior without canonical analog defaults to preserve, not delete. Applies to future COMPANION-001, SNIPE-001, and FORAGE-001 reconciliation dispatches.
- Wrote the 001b dispatch report at `/mnt/user-data/outputs/DRG-RANGER-RECONCILE-IDENTITY-001b-report.md`.

### DRG-RANGER-RECONCILE-IDENTITY-001a

- Built the canonical additive Ranger SAF service at `engine/services/ranger_saf_service.py` with the bounded 12-method surface and `HowlState` enum, without migrating any live Ranger consumer.
- Added the canonical persisted state slot `db.canonical_saf` to character creation/default backfill while keeping `wilderness_bond`, `nature_focus`, companion, forage, snipe, and skin runtime untouched.
- Added focused service coverage for SAF clamping, thresholds, howl state, drift, and related authority seams.
- Validation remained green: focused SAF slice `13 passed`, Ranger-adjacent batch `71 passed`, exact documented preservation batch `302 passed, 107 subtests passed`, and no editor errors in the touched files.

### DRG-RANGER-RECONCILE-PROFESSION-001

- Reconciled Ranger profession identity from survival-primary to canonical Primary Magic primary in the live profession profile.
- Migrated the only live non-test consumer seam that still encoded the retired identity: Ranger practice-XP weights now emphasize magic over survival, while runtime wilderness_bond, nature_focus, companion, forage, and snipe systems remain untouched.
- Added focused regression coverage for Ranger profile placement, EXP tier lookup, magic-slot curve, and null-pool bootstrap behavior.
- Validation remained green: focused migrated slice `37 passed`, Ranger-adjacent batch `71 passed`, and the exact documented preservation batch `302 passed, 107 subtests passed`.

# DRG-RANGER-CANON-AUDIT-02 — REVISED — Memory Transcription of Verified Findings

**Type:** Pure memory transcription dispatch. The canon investigation has ALREADY happened in Claude's conversation context (Claude has GSL corpus access; the local agent does not). This dispatch transcribes those verified findings into the Ranger canon memory note. No GSL access required by the executing agent.
**Output:** Updated `/memories/repo/repo-memory-ranger-canon-mechanic.md` with 8 of 10 gaps fully closed, 2 partially closed, plus new Canonical Reference Index section. No code, no tests.
**Estimated touch:** 0 lines of code. ~15-20 min agent time. One memory file update.
**Sequencing:** Replaces the prior DRG-RANGER-CANON-AUDIT-02 dispatch that halted on missing GSL access. Prerequisites: prior dispatch halted with no edits made (confirmed in transcript). Next: DRG-RANGER-RECONCILE-PROFESSION-001 from complete canonical authority.

---

## Context: Why this dispatch is revised

The original DRG-RANGER-CANON-AUDIT-02 instructed the local agent to "do a GSL deep-dive." That was a mistake. The local agent has no access to the GSL corpus at `/tmp/origin_verify/origin/` — that path exists only in Claude's conversation sandbox, not on Gary's local filesystem.

The agent correctly halted on the GSL-access gate without making edits. This dispatch fixes the layer error: **Claude (with GSL access) does the canon investigation; the local agent transcribes verified findings into memory.** Same pattern that worked for every canonical claim in the Cleric and Empath programs.

The findings below were verified by direct GSL inspection in Claude's conversation context during this session. Each cites the source S-script for traceability. The agent's job is to write these into the memory note via single-section-rewrites per the established memory hygiene pattern.

---

## Step 0 — Audit prep

Time-boxed to 5 minutes. **No memory edits during Step 0.**

### Step 0a: Prereqs

- DRG-RANGER-AUDIT closed as Classification C (CHANGELOG check)
- Prior DRG-RANGER-CANON-AUDIT-02 attempt halted with NO edits made (verify by re-reading the Ranger canon memory note; the "Known Canon Gaps" section should still have all 10 gaps unchanged)
- `/memories/repo/repo-memory-ranger-canon-mechanic.md` exists with 10 documented gaps in "Known Canon Gaps" section

### Step 0b: Confirm clean slate

Re-read the Ranger canon memory note's "Known Canon Gaps" section. Confirm:
- All 10 gaps are present unchanged
- No partial transcription happened from the prior failed attempt

If anything's been modified, surface for review before proceeding.

---

## Frozen design decisions

### Decision 1: Pure memory transcription, zero investigation

The agent does NOT need to verify the GSL findings below. They were verified by Claude in this session against the GSL corpus. The agent's job is to transcribe them faithfully into the memory note.

If the agent doubts a finding, surface it — don't try to verify it independently (you can't; you don't have GSL access).

### Decision 2: Single-section-rewrites per memory hygiene discipline

Each gap entry in the "Known Canon Gaps" section gets rewritten in place to reflect the new finding. Sections elsewhere in the note that reference the gap also get rewritten where appropriate (e.g., the 405xxx spell table now includes Claws of the Cougar as "stub spell, do not implement").

This is the memory hygiene "single-section-rewrite allowed when content is explicitly superseded" pattern, applied to multiple sections within the same dispatch.

### Decision 3: Canonical Reference Index gets appended

Per the original DRG-RANGER-CANON-AUDIT-02 plan, append a Canonical Reference Index section at the end (before version history) consolidating S-script citations. The list of citations is provided below.

### Decision 4: Version history entry

Add a single new entry to the version history at the file's end, dated 2026-05-15, noting that canon gaps were closed via Claude-side GSL investigation transcribed into memory.

### Decision 5: Findings cite source scripts

Every closed gap entry cites the source S-script(s). Pattern matches the existing Ranger memory note: `(S00264)`, `(S00485 lines 230-250)`, etc. Citations make the canon traceable.

---

## Step-by-step execution

### Step 1: Step 0 verification

Per Step 0a-b. Output: confirmation prior dispatch halted clean.

### Step 2: Transcribe verified findings — Gap-by-gap rewrites

**Gap 1 — Wisdom of the Pack (405010) targeting: CLOSED**

Rewrite the gap entry to:

```markdown
1. **Wisdom of the Pack (405010) targeting:** VERIFIED self-cast only.
   Per S12148: `$OTHER` block sets `$BREAK to 1` (disallow casting at
   others); `$SELF` block clears `$BREAK` (allow self-cast); `$OBJECT`
   block sets `$BREAK to 1` (disallow inanimate targets); `$OFFENSE`
   block clears `$BREAK` (non-offensive). Standard self-cast Ranger
   buff. (S12148 lines 104-130)
```

Also update the 405xxx Animal Abilities Book table — Wisdom of the Pack target column changes from `self (assumed)` to `self`.

**Gap 2 — Spells 407007/407008/407009 sequence: CLOSED (CONFIRMED ABSENT)**

Rewrite the gap entry to:

```markdown
2. **Spells 407007/407008/407009:** VERIFIED absent from GSL corpus.
   No script files contain references to these spell IDs. Wilderness
   Defense Book sequence: 407001 Compost, 407002 Swarm, 407003 Harawep's
   Bonds, 407004 Awaken Forest, 407005 Hobble, 407006 Branch Break,
   gap (407007-009), 407010 Plague of Scavengers. The gap represents
   cut content or unfinished design that didn't ship in 2004 canon.
   DireEngine implementation should match: 7 spells in Wilderness
   Defense Book, IDs 407001-407006 and 407010.
```

Also remove "(gap at 407007-009)" from the 407xxx table heading; the gap is now confirmed canonical.

**Gap 3 — Claws of the Cougar (S12145) spell ID: CLOSED (STUB)**

Rewrite the gap entry to:

```markdown
3. **Claws of the Cougar (S12145) spell ID:** VERIFIED stub script.
   S12145 (Jason Collette / GM Paklin, 09/23/03) contains ONLY the
   `$NAME` block setting `t0 = "Claws of the Cougar"`. No CASTMOD, no
   spell ID, no effect logic, no targeting blocks. The script body
   terminates at line 34 with a file separator character. This was
   in-development canonical content that never shipped. **DireEngine
   should NOT implement Claws of the Cougar.** The Animal Abilities
   Book contains exactly 10 canonical spells (405001-405010).
```

Also update Special Mechanics / 405xxx section: remove the "Candidate additional Ranger spell: Claws of the Cougar" note from the canon memory (it's not canonical).

**Gap 4 — Full companion system mechanics: CLOSED**

Replace the brief "Animal Companion" section in Special Mechanics with:

```markdown
### Animal Companion (`np0:companion`)

**Canonical companion types** (only two exist in GSL corpus):
- **101 = Raccoon** (S03005 sets `nc1:noun to "raccoon"`)
- **102 = Wolf** (S05642 sets `nc1:noun to "wolf"`)

No other canonical companion types exist. Bear, hawk, cat, etc. are
NOT canonical in 2004 GSL.

**Control script:** S02779 — companion command surface includes FIND,
GET, SIT, STAND, RETURN, FOLLOW, NOCOMPOST plus standard familiar verbs.

**Call/Summon script:** S05642 — handles initial companion creation
and resummon. Routes companion type to noun assignment.

**Lifecycle:** Companion state persists on `np0:companion` field (and
`np0:compborn` for birth time per S00682 TEASE reference). Logout
persistence canonical; details in S02779.

**SAF interaction (canonical, verified Gap 8):** Several wilderness
verbs check both companion presence AND Ranger SAF — wolf companion
+ SAF < -25 in wilderness enables enhanced howl interaction (S01034),
tease-companion interaction (S00682), and companion-related skill
bonuses elsewhere.
```

**Gap 5 — Level milestones beyond 1-2 and 4-5: CLOSED**

Replace the partial "Ranger Guild Promotion Milestones" section with:

```markdown
### Ranger Guild Promotion Milestones (canonical from S00485 $PROMOTE)

- **Every level 1-5 promotion**: `200 * level` XP awarded in Primary
  Magic (skill 44) via S00157 utility. (S00485 lines 220-230)
- **Level 2 promotion**: Kalika delivers the wilderness affinity speech
  ("an almost innate survival in the wilderness... Be wary of the
  seductive ease of the city"). First explicit canonical introduction
  of Ranger SAF concept to the player.
- **Level 4 promotion**: Extra 400 XP in Primary Magic (Base Magical
  Ability bonus). (S00485 lines 247-250)
- **Levels 6+**: NO fixed Primary Magic XP grant on promotion (the
  `if (np0:level < 6)` gate). Higher-level promotion grants depend on
  spell slot eligibility checks only.
- **Spell slots**: Granted via S01155 `$GIVE_NEW_SLOTS` central utility
  (cross-class). Eligibility check on every promotion; awarded when
  `np0:newspells` increases. (S00485 lines 255-265)
- **Medium-level milestone**: At `no1:ddata1` (configurable per guild
  prop, NOT hardcoded level): "greater control over training" speech.
  Standard DR pattern — milestone levels stored in the guild's prop
  varfields, not the script.
- **High-level milestone**: At `no1:ddata2`: "ultimate control over
  training" speech.
- **Highest-level milestone**: At `no1:ddata3` (declared in $PROMOTE
  header comment; specific behavior not in visible script body).

**Note on level cap:** S00485 does not document a canonical Ranger
level cap; the `no1:ddata4` field is described as "end of highest
level??" suggesting it MAY define a cap but the script body uses it
ambiguously.
```

**Gap 6 — Forage table contents (S01265): PARTIALLY CLOSED**

Rewrite gap entry to:

```markdown
6. **Forage table contents (S01265):** PARTIALLY VERIFIED. S01265 is
   the canonical "Forage Utility #2" containing per-item profile data
   for forageable items. 594 lines total. Table structure:
   - `t2` set to noun (e.g., "grass", "tuft of", etc.) by caller
   - `v1`/`v2` returned: vegetation types where item can be found
     (decimal-packed format: e.g., `v1 = 130107` means types 1, 7, 13)
   - `a1`/`a2` returned: difficulty percentages per vegetation type
     (e.g., `a1 = 207533` means 150% likelihood in type 1, 66% in 7,
     40% in 13)
   - `a4` returned: maximum exp award for foraging that item
   - `a5` returned: percentage chance to find in other terrain types
   - `b1`-`bN` returned: item profile (weight, volume, value) for
     creation
   - Hidden-mode foraging (`no0:hidden`) routes to a different code
     path using table 538 — likely the "secret/rare" forage path
   - Terrain control via `a6`/`a7` (main/secondary vegetation), `a0`
     (lushness %), `a8` (soil), `a9` (terrain type)

   **Item enumeration partial:** Sample items confirmed: tuft of grass,
   rocks, hulnik grass, muljin, sufil sap, flowers (blue/red variants).
   Full item list spans hundreds of entries; not fully enumerated this
   session.

   **DireEngine implementation note:** The exact item table is large
   enough that a faithful canonical port would be its own focused
   dispatch. A minimal canonical forage with ~10 representative items
   per major terrain type satisfies the canonical pattern; full table
   port is optional follow-up.
```

**Gap 7 — Sniping mechanic details: CLOSED**

Replace the brief "Sniping" subsection with:

```markdown
### Sniping (canonical from S10073 + S10728 + S11364)

**Shared mechanic:** Both Ranger (profession=2) AND Thief (profession=6)
can snipe. Underlying ranged-attack chain: S10073 (snipe verb) calls
S00078 (FIRE verb) for the actual attack resolution.

**Ranger gate (`np0:guild1` varfield):**
- Bit 0 = 1: Knows how to snipe
- Bit 1 = 1: Has abused snipe; ability revoked
- Both bits 0 in initial state — Rangers don't auto-learn snipe at any
  level

**How a Ranger learns snipe:** Via guild leader speech interaction.
S10728 contains the canonical SNIPESPEECH multi-stage teaching dialog
(originally with Tolle at Langenfirth per script text, but routed
through S11701 shared Ranger Guildleader subscript so Kalika at the
Crossing teaches it too). Player asks guild leader about "snipe" or
"sniping"; speech delivered in stages via timed effects (`code 10728000`,
6-second interval per stage). At conclusion, `np0:guild1` bit 0 set.

**Snipe requirements:**
- Must be hidden or invisible (`np0:hidden || np0:invisible`)
- Must have bow loaded (routed through standard load mechanic, S00076)
- Must have ranged weapon attached (`no1:profile` check excludes
  non-ranged weapons via 1599-1610 range exclusion)

**Skill checks (S11364 $SNIPE_SKILL):**
- Stealth skill (skill 61 hiding) for award + difficulty
- Aim, perception, and target-awareness factor into hit chance
- Killing blow on a hidden target awards bonus stealth XP via $AWARD_KILL

**Anti-grief gating (S10073 lines 200+):**
- GM log when sniper is 2x target's level (`np0:level > np1:level*2`)
- Murder tracker integration for player-vs-player snipes
- Guild leader can revoke ability via guild1 bit 1

**Dual-arrow loading interaction (S00076):** Rangers can pre-load two
arrows and fire both via the snipe sequence (canonical Ranger +
Barbarian dual-load combined with snipe).
```

**Gap 8 — Complete SAF gate audit: CLOSED**

Replace the "What Ranger SAF Gates" subsection with:

```markdown
### What Ranger SAF Gates (comprehensive canonical enumeration)

Ranger SAF gates the entire Ranger wilderness identity. Every
wilderness-themed verb interacts with SAF. Verified gates:

1. **Spellcasting difficulty (S03371 Earth Meld reference pattern):**
   Ranger + SAF == -100: `b9 -= 2` (bonus). Non-Ranger casting Ranger
   spell: `b9 += 2` (penalty). This is the canonical reference; other
   Ranger spells likely apply similar logic.

2. **Bow loading (S00076 LOAD verb):**
   - Ranger + SAF < -50: `a1 *= 11/10` (+10% bonus to load skill)
   - Ranger + SAF > 75: `a1 *= 9/10` (-10% penalty)

3. **Forage harm (S00340):** Some forage actions COST SAF
   (`np0:saf -= 1`) when they harm wild things — Ranger has explicit
   consequence for breaking wilderness, mirroring Empath consequence
   for harming sentients but much smaller magnitude.

4. **Guild commitment (S00486 Crossing + S03009 Langenfirth):** SAF
   `clear`-ed to 0 on guild join. Fresh start for new Rangers.

5. **Companion teasing (S00682 TEASE):** Wilderness (`urbanclass < 8`)
   + SAF < -25: special companion interaction enabled.

6. **Howl × wolf companion (S01034):**
   - Wilderness + SAF < -25 + wolf companion: enhanced howl
   - SAF > -1 attempting stealth howl: "trapped milk cow" failure

7. **Multi-tier verb (S02847):** SAF > -33 triggers one path, otherwise
   another. (Script body not fully read this session — likely TRACK,
   SCOUT, or similar Ranger-themed verb.)

8. **SAF percent display (S04537):** SAF expressed as percentage via
   `(0 - np0:saf)` — UI representation of how "wild" the Ranger is.

9. **Skin yield (S04627 SKIN):** Ranger SKIN bonus formula:
   `v7 = 15 + ((np0:level/4) * ((100 - (np0:saf + 100)) / 100))`
   Better (more negative) SAF = better skinning result.

**Architectural implication:** A canonical RangerSafService needs to
support these gate types:
- Spellcasting modifier (binary -100 check OR graduated)
- Skill difficulty modifier (SAF < -50, SAF > 75 thresholds)
- Bonus multiplier on Ranger-themed actions (SKIN, FORAGE)
- Boolean gates (`< -25` enables behavior, `> -1` disables)
- SAF mutation by actions (forage harm decrements SAF)
- Display percentage representation
```

**Gap 9 — Magic realm verification: CLOSED**

Rewrite "Magic realm" entry in Profession Identity section:

```markdown
- **Magic realm:** **Life realm (realm 4)** — VERIFIED. Per S01555:
  `is 4 ! life: rangers & empaths` with check
  `if ((NP0:profession=2)|(NP0:profession=4))`. Ranger shares realm 4
  with Empath. Full realm constants:
  - Realm 1 = Elemental (Warmage)
  - Realm 2 = Holy (Paladin, Cleric)
  - Realm 4 = Life (Ranger, Empath)
  - (Realm 3 = mental or arcane; not directly relevant to Ranger work)
```

**Gap 10 — Other-city guild leaders: CLOSED (CANONICAL CORPUS HAS ONLY TWO)**

Rewrite "Other canonical guild leaders by city":

```markdown
- **Other canonical guild leaders by city:** ONLY TWO canonical Ranger
  guildhalls exist in the 2004 GSL corpus:
  - **Kalika** — The Crossing (S00485 NPC + S00486 guild room script).
    Elven woman, ash longbow, falchion. Verbose canonical philosophy
    speech in $GUILD section.
  - **Tolle** — The Langenfirth (S03009 guild room script). Detail
    sparser than Kalika but uses parallel join/promote/teach surface.
  
  No Ranger guildhalls in Riverhaven, Shard, Aesry, Hibarnhvidar,
  Theren, Ratha, or other DR cities exist in the 2004 corpus. Those
  may exist in modern DR canon but not in our canonical reference.
  
- **DireEngine reference:** Kalika at the Crossing matches the Empath
  Merla precedent. Tolle at the Langenfirth is canonical-valid as a
  second guild for a non-Crossing city if/when DireEngine expands
  beyond the Crossing.
```

### Step 3: Append Canonical Reference Index

Before version history, append:

```markdown
## Canonical Reference Index

Quick lookup of all S-script citations used in this memory note.
Sorted by S-number.

| Script | Subject | Used For |
|--------|---------|----------|
| S00076 | LOAD verb | Dual-arrow loading (Ranger + Barbarian); SAF skill modifier |
| S00078 | FIRE verb | Underlying ranged-attack mechanic for snipe |
| S00157 | Skill XP utility | Primary Magic XP grants per promotion |
| S00256 | CARVE verb | Critter harvesting (cross-class, Ranger-themed) |
| S00261 | Forage Utility #1 | Forage adjective/noun matching |
| S00264 | Limitation Script ($RANGER section) | Canonical Ranger SAF mechanic |
| S00340 | (Forage SAF cost) | SAF decrements when forage harms wild things |
| S00350 | Forage Verb | Forage mechanic entry point |
| S00485 | Ranger Guild Guy (Kalika) | Crossing Ranger guild leader; guild speech; promotion milestones; snipe speech entry |
| S00486 | Ranger Guild Room (Crossing) | Crossing Ranger guildhall script |
| S00682 | TEASE verb | Companion teasing × Ranger SAF interaction |
| S00766 | $URBANCLASSA | Urban-vs-wilderness terrain classifier |
| S01034 | HOWL verb (Rakash) | Rakash howl × Ranger SAF × wolf companion interaction |
| S01155 | /SPELL verb | Profession-to-spell-tree dispatch; profession constants |
| S01265 | Forage Utility #2 | Canonical forage item table |
| S01555 | (Realm dispatch) | Magic realm constants; Ranger = realm 4 (Life) shared with Empath |
| S01918 | Spell Tree | Table 351 spell prerequisite tree |
| S02779 | Companion Control Script | Companion command surface (FIND/GET/SIT/STAND/etc.) |
| S02847 | (Multi-tier SAF verb) | SAF > -33 vs ≤ -33 threshold gate (verb not identified) |
| S03005 | (Companion noun assignment) | Raccoon companion type 101 confirmation |
| S03009 | Ranger Guild Room (Langenfirth) | Tolle as Langenfirth guild leader |
| S03366 | Wolf Scent (405001) | Animal Abilities Book |
| S03367 | See the Wind (405002) | Animal Abilities Book |
| S03368 | Spider Climb (405003) | Animal Abilities Book |
| S03369 | Eagle Vision (405004) | Animal Abilities Book |
| S03370 | Hands of Lirisa (406001) | Wilderness Survival Book |
| S03371 | Earth Meld (406002) | Wilderness Survival Book + canonical SAF spellcasting modifier reference |
| S03372 | Mesmerize (406003) | Wilderness Survival Book |
| S03373 | Compost (407001) | Wilderness Defense Book |
| S03374 | Swarm (407002) | Wilderness Defense Book |
| S03375 | Harawep's Bonds (407003) | Wilderness Defense Book |
| S03376 | Awaken Forest (407004) | Wilderness Defense Book |
| S04537 | (SAF percent display) | SAF expressed as percentage `(0 - np0:saf)` |
| S04627 | SKIN verb | Critter harvesting + Ranger SAF skin yield formula |
| S04972 | Blend (406004) | Wilderness Survival Book |
| S05344 | Cheetah Swiftness (405005) | Animal Abilities Book |
| S05642 | (Companion summon/call) | Companion type assignment (101 Raccoon, 102 Wolf) |
| S05692 | Water Purification (406006) | Wilderness Survival Book |
| S06438 | Measured Breaths (408003 - EMPATH not Ranger) | Disambiguation: 408xxx is NOT a Ranger book |
| S06440 | Breathe Water (406005) | Wilderness Survival Book |
| S06464 | Hobble (407005) | Wilderness Defense Book |
| S08104 | Caiman Swim (405007) | Animal Abilities Book |
| S08110 | Bear Strength (405006) | Animal Abilities Book |
| S10011 | Plague of Scavengers (407010) | Wilderness Defense Book |
| S10073 | Snipe verb | Canonical sniping mechanic (Ranger + Thief shared); guild1 bit gating |
| S10271 | Branch Break (407006) | Wilderness Defense Book |
| S10728 | $SNIPESPEECH | Multi-stage snipe teaching dialog (Tolle/Kalika via S11701) |
| S11242 | Senses of the Tiger (405009) | Animal Abilities Book |
| S11243 | Grizzly Claw (405008) | Animal Abilities Book |
| S11364 | $SNIPE_SKILL + $AWARD_KILL | Sniping skill check + killing-blow stealth XP |
| S11566 | Plague of Scavengers overflow | S10011 supplementary script |
| S11701 | Ranger Guildleader subscript | Shared $ASK routing for Kalika + Tolle |
| S11848 | (Companion-related) | Raccoon companion behavior |
| S12145 | Claws of the Cougar (STUB) | Unfinished canonical content; do NOT implement |
| S12148 | Wisdom of the Pack (405010) | Animal Abilities Book; self-cast only |
```

### Step 4: Update version history

At the end of the file, add:

```markdown
- 2026-05-15 (cont.) — Canon gaps closed via Claude-side GSL investigation
  transcribed into memory. 8 of 10 gaps fully verified, 2 partially
  (forage table partial enumeration; multi-tier SAF verb S02847 not
  fully identified). Canonical Reference Index appended for fast lookup
  by future Ranger dispatches. Layer error corrected: GSL access is
  Claude's responsibility, transcription is the local agent's job.
```

### Step 5: Verify memory file well-formedness

Re-open the file. Confirm:
- All 10 gap entries updated (8 marked verified, 2 partial)
- All cross-section updates landed (405xxx table Wisdom of the Pack target, 407xxx removed gap notation, Special Mechanics companion + sniping subsections rewritten, Magic realm verified, Other-city guilds enumerated, comprehensive SAF gate list)
- Canonical Reference Index present before version history
- Version history is at the end
- All markdown tables render
- File reads naturally end-to-end

# DRG-RANGER-CANON-AUDIT-02 — REVISED — Memory Transcription of Verified Findings

**Type:** Pure memory transcription dispatch. The canon investigation has ALREADY happened in Claude's conversation context (Claude has GSL corpus access; the local agent does not). This dispatch transcribes those verified findings into the Ranger canon memory note. No GSL access required by the executing agent.
**Output:** Updated `/memories/repo/repo-memory-ranger-canon-mechanic.md` with 8 of 10 gaps fully closed, 2 partially closed, plus new Canonical Reference Index section. No code, no tests.
**Estimated touch:** 0 lines of code. ~15-20 min agent time. One memory file update.
**Sequencing:** Replaces the prior DRG-RANGER-CANON-AUDIT-02 dispatch that halted on missing GSL access. Prerequisites: prior dispatch halted with no edits made (confirmed in transcript). Next: DRG-RANGER-RECONCILE-PROFESSION-001 from complete canonical authority.

---

## Context: Why this dispatch is revised

The original DRG-RANGER-CANON-AUDIT-02 instructed the local agent to "do a GSL deep-dive." That was a mistake. The local agent has no access to the GSL corpus at `/tmp/origin_verify/origin/` — that path exists only in Claude's conversation sandbox, not on Gary's local filesystem.

The agent correctly halted on the GSL-access gate without making edits. This dispatch fixes the layer error: **Claude (with GSL access) does the canon investigation; the local agent transcribes verified findings into memory.** Same pattern that worked for every canonical claim in the Cleric and Empath programs.

The findings below were verified by direct GSL inspection in Claude's conversation context during this session. Each cites the source S-script for traceability. The agent's job is to write these into the memory note via single-section-rewrites per the established memory hygiene pattern.

---

## Step 0 — Audit prep

Time-boxed to 5 minutes. **No memory edits during Step 0.**

### Step 0a: Prereqs

- DRG-RANGER-AUDIT closed as Classification C (CHANGELOG check)
- Prior DRG-RANGER-CANON-AUDIT-02 attempt halted with NO edits made (verify by re-reading the Ranger canon memory note; the "Known Canon Gaps" section should still have all 10 gaps unchanged)
- `/memories/repo/repo-memory-ranger-canon-mechanic.md` exists with 10 documented gaps in "Known Canon Gaps" section

### Step 0b: Confirm clean slate

Re-read the Ranger canon memory note's "Known Canon Gaps" section. Confirm:
- All 10 gaps are present unchanged
- No partial transcription happened from the prior failed attempt

If anything's been modified, surface for review before proceeding.

---

## Frozen design decisions

### Decision 1: Pure memory transcription, zero investigation

The agent does NOT need to verify the GSL findings below. They were verified by Claude in this session against the GSL corpus. The agent's job is to transcribe them faithfully into the memory note.

If the agent doubts a finding, surface it — don't try to verify it independently (you can't; you don't have GSL access).

### Decision 2: Single-section-rewrites per memory hygiene discipline

Each gap entry in the "Known Canon Gaps" section gets rewritten in place to reflect the new finding. Sections elsewhere in the note that reference the gap also get rewritten where appropriate (e.g., the 405xxx spell table now includes Claws of the Cougar as "stub spell, do not implement").

This is the memory hygiene "single-section-rewrite allowed when content is explicitly superseded" pattern, applied to multiple sections within the same dispatch.

### Decision 3: Canonical Reference Index gets appended

Per the original DRG-RANGER-CANON-AUDIT-02 plan, append a Canonical Reference Index section at the end (before version history) consolidating S-script citations. The list of citations is provided below.

### Decision 4: Version history entry

Add a single new entry to the version history at the file's end, dated 2026-05-15, noting that canon gaps were closed via Claude-side GSL investigation transcribed into memory.

### Decision 5: Findings cite source scripts

Every closed gap entry cites the source S-script(s). Pattern matches the existing Ranger memory note: `(S00264)`, `(S00485 lines 230-250)`, etc. Citations make the canon traceable.

---

## Step-by-step execution

### Step 1: Step 0 verification

Per Step 0a-b. Output: confirmation prior dispatch halted clean.

### Step 2: Transcribe verified findings — Gap-by-gap rewrites

**Gap 1 — Wisdom of the Pack (405010) targeting: CLOSED**

Rewrite the gap entry to:

```markdown
1. **Wisdom of the Pack (405010) targeting:** VERIFIED self-cast only.
   Per S12148: `$OTHER` block sets `$BREAK to 1` (disallow casting at
   others); `$SELF` block clears `$BREAK` (allow self-cast); `$OBJECT`
   block sets `$BREAK to 1` (disallow inanimate targets); `$OFFENSE`
   block clears `$BREAK` (non-offensive). Standard self-cast Ranger
   buff. (S12148 lines 104-130)
```

Also update the 405xxx Animal Abilities Book table — Wisdom of the Pack target column changes from `self (assumed)` to `self`.

**Gap 2 — Spells 407007/407008/407009 sequence: CLOSED (CONFIRMED ABSENT)**

Rewrite the gap entry to:

```markdown
2. **Spells 407007/407008/407009:** VERIFIED absent from GSL corpus.
   No script files contain references to these spell IDs. Wilderness
   Defense Book sequence: 407001 Compost, 407002 Swarm, 407003 Harawep's
   Bonds, 407004 Awaken Forest, 407005 Hobble, 407006 Branch Break,
   gap (407007-009), 407010 Plague of Scavengers. The gap represents
   cut content or unfinished design that didn't ship in 2004 canon.
   DireEngine implementation should match: 7 spells in Wilderness
   Defense Book, IDs 407001-407006 and 407010.
```

Also remove "(gap at 407007-009)" from the 407xxx table heading; the gap is now confirmed canonical.

**Gap 3 — Claws of the Cougar (S12145) spell ID: CLOSED (STUB)**

Rewrite the gap entry to:

```markdown
3. **Claws of the Cougar (S12145) spell ID:** VERIFIED stub script.
   S12145 (Jason Collette / GM Paklin, 09/23/03) contains ONLY the
   `$NAME` block setting `t0 = "Claws of the Cougar"`. No CASTMOD, no
   spell ID, no effect logic, no targeting blocks. The script body
   terminates at line 34 with a file separator character. This was
   in-development canonical content that never shipped. **DireEngine
   should NOT implement Claws of the Cougar.** The Animal Abilities
   Book contains exactly 10 canonical spells (405001-405010).
```

Also update Special Mechanics / 405xxx section: remove the "Candidate additional Ranger spell: Claws of the Cougar" note from the canon memory (it's not canonical).

**Gap 4 — Full companion system mechanics: CLOSED**

Replace the brief "Animal Companion" section in Special Mechanics with:

```markdown
### Animal Companion (`np0:companion`)

**Canonical companion types** (only two exist in GSL corpus):
- **101 = Raccoon** (S03005 sets `nc1:noun to "raccoon"`)
- **102 = Wolf** (S05642 sets `nc1:noun to "wolf"`)

No other canonical companion types exist. Bear, hawk, cat, etc. are
NOT canonical in 2004 GSL.

**Control script:** S02779 — companion command surface includes FIND,
GET, SIT, STAND, RETURN, FOLLOW, NOCOMPOST plus standard familiar verbs.

**Call/Summon script:** S05642 — handles initial companion creation
and resummon. Routes companion type to noun assignment.

**Lifecycle:** Companion state persists on `np0:companion` field (and
`np0:compborn` for birth time per S00682 TEASE reference). Logout
persistence canonical; details in S02779.

**SAF interaction (canonical, verified Gap 8):** Several wilderness
verbs check both companion presence AND Ranger SAF — wolf companion
+ SAF < -25 in wilderness enables enhanced howl interaction (S01034),
tease-companion interaction (S00682), and companion-related skill
bonuses elsewhere.
```

**Gap 5 — Level milestones beyond 1-2 and 4-5: CLOSED**

Replace the partial "Ranger Guild Promotion Milestones" section with:

```markdown
### Ranger Guild Promotion Milestones (canonical from S00485 $PROMOTE)

- **Every level 1-5 promotion**: `200 * level` XP awarded in Primary
  Magic (skill 44) via S00157 utility. (S00485 lines 220-230)
- **Level 2 promotion**: Kalika delivers the wilderness affinity speech
  ("an almost innate survival in the wilderness... Be wary of the
  seductive ease of the city"). First explicit canonical introduction
  of Ranger SAF concept to the player.
- **Level 4 promotion**: Extra 400 XP in Primary Magic (Base Magical
  Ability bonus). (S00485 lines 247-250)
- **Levels 6+**: NO fixed Primary Magic XP grant on promotion (the
  `if (np0:level < 6)` gate). Higher-level promotion grants depend on
  spell slot eligibility checks only.
- **Spell slots**: Granted via S01155 `$GIVE_NEW_SLOTS` central utility
  (cross-class). Eligibility check on every promotion; awarded when
  `np0:newspells` increases. (S00485 lines 255-265)
- **Medium-level milestone**: At `no1:ddata1` (configurable per guild
  prop, NOT hardcoded level): "greater control over training" speech.
  Standard DR pattern — milestone levels stored in the guild's prop
  varfields, not the script.
- **High-level milestone**: At `no1:ddata2`: "ultimate control over
  training" speech.
- **Highest-level milestone**: At `no1:ddata3` (declared in $PROMOTE
  header comment; specific behavior not in visible script body).

**Note on level cap:** S00485 does not document a canonical Ranger
level cap; the `no1:ddata4` field is described as "end of highest
level??" suggesting it MAY define a cap but the script body uses it
ambiguously.
```

**Gap 6 — Forage table contents (S01265): PARTIALLY CLOSED**

Rewrite gap entry to:

```markdown
6. **Forage table contents (S01265):** PARTIALLY VERIFIED. S01265 is
   the canonical "Forage Utility #2" containing per-item profile data
   for forageable items. 594 lines total. Table structure:
   - `t2` set to noun (e.g., "grass", "tuft of", etc.) by caller
   - `v1`/`v2` returned: vegetation types where item can be found
     (decimal-packed format: e.g., `v1 = 130107` means types 1, 7, 13)
   - `a1`/`a2` returned: difficulty percentages per vegetation type
     (e.g., `a1 = 207533` means 150% likelihood in type 1, 66% in 7,
     40% in 13)
   - `a4` returned: maximum exp award for foraging that item
   - `a5` returned: percentage chance to find in other terrain types
   - `b1`-`bN` returned: item profile (weight, volume, value) for
     creation
   - Hidden-mode foraging (`no0:hidden`) routes to a different code
     path using table 538 — likely the "secret/rare" forage path
   - Terrain control via `a6`/`a7` (main/secondary vegetation), `a0`
     (lushness %), `a8` (soil), `a9` (terrain type)

   **Item enumeration partial:** Sample items confirmed: tuft of grass,
   rocks, hulnik grass, muljin, sufil sap, flowers (blue/red variants).
   Full item list spans hundreds of entries; not fully enumerated this
   session.

   **DireEngine implementation note:** The exact item table is large
   enough that a faithful canonical port would be its own focused
   dispatch. A minimal canonical forage with ~10 representative items
   per major terrain type satisfies the canonical pattern; full table
   port is optional follow-up.
```

**Gap 7 — Sniping mechanic details: CLOSED**

Replace the brief "Sniping" subsection with:

```markdown
### Sniping (canonical from S10073 + S10728 + S11364)

**Shared mechanic:** Both Ranger (profession=2) AND Thief (profession=6)
can snipe. Underlying ranged-attack chain: S10073 (snipe verb) calls
S00078 (FIRE verb) for the actual attack resolution.

**Ranger gate (`np0:guild1` varfield):**
- Bit 0 = 1: Knows how to snipe
- Bit 1 = 1: Has abused snipe; ability revoked
- Both bits 0 in initial state — Rangers don't auto-learn snipe at any
  level

**How a Ranger learns snipe:** Via guild leader speech interaction.
S10728 contains the canonical SNIPESPEECH multi-stage teaching dialog
(originally with Tolle at Langenfirth per script text, but routed
through S11701 shared Ranger Guildleader subscript so Kalika at the
Crossing teaches it too). Player asks guild leader about "snipe" or
"sniping"; speech delivered in stages via timed effects (`code 10728000`,
6-second interval per stage). At conclusion, `np0:guild1` bit 0 set.

**Snipe requirements:**
- Must be hidden or invisible (`np0:hidden || np0:invisible`)
- Must have bow loaded (routed through standard load mechanic, S00076)
- Must have ranged weapon attached (`no1:profile` check excludes
  non-ranged weapons via 1599-1610 range exclusion)

**Skill checks (S11364 $SNIPE_SKILL):**
- Stealth skill (skill 61 hiding) for award + difficulty
- Aim, perception, and target-awareness factor into hit chance
- Killing blow on a hidden target awards bonus stealth XP via $AWARD_KILL

**Anti-grief gating (S10073 lines 200+):**
- GM log when sniper is 2x target's level (`np0:level > np1:level*2`)
- Murder tracker integration for player-vs-player snipes
- Guild leader can revoke ability via guild1 bit 1

**Dual-arrow loading interaction (S00076):** Rangers can pre-load two
arrows and fire both via the snipe sequence (canonical Ranger +
Barbarian dual-load combined with snipe).
```

**Gap 8 — Complete SAF gate audit: CLOSED**

Replace the "What Ranger SAF Gates" subsection with:

```markdown
### What Ranger SAF Gates (comprehensive canonical enumeration)

Ranger SAF gates the entire Ranger wilderness identity. Every
wilderness-themed verb interacts with SAF. Verified gates:

1. **Spellcasting difficulty (S03371 Earth Meld reference pattern):**
   Ranger + SAF == -100: `b9 -= 2` (bonus). Non-Ranger casting Ranger
   spell: `b9 += 2` (penalty). This is the canonical reference; other
   Ranger spells likely apply similar logic.

2. **Bow loading (S00076 LOAD verb):**
   - Ranger + SAF < -50: `a1 *= 11/10` (+10% bonus to load skill)
   - Ranger + SAF > 75: `a1 *= 9/10` (-10% penalty)

3. **Forage harm (S00340):** Some forage actions COST SAF
   (`np0:saf -= 1`) when they harm wild things — Ranger has explicit
   consequence for breaking wilderness, mirroring Empath consequence
   for harming sentients but much smaller magnitude.

4. **Guild commitment (S00486 Crossing + S03009 Langenfirth):** SAF
   `clear`-ed to 0 on guild join. Fresh start for new Rangers.

5. **Companion teasing (S00682 TEASE):** Wilderness (`urbanclass < 8`)
   + SAF < -25: special companion interaction enabled.

6. **Howl × wolf companion (S01034):**
   - Wilderness + SAF < -25 + wolf companion: enhanced howl
   - SAF > -1 attempting stealth howl: "trapped milk cow" failure

7. **Multi-tier verb (S02847):** SAF > -33 triggers one path, otherwise
   another. (Script body not fully read this session — likely TRACK,
   SCOUT, or similar Ranger-themed verb.)

8. **SAF percent display (S04537):** SAF expressed as percentage via
   `(0 - np0:saf)` — UI representation of how "wild" the Ranger is.

9. **Skin yield (S04627 SKIN):** Ranger SKIN bonus formula:
   `v7 = 15 + ((np0:level/4) * ((100 - (np0:saf + 100)) / 100))`
   Better (more negative) SAF = better skinning result.

**Architectural implication:** A canonical RangerSafService needs to
support these gate types:
- Spellcasting modifier (binary -100 check OR graduated)
- Skill difficulty modifier (SAF < -50, SAF > 75 thresholds)
- Bonus multiplier on Ranger-themed actions (SKIN, FORAGE)
- Boolean gates (`< -25` enables behavior, `> -1` disables)
- SAF mutation by actions (forage harm decrements SAF)
- Display percentage representation
```

**Gap 9 — Magic realm verification: CLOSED**

Rewrite "Magic realm" entry in Profession Identity section:

```markdown
- **Magic realm:** **Life realm (realm 4)** — VERIFIED. Per S01555:
  `is 4 ! life: rangers & empaths` with check
  `if ((NP0:profession=2)|(NP0:profession=4))`. Ranger shares realm 4
  with Empath. Full realm constants:
  - Realm 1 = Elemental (Warmage)
  - Realm 2 = Holy (Paladin, Cleric)
  - Realm 4 = Life (Ranger, Empath)
  - (Realm 3 = mental or arcane; not directly relevant to Ranger work)
```

**Gap 10 — Other-city guild leaders: CLOSED (CANONICAL CORPUS HAS ONLY TWO)**

Rewrite "Other canonical guild leaders by city":

```markdown
- **Other canonical guild leaders by city:** ONLY TWO canonical Ranger
  guildhalls exist in the 2004 GSL corpus:
  - **Kalika** — The Crossing (S00485 NPC + S00486 guild room script).
    Elven woman, ash longbow, falchion. Verbose canonical philosophy
    speech in $GUILD section.
  - **Tolle** — The Langenfirth (S03009 guild room script). Detail
    sparser than Kalika but uses parallel join/promote/teach surface.
  
  No Ranger guildhalls in Riverhaven, Shard, Aesry, Hibarnhvidar,
  Theren, Ratha, or other DR cities exist in the 2004 corpus. Those
  may exist in modern DR canon but not in our canonical reference.
  
- **DireEngine reference:** Kalika at the Crossing matches the Empath
  Merla precedent. Tolle at the Langenfirth is canonical-valid as a
  second guild for a non-Crossing city if/when DireEngine expands
  beyond the Crossing.
```

### Step 3: Append Canonical Reference Index

Before version history, append:

```markdown
## Canonical Reference Index

Quick lookup of all S-script citations used in this memory note.
Sorted by S-number.

| Script | Subject | Used For |
|--------|---------|----------|
| S00076 | LOAD verb | Dual-arrow loading (Ranger + Barbarian); SAF skill modifier |
| S00078 | FIRE verb | Underlying ranged-attack mechanic for snipe |
| S00157 | Skill XP utility | Primary Magic XP grants per promotion |
| S00256 | CARVE verb | Critter harvesting (cross-class, Ranger-themed) |
| S00261 | Forage Utility #1 | Forage adjective/noun matching |
| S00264 | Limitation Script ($RANGER section) | Canonical Ranger SAF mechanic |
| S00340 | (Forage SAF cost) | SAF decrements when forage harms wild things |
| S00350 | Forage Verb | Forage mechanic entry point |
| S00485 | Ranger Guild Guy (Kalika) | Crossing Ranger guild leader; guild speech; promotion milestones; snipe speech entry |
| S00486 | Ranger Guild Room (Crossing) | Crossing Ranger guildhall script |
| S00682 | TEASE verb | Companion teasing × Ranger SAF interaction |
| S00766 | $URBANCLASSA | Urban-vs-wilderness terrain classifier |
| S01034 | HOWL verb (Rakash) | Rakash howl × Ranger SAF × wolf companion interaction |
| S01155 | /SPELL verb | Profession-to-spell-tree dispatch; profession constants |
| S01265 | Forage Utility #2 | Canonical forage item table |
| S01555 | (Realm dispatch) | Magic realm constants; Ranger = realm 4 (Life) shared with Empath |
| S01918 | Spell Tree | Table 351 spell prerequisite tree |
| S02779 | Companion Control Script | Companion command surface (FIND/GET/SIT/STAND/etc.) |
| S02847 | (Multi-tier SAF verb) | SAF > -33 vs ≤ -33 threshold gate (verb not identified) |
| S03005 | (Companion noun assignment) | Raccoon companion type 101 confirmation |
| S03009 | Ranger Guild Room (Langenfirth) | Tolle as Langenfirth guild leader |
| S03366 | Wolf Scent (405001) | Animal Abilities Book |
| S03367 | See the Wind (405002) | Animal Abilities Book |
| S03368 | Spider Climb (405003) | Animal Abilities Book |
| S03369 | Eagle Vision (405004) | Animal Abilities Book |
| S03370 | Hands of Lirisa (406001) | Wilderness Survival Book |
| S03371 | Earth Meld (406002) | Wilderness Survival Book + canonical SAF spellcasting modifier reference |
| S03372 | Mesmerize (406003) | Wilderness Survival Book |
| S03373 | Compost (407001) | Wilderness Defense Book |
| S03374 | Swarm (407002) | Wilderness Defense Book |
| S03375 | Harawep's Bonds (407003) | Wilderness Defense Book |
| S03376 | Awaken Forest (407004) | Wilderness Defense Book |
| S04537 | (SAF percent display) | SAF expressed as percentage `(0 - np0:saf)` |
| S04627 | SKIN verb | Critter harvesting + Ranger SAF skin yield formula |
| S04972 | Blend (406004) | Wilderness Survival Book |
| S05344 | Cheetah Swiftness (405005) | Animal Abilities Book |
| S05642 | (Companion summon/call) | Companion type assignment (101 Raccoon, 102 Wolf) |
| S05692 | Water Purification (406006) | Wilderness Survival Book |
| S06438 | Measured Breaths (408003 - EMPATH not Ranger) | Disambiguation: 408xxx is NOT a Ranger book |
| S06440 | Breathe Water (406005) | Wilderness Survival Book |
| S06464 | Hobble (407005) | Wilderness Defense Book |
| S08104 | Caiman Swim (405007) | Animal Abilities Book |
| S08110 | Bear Strength (405006) | Animal Abilities Book |
| S10011 | Plague of Scavengers (407010) | Wilderness Defense Book |
| S10073 | Snipe verb | Canonical sniping mechanic (Ranger + Thief shared); guild1 bit gating |
| S10271 | Branch Break (407006) | Wilderness Defense Book |
| S10728 | $SNIPESPEECH | Multi-stage snipe teaching dialog (Tolle/Kalika via S11701) |
| S11242 | Senses of the Tiger (405009) | Animal Abilities Book |
| S11243 | Grizzly Claw (405008) | Animal Abilities Book |
| S11364 | $SNIPE_SKILL + $AWARD_KILL | Sniping skill check + killing-blow stealth XP |
| S11566 | Plague of Scavengers overflow | S10011 supplementary script |
| S11701 | Ranger Guildleader subscript | Shared $ASK routing for Kalika + Tolle |
| S11848 | (Companion-related) | Raccoon companion behavior |
| S12145 | Claws of the Cougar (STUB) | Unfinished canonical content; do NOT implement |
| S12148 | Wisdom of the Pack (405010) | Animal Abilities Book; self-cast only |
```

### Step 4: Update version history

At the end of the file, add:

```markdown
- 2026-05-15 (cont.) — Canon gaps closed via Claude-side GSL investigation
  transcribed into memory. 8 of 10 gaps fully verified, 2 partially
  (forage table partial enumeration; multi-tier SAF verb S02847 not
  fully identified). Canonical Reference Index appended for fast lookup
  by future Ranger dispatches. Layer error corrected: GSL access is
  Claude's responsibility, transcription is the local agent's job.
```

### Step 5: Verify memory file well-formedness

Re-open the file. Confirm:
- All 10 gap entries updated (8 marked verified, 2 partial)
- All cross-section updates landed (405xxx table Wisdom of the Pack target, 407xxx removed gap notation, Special Mechanics companion + sniping subsections rewritten, Magic realm verified, Other-city guilds enumerated, comprehensive SAF gate list)
- Canonical Reference Index present before version history
- Version history is at the end
- All markdown tables render
- File reads naturally end-to-end

### Step 6: Update CHANGELOG

```markdown
## DRG-RANGER-CANON-AUDIT-02 (revised) — Memory transcription of verified canon

Pure memory dispatch. No code changed, no tests ran. GSL canon
investigation was completed by Claude in conversation context (Claude
has GSL corpus access; local agent does not — prior dispatch correctly
halted on this gap). This dispatch transcribed Claude's verified
findings into the Ranger canon memory note.

Results: 8 of 10 documented canon gaps fully verified, 2 partially
verified. New Canonical Reference Index section appended consolidating
all 50+ S-script citations for fast lookup by subsequent Ranger
dispatches.

Key resolutions:
- Magic realm: Life (4), shared with Empath (S01555)
- Companion types: only 101 Raccoon + 102 Wolf canonical (no others)
- Sniping: Ranger + Thief shared mechanic; guild1 bit gating; learned
  via guild leader speech (S10728); requires hidden state (S10073)
- 407007-009: confirmed absent from canon (cut content)
- Claws of the Cougar: STUB script, do NOT implement
- Wisdom of the Pack: self-cast only (S12148)
- Level milestones: Primary Magic XP every promotion 1-5, extra at L4,
  spell slots via S01155 central utility, medium/high/highest milestones
  configurable per guild prop (no hardcoded levels)
- Comprehensive SAF gate audit: 9 distinct gate types catalogued
  including spellcasting, skill modifiers, action bonuses, behavioral
  thresholds, SAF mutation actions, and display representation

Partially verified:
- Forage table contents: structure documented, full item list deferred
  to future focused dispatch
- S02847 multi-tier SAF verb: threshold at SAF > -33 documented; verb
  not identified

Sets up DRG-RANGER-RECONCILE-PROFESSION-001 to start with complete
canonical authority cached.
```

### Step 7: Dispatch report

Write `/mnt/user-data/outputs/DRG-RANGER-CANON-AUDIT-02-report.md`:

1. Note that this dispatch revises the prior halted attempt; layer error explained
2. Gap-by-gap result table (8 verified, 2 partial)
3. Key new canonical findings
4. Canonical Reference Index summary (~50 scripts cited)
5. Recommended next dispatch: DRG-RANGER-RECONCILE-PROFESSION-001

---

## Halt conditions

1. DRG-RANGER-AUDIT not closed as Classification C — HALT
2. Prior DRG-RANGER-CANON-AUDIT-02 attempt didn't actually halt clean (gaps section has been modified) — HALT for review
3. Any pull toward "let me try to verify these findings against GSL myself" — HALT (you don't have GSL access; trust the findings or surface doubt)
4. Any pull toward code edits — HALT (Decision 1)
5. Markdown structure broken after edits — HALT, restore from prior state
6. Dispatch time exceeds 30 minutes — HALT (pure transcription should be fast)

---

## What this dispatch is NOT

- Not re-doing GSL investigation (Claude already did it; agent transcribes)
- Not modifying any code, tests, or world content
- Not closing newly-discovered gaps
- Not starting reconciliation work

---

## After this dispatch

**Day 1 truly closes.** 28 dispatches total. Cleric + Empath complete, Ranger canonical authority complete (8/10 gaps verified, 2 partial documented), 50+ S-script citations indexed for fast lookup, memory layer durable.

**Saturday morning opens with DRG-RANGER-RECONCILE-PROFESSION-001.** The foundational architectural dispatch — changes Ranger primary axis from survival to Primary Magic per canon. Highest-risk Ranger dispatch because it touches existing test coverage. Halt conditions aggressive.

Ship it.

- Completed DRG-RANGER-AUDIT as a read-only architectural audit against the new Ranger canon authority note. Step 0 prerequisites were verified, the documented preservation batch reran green at `302 passed, 107 subtests passed`, and the audit classified current Ranger state as `C`, requiring a halt before implementation. The core finding is that DireEngine already ships a substantial Ranger implementation that conflicts with the cached canonical authority: `world/professions/professions.py` defines Ranger with `survival` as the primary axis, `domain/spells/spell_definitions.py` lists Ranger as a spellcasting profession but contains no canonical `405xxx`/`406xxx`/`407xxx` spell rows, `server/conf/at_server_startstop.py` bootstraps a multi-room `Ranger Guild` in The Landing with guildmaster `Elarion` plus mentor NPCs instead of canonical Crossing leader Kalika, and `typeclasses/characters.py` / `world/systems/ranger/` already implement a bespoke wilderness-bond / nature-focus / companion / beseech / snipe runtime that does not match the canonical Ranger SAF model captured on Day 1. The audit report was written to `/mnt/user-data/outputs/DRG-RANGER-AUDIT-report.md`, brief current-state findings were appended to `/memories/repo/repo-memory-ranger-canon-mechanic.md`, and the dispatch closed as a halt-for-scope-decision result rather than continuing into code changes.

- Completed DRG-RANGER-CANON-AUDIT as the Day 1 final Ranger canon-capture dispatch. No code changed. New repo memory file `/memories/repo/repo-memory-ranger-canon-mechanic.md` now holds the verified canonical Ranger authority from the prior GSL deep-dive: profession `2`, Crossing guild leader Kalika as the primary DireEngine reference, Ranger SAF as environmental affinity rather than Empath-style consequence accumulation with canonical range `[-100, +150]`, three verified spellbooks (`405xxx` Animal Abilities with 10 spells, `406xxx` Wilderness Survival with 6 spells, `407xxx` Wilderness Defense with 7 verified entries including the `407007-009` gap), the current special-mechanics inventory (companion, forage, skin/carve, snipe, dual-arrow loading, Rakash howl, partial promotion milestones), Kalika's canonical guild philosophy, and 10 explicit canon gaps for follow-up Ranger audit work. The new note cross-references the existing canon-authority, operational-discipline, preservation-batch, smoke-fixtures, and Empath canon-memory notes so Day 2 architectural work can start from durable repo authority instead of transcript reconstruction. Day 1 now closes with 26 dispatches shipped, two complete profession programs, durable memory-layer rules, and Ranger canon cached for `DRG-RANGER-AUDIT`.

- Completed DRG-MEMORY-HYGIENE-001 as the Day 1 memory-layer closeout dispatch. No code changed. Durable operational rules that had been scattered across dispatch prose, changelog notes, and transcript-only context are now captured in repo memory instead: `/memories/repo/preservation-batch.md` now holds the exact documented Cleric + Empath preservation batch command plus the pass-count anchors through `298 passed, 107 subtests passed`; `/memories/repo/operational-discipline.md` now holds the audit-first Step 0 rule, A/B/C classification meanings, bounded-budget and halt-condition discipline, scoped validation, inline citation expectations, provenance taxonomy, and hotfix discipline; `/memories/repo/smoke-fixtures.md` now records the `depart` -> `depart confirm` recovery pattern, the `/play` websocket transport caveat, the direct Evennia object-query fallback, the Evennia `py` generator-expression contamination warning, and the rule that smoke-fixture circle drift is normal when it is explicitly documented for verification needs; and `/memories/repo/repo-memory-empath-canon-mechanic.md` now marks both DRG-EMPATH-PROGRESSION-001 and DRG-EMPATH-SAF-001 as shipped rather than future work, adds a final-status summary for the completed Empath program, and removes the stale implication that Day 2 might still begin with those follow-up slices. Memory files were manually re-opened and checked for well-formed Markdown after edit. Ranger Day 2 can now start from durable repo authority rather than transcript reconstruction.

- Completed DRG-EMPATH-SAF-001 as the canonical Empath SAF subsystem dispatch. Step 0 classified the seam as `B`: the existing combat runtime already exposed a bounded post-resolution consequence hook in `engine/services/combat_service.py`, the existing empath tick loop in `typeclasses/characters.py` already provided a natural decay seam, and the remaining missing work was the moral-state implementation rather than a broad infrastructure gap. `engine/services/empath_saf_service.py` now owns the bounded SAF duration/burden model, timed shock/prone consequences, permashock threshold, and `take shock` rescue path; `engine/services/combat_service.py` now applies SAF from the real attack outcome instead of the older pre-attack placeholder; `engine/services/wound_transfer_service.py` now blocks ordinary transfer while SAF is active and routes `take shock` through the rescue seam; `engine/services/spell_effect_service.py` now applies the real Gift of Life SAF gate instead of the older deferred marker; and `typeclasses/characters.py` now persists SAF state, honors timed stun through `db.stunned_until`, and decays SAF on the existing empath tick. Focused SAF coverage validated green at `92 passed`, and the preserved Empath-adjacent runtime/service/presenter/guild slice validated green at `234 passed, 107 subtests passed`. Live verification on the active `SmokeEmpathLive` runtime used direct object-state proof around the real seams: tier-0 aggression set `duration=10800` and `burden=3` with stun applied, wound transfer then failed with `You feel a sudden spiritual shock as the link shatters.`, Gift of Life failed with `You have lost your sensitivity by harming others, so Gift of Life cannot take hold.`, and a temporary permashocked `EmpathAuditPatient` was cleared by `take shock` while the rescuer inherited SAF burden. Bounded caveat preserved intentionally: the murder-tier self-wound mirror remains deferred rather than widening this slice beyond the requested scope.

- Completed DRG-EMPATH-PROGRESSION-001 as the canonical Empath XP-from-healing progression dispatch. Step 0 classified the seam as `A`: `engine/services/skill_service.py::SkillService.award_xp(...)` already provides the live skill-XP entrypoint, `primary_magic`, `perception`, and `empathy` already exist as tracked skills, `typeclasses/characters.py` already exposes progression ranks through `get_progression_skill_rank(...)` and circle/level through `get_circle()`, and `engine/services/wound_transfer_service.py::transfer(...)` already owned the success seam with patient and wound-type context. The bounded repair now awards canonical S00524 progression XP directly in `WoundTransferService.transfer(...)` with inline `gsl_2004` provenance comments: `primary_magic = (amount * 80 / 100) + 1`, `perception = (amount * 20 / 100) + 1`, and canonical Transference routed through DireEngine Empathy using `clamp(rank / level, 1, 8)` plus the documented poison/disease bonuses. The same service seam now applies the canonical caster fatigue cost `amount / 3`, records the actual transferred amount from live wound deltas, and passes a bounded `canonical_progression` learning action into `take_empath_wound(...)` so the older generic Empathy field-learning path no longer double-awards XP during canonical transfers. The canonical class-internal limitation is now preserved at the service seam: when the patient is another Empath, transfer still succeeds and fatigue still drops, but the progression pools stay unchanged. Focused transfer coverage validated green at `12 passed`, and the exact required preservation batch reran green at `298 passed, 107 subtests passed`. Live verification after Evennia reload used the active `SmokeEmpathLive` fixture and authoritative live-object queries around the real wound-transfer runtime: a commoner-patient vitality transfer moved `9` points, reduced caster fatigue from `12` to `9`, dropped the patient's vitality from `10` to `1`, and increased the progression pools by the expected canonical amounts (`primary_magic` pool `+8`, `perception` pool `+2`, `empathy` pool `+44.343999...` from the existing live rank/level ratio). A bounded follow-up live gate check with the patient's profession temporarily set to `empath` confirmed the transfer still moved `4` vitality and fatigue still dropped from `12` to `11`, while the three progression pools stayed flat across the transfer itself. Operational caveat worth preserving: the attached `/play` browser tab reconnected cleanly and accepted forced UI actions, but stateful command transport remained too noisy to trust for proof capture, so the final live assertions were taken from direct live-object state queries around the same `SmokeEmpathLive` runtime after reload. One deferred Empath subsystem remains: `DRG-EMPATH-SAF-001`.

- Completed DRG-EMPATH-09 as the final Empath program closeout dispatch. The exact required preservation batch stayed green at `294 passed, 107 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` completed the end-to-end cast matrix for all 13 canonical Empath spells: External Wound Healing, Internal Wound Healing, Vitality Healing, Heal Wounds, Heal Scars, Heal, Flush Poisons, Cure Disease, Refresh, Raise Power, Gift of Life, Innocence, and Zone of Protection all prepared and cast successfully with state-query proof on the intended runtime seam. Self-only spells preserved their guardrail live with `You can only cast that spell on yourself.`, Refresh again proved both self and cross-target behavior on `EmpathAuditPatient`, Innocence again showed the bounded hybrid behavior live by releasing `SmokeInnocenceWolf` while driving undead backfire onto `SmokeInnocenceSkeleton`, and Zone of Protection again persisted the expected caster ward state with `absorbs_physical=False`. The EMPATH-08 off-class regression guard also held unchanged with `Guildleader Merla says, "I do not teach a spell called 'bless'."` Policy revisit for DRG-CANON-POLICY-001 stays `B`: hybrid-leaning-grandfather succeeded for Empath with caveats because the shipped program now has 13 canonical `gsl_2004` spells across four sub-books, one explicit `hybrid_design` roster exception (`empath_heal`), five named inline bounded adaptations instead of silent rewrites, zero surfaced undocumented substitutions, and two named deferred dispatches (`DRG-EMPATH-SAF-001`, `DRG-EMPATH-PROGRESSION-001`) for the remaining canon-heavy subsystems. Local LLM migration readiness is `ready with caveats` for the planned post-window test: the canonical authority now lives in repo memory, the dispatch breadcrumbs and changelog are sufficient to continue deferred Empath work without replaying the whole program, and the only operational nuance worth carrying forward is the live smoke recovery pattern around `DEPART CONFIRM`, temporary hostile cleanup, and grave noise on `SmokeEmpathLive`.

- Completed DRG-EMPATH-08 as the Empath guild progression audit-and-close dispatch. Classification: `B`, but only for bounded presentation work. Step 0 verified the hard progression seam already worked: the exact documented preservation batch stayed green at `294 passed, 107 subtests passed`, Merla's teaching allowlist in `typeclasses/npcs.py` is registry-derived from the current Empath-only rows rather than a hand-maintained list, the live Empath roster is the expected 15 teachable rows (13 canonical spells plus `regenerate` and hybrid `empath_heal`), and the current circle/apprentice tiers are canon-adjacent with no substantial gating mismatch that would justify widening the dispatch. The one real audit gap was the `spells` presentation surface in `commands/cmd_spellbook.py`, which was still flat and left the hybrid `empath_heal` row visually ambiguous beside canonical `heal`. The bounded EMPATH-08 fix now groups both permanent and apprentice spells by sub-book and marks hybrid rows explicitly as `[Hybrid]`; focused spell-command coverage validated green at `6 passed`, and the exact required preservation batch reran green unchanged at `294 passed, 107 subtests passed`. Live `/play` smoke on `SmokeEmpathLive` after in-band reload plus dead-state recovery via `DEPART CONFIRM` confirmed the new grouped spellbook output (`Healing`, `Cleansing`, `Vitality`, `Protection`) with `Heal [Hybrid]` clearly distinguished, preserved the off-class boundary with `Guildleader Merla says, "I do not teach a spell called 'bless'."`, resolved all 13 canonical Empath teach commands cleanly as `You already know that spell.`, and opportunistically closed EMPATH-07's remaining live proof by showing bare `Innocence` cast successfully with `A quiet stillness settles around you, signaling to nearby threats that you are no danger.`

- Completed DRG-EMPATH-07 as the canonical Empath Protection Book dispatch. Step 0 classified the runtime seam as `B`: existing NPC target/threat/disengage state was sufficient for a real bounded `Innocence` implementation, while `Zone of Protection` had to ride the already-existing room-account group helper rather than a missing canonical follow/party model. `domain/spells/spell_definitions.py` now ships `innocence` (404002) and `zone_of_protection` (404003) as `gsl_2004` Protection Book rows with the verified CASTMOD anchors, `engine/services/spell_effect_service.py` now applies `Innocence` through a dedicated utility handler that drops non-undead critter aggro while forcing undead backfire threat and now gates only on empathic shock rather than the unrelated `manipulate` tutorial unlock, `typeclasses/npcs.py` now suppresses non-undead auto-engage against actors carrying active Innocence, and `engine/presenters/spell_effect_presenter.py` now gives both spells dedicated messaging. Focused registry/service/runtime/presenter/NPC-aggro coverage validated green at `216 passed, 107 subtests passed`, the documented preservation slice validated green before live smoke at `294 passed, 107 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` after Evennia reload confirmed Merla teaching both spells, explicit off-self rejection for both with `You can only cast that spell on yourself.`, and a live Zone of Protection self-cast persisting `{'strength': 4, 'duration': 23, 'absorbs_physical': False}` on the caster. Live nuance worth preserving: the first Innocence cast attempt in `/play` surfaced a real local defect where the spell was incorrectly inheriting the Empath `manipulate` unlock gate (`You are not yet ready to impose calm on another mind.`); that hotfix was applied immediately and revalidated in focused tests, but a pre-existing bleed/death state contaminated the follow-up live character fixture before a clean second Innocence cast proof could complete.

- Completed DRG-EMPATH-06 as the canonical Empath Vitality Book dispatch. `domain/spells/spell_definitions.py` now ships `refresh` (403001), `raise_power` (403002), and `gift_of_life` (403003) as `gsl_2004` Vitality Book rows with the verified CASTMOD anchors and the corrected Gift of Life canon shape: self-cast only, augmenting empathic linking plus stamina/resilience rather than transferring life to another target. `typeclasses/characters.py` now preserves a bounded `self_or_other` targeting seam so Refresh defaults to bare self-cast while still allowing an explicit other target, `engine/services/spell_effect_service.py` now routes all three spells through dedicated bounded utility handlers, and `engine/presenters/spell_effect_presenter.py` now gives them dedicated self/target/room messaging. Focused vitality coverage validated green, the exact documented preservation batch reran green at `286 passed, 105 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` after Evennia reload confirmed Merla teaching all three spells, Refresh reducing persisted fatigue from `25` to `5` on self and `20` to `8` on `EmpathAuditPatient`, Raise Power increasing room Life mana from `1.0` to `1.48`, and Gift of Life persisting `gift_of_life_active=True` plus an active utility state containing `duration=1081`, `stamina_bonus=8`, `link_bonus=2`, and `saf_gate_deferred=True`. Live operator note: the smoke fixture had no free spell slots, so Gift of Life teaching required a temporary in-band circle bump to `11` before the final live cast verification.

- Completed DRG-EMPATH-05 as the canonical Empath Cleansing Book dispatch. Step 0 classified the poison/disease seam as `B`: `typeclasses/characters.py` already persisted poison and disease as first-class Empath wound buckets, the existing transfer loop already carried both through `take_empath_wound(...)` and `WoundTransferService.transfer(...)`, and the only missing runtime seam was a structured self-cleanse path for canonical spellcasting. `domain/spells/spell_definitions.py` now ships `flush_poisons` (402002) and `cure_disease` (402003) as `gsl_2004` Empath-only self-cast Cleansing Book rows with the verified CASTMOD anchors, `engine/services/spell_effect_service.py` now routes both through a bounded self-cleanse utility branch that clears the caster's persisted poison or disease bucket without widening into per-condition targeting, and `engine/presenters/spell_effect_presenter.py` now gives both spells dedicated self and room messaging. Focused registry/service/runtime/presenter coverage validated green at `182 passed, 102 subtests passed`, the exact documented preservation batch validated green at `273 passed, 102 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` after in-band `@reload` confirmed Merla teaching both spells, bare `cast` working for `Flush Poisons` and `Cure Disease`, persisted wound lines dropping from `P25` to `P0` and `D18` to `D0`, and explicit off-self targeting still rejecting in-band with `You can only cast that spell on yourself.`

- Completed DRG-EMPATH-04B as the canonical Empath Healing Book tier 3-4 plus cast self-target UX dispatch. `domain/spells/spell_definitions.py` now ships `external_wound_healing` (401001), `internal_wound_healing` (401002), and canonical `heal` (401008) as `gsl_2004` Empath-only healing rows, `engine/services/spell_effect_service.py` and `engine/presenters/spell_effect_presenter.py` now route all three through bounded self-healing injury/scar behavior with dedicated messaging, and `typeclasses/characters.py` now preserves bare `cast` self-defaulting only for healing rows whose registry metadata is explicitly `target_type="self"` while still rejecting explicit off-self targets for self-only healing spells. Focused runtime/service/presenter/registry coverage for the self-target cast seam and new Healing Book rows validated green at `173 passed, 98 subtests passed`, the required preservation batch validated green at `264 passed, 98 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` after a clean Evennia reload confirmed bare `cast` works with no `cast me` for External Wound Healing, Internal Wound Healing, and Heal, with persisted state proving the expected selective and combined self-heal outcomes. Live smoke also confirmed the explicit guardrail still holds in-band: `cast merla` on a prepared self-only healing spell returns `You can only cast that spell on yourself.`

- Completed DRG-EMPATH-04A as the first canonical Empath Healing Book content dispatch. `domain/spells/spell_definitions.py` now ships `vitality_healing`, `heal_wounds`, and `heal_scars` as `gsl_2004` Empath-only healing rows, preserves the verified script/CASTMOD anchors in spell metadata, and formalizes Step 0d as Repair-3 by keeping `empath_heal` live as a documented `hybrid_design` exception rather than silently rewriting it into canonical wound-transfer behavior. `engine/services/spell_effect_service.py` now enforces self-target-only healing when the registry says `target_type="self"`, routes Vitality Healing through the existing HP-heal seam, routes Heal Wounds through the existing Empath carried-wound state, and routes Heal Scars through the bounded body-scar state without widening into a new subsystem; `engine/presenters/spell_effect_presenter.py` now gives all three spells dedicated self and room messaging. Focused registry/service/presenter coverage landed alongside the DRG-EMPATH-02 provenance guard updates and validated green at `113 passed, 77 subtests passed`, the required preservation batch validated green at `246 passed, 15 subtests passed`, and live `/play` smoke on `SmokeEmpathLive` confirmed Merla teaching all three spells plus successful casts of Vitality Healing, Heal Wounds, and Heal Scars after a clean in-band reload. The only live residual surfaced by smoke is command-surface, not spell-runtime: self-target healing still currently requires `cast me` because a bare `cast` returns `You must specify a target.` even when the underlying spell is self-only.

- Completed DRG-EMPATH-03 as the Empath world content audit. Classification: `A`. `world/areas/crossing/empath_guild/build.py` already contained a fully wired 12-room Empath guildhall with descriptions on every room, a live recovery-space equivalent expressed through the existing `empath_zone_recovery` tagging on the Infirmary and Sitting Room rather than a missing shrine-style attribute, and a complete ambient roster around Guildleader Merla. `typeclasses/npcs.py` and `engine/services/guildhall_locator.py` were tagged inline as `directengine_canon` per DRG-CANON-POLICY-001, with no runtime-world fix required beyond provenance comments. The documented preservation batch stayed green at `240 passed, 15 subtests passed`. Live `/play` smoke reconfirmed the attached `SmokeEmpathLive` session in `Empath Guildleader's Office` with Guildleader Merla present; the broader Empath feed remained noisy with continuous audit-patient sense lines, so the remaining guild NPC placements were confirmed against live Evennia object state in the running world: Attending Empath and Wounded Traveler in the Entry Hall, Resting Patient and House Healer in the Infirmary, and Guild Librarian in the Library.

- Completed DRG-EMPATH-MECHANIC-001 as the canonical Empath wound-transfer service dispatch. `engine/services/wound_transfer_service.py` now establishes a thin `directengine_canon` service seam over the existing character-side `touch_empath_target(...)`, `link_empath_target(...)`, `take_empath_wound(...)`, and `mend_empath_self(...)` hooks instead of rebuilding the subsystem, and `commands/cmd_touch.py`, `commands/cmd_link.py`, `commands/cmd_take.py`, and `commands/cmd_mend.py` now route their live command surfaces through that service. The implementation preserves the canonical Empath profession gate, posture gate, fatigue gate, and 20-point-per-cycle cap, defers the unresolved concentration and SAF/moral equivalents per Q2, and applies the Empathy-for-Transference substitution conditionally rather than universally: only the current advanced typed transfer surface is checked there, while blank, `bleeding`, `vitality`, and selector-driven transfers continue through the grandfathered character seam. Focused service and command-routing coverage landed in `tests/services/test_wound_transfer_service.py` and `tests/test_empath_transfer_commands.py`, live `/play` smoke on `SmokeEmpathLive` preserved the canonical `touch` -> `link` -> `take` -> `mend self` loop with the expected in-band messaging, and this closeout reuses the last reported preservation result of `228 passed, 15 subtests passed` without rerunning it.

- Completed DRG-EMPATH-02 as the Empath spell registry canon-compliance audit. All `empath`-allowed rows in `domain/spells/spell_definitions.py` were classified against the canonical wound-transfer mechanic and documented in `docs/references/direngine-empath-spell-registry-audit.md`. The audit found one canon-compliant live Empath row (`regenerate`), one canon-violating live hybrid (`empath_heal`, which currently heals another character directly instead of routing through wound transfer), and thirteen grandfathered exceptions that remain either shared `directengine_canon` fundamentals or approved `magic_3_0_design` Analogous Patterns rows rather than canonical Empath class-book coverage. Registry provenance was updated so `empath_heal` now reads `hybrid_design`, the new audit guard in `tests/domain/test_spell_registry.py` validated green at `7 passed, 70 subtests passed`, and the required preservation batch stayed green at `228 passed, 15 subtests passed`. No runtime behavior changed in this dispatch; repair is explicitly scoped to `DRG-EMPATH-MECHANIC-001` and later Empath content dispatches.

- Completed DRG-EMPATH-01 as the Empath profession audit-and-tag dispatch. Step 0 classified the identity layer as `B`: the string-keyed Empath profession entry, `empath -> life` mana-realm routing, and the live `empathy` skill already existed and interlocked correctly enough to grandfather, but the intended Empath-first training seam was not actually being honored at runtime because `Character.get_exp_skillset_tier('empathy')` still resolved to `secondary`. The bounded fix kept the inherited Empath profession profile grandfathered as `directengine_canon`, tagged the canonical `empath -> life` routing and `empathy` skill seam inline, and repaired the EXP tier seam so Empathy now resolves as `primary` while `first_aid` and `scholarship` remain the supporting `secondary` skills called for by the audited Empath identity. Focused profession-skillset coverage expanded to six assertions and validated green at `6 passed`, the required preservation batch stayed green at `228 passed, 15 subtests passed`, and a post-reload live `/play` check on `SmokeEmpathLive` printed `{'profession': 'empath', 'mana_realm': 'life', 'empathy_tier': 'primary'}` from the live server.

- Completed DRG-EMPATH-FOUNDATION-001 as the bounded Empath guildmaster teaching-seam repair surfaced by DRG-EMPATH-AUDIT. `typeclasses/npcs.py` now gives `EmpathGuildleader.teach_spell(...)` an Empath-specific allowlist derived from the current Empath-only registry rows instead of the Cleric teaching allowlist, and focused guild-progression coverage was expanded in `tests/learning/test_guild_progression_commands.py` to prove on-class teaching, circle gating, off-class refusal, and refusal of shared cross-profession spells like `burden`. The code/test delta stayed bounded to the Merla seam plus one focused regression file, the touched slice validated green at `11 passed`, and the required preservation batch validated green at `228 passed, 15 subtests passed`. Live `/play` smoke on `SmokeEmpathLive` in `Empath Guildleader's Office` required one clean Evennia reload to pick up the new server code, after which `learn empath_heal from merla` succeeded with `Guildleader Merla instructs you in Empath_Heal. You commit the pattern to memory.`, `spells` showed `Heal (Healing)` added beside `Regenerate`, and the reverse class boundary still held on `learn bless from merla` and `learn divine_radiance from merla`.

- Completed DRG-EMPATH-AUDIT as the Empath class audit-and-scope dispatch. The audit classified profession identity, the Life mana realm, the custom Empath circle path, the wound-transfer class-identity loop, the existing Empath-accessible spell registry, the Empath guildhall / guildmaster scaffolding, and the required class-boundary learn checks. Findings were documented in `docs/references/direngine-empath-canon-audit.md`, and the resulting program sequence was documented in `docs/roadmap/drg-empath-program-scope.md`. The key audit result is `Class II`: wound transfer exists and was verified live on `SmokeEmpathLive` through `touch`, `link`, `take`, and `mend self`, but the structured spell/guild layer is not aligned with that identity yet. Live command smoke in Merla's office proved the reverse class boundary on `bless`, `divine_radiance`, and `hand_of_tenemlor`, but also surfaced the controlling Empath-program blocker: Merla currently refuses even `empath_heal` and `regenerate` because her `teach_spell(...)` seam is still wired to the Cleric teaching allowlist. The recommended next step is therefore `DRG-EMPATH-FOUNDATION-001`, followed by `DRG-EMPATH-01`.

- Completed DRG-CLERIC-10 as the Cleric program closeout dispatch. The comprehensive `SmokeClericLive` smoke matrix was executed end-to-end and preserved at the report layer: identity and guildhall routing held, bare `learn` still rendered mindstate, Cleric refused to learn Empath spells at the command level, Bless / Divine Radiance / Hand of Tenemlor / Uncurse all cast live, Rejuvenation enforced the shrine requirement and then succeeded from the Cleric Guild Chapel, shrine prayer restored favor in-band, and deferred surfaces stayed honest rather than crashing. In particular, `learn mass_rejuvenation from esuin` succeeded after freeing one slot and `cast` then returned the explicit placeholder `Mass Rejuvenation's held-mana ritual is not yet implemented.` with no traceback. The final preservation batch validated green at `224 passed, 15 subtests passed`. Policy revisit per DRG-CANON-POLICY-001 landed as decision `B`: hybrid-leaning-grandfather succeeded with caveats, so Empath should keep the same default posture while treating signature class-identity mechanics and live command-boundary smoke as mandatory proof points. Cleric closes with 14 canonical 2004-GSL spells live and a 10-item deferred-mechanics queue, and the class is now shippable.

- Completed DRG-CLERIC-09 (resumed) as the bounded Cleric progression-content follow-up to DRG-INFRA-GUILD-001: `typeclasses/npcs.py` now constrains Esuin's teaching surface to the 14 shipped canonical Cleric spells and enforces per-spell circle gating at the guildmaster seam, `engine/services/circle_service.py` now gives Clerics explicit Primary Magic plus Theurgy advancement requirements instead of the shared aggregate placeholder totals, and `domain/spells/spell_definitions.py` now tags Bless, Protection from Evil, and Holy Light as apprentice-accessible through circle 10. Focused regression coverage was expanded across guild progression, circle-service, and spell-access slices and validated green at `46 passed`, and the required preservation batch validated green at `205 passed, 15 subtests passed`. Live `/play` smoke was completed after a clean Evennia reload on `SmokeClericLive`: `learn halo from esuin` now correctly rejects below-circle learning with `You are not yet ready for Halo. Return when you have reached Circle 20.`, `circle` now reports `Esuin requires Primary Magic 250 and Theurgy 250 before marking Cleric circle 11.` with the expected per-skill missing lines, and a one-slot fixture reset followed by `learn bless from esuin` repopulated Bless in the live spellbook with `learned_via: npc`, closing the low-tier teach path end-to-end.

- Completed DRG-INFRA-GUILD-001 as the shared guild progression infrastructure slice: `learn` is now a single argument-dispatch command surface, with bare `learn` preserving the old mindstate display, `learn feat <feat>` preserving feat training, and `learn <spell> from <guildmaster>` routing through new guildmaster `teach_spell(...)` hooks in `typeclasses/npcs.py` into `SpellbookService.learn_spell(..., "npc")`. `circle` now preserves the grandfathered Empath path unchanged while routing non-Empaths through the existing generic `circle_service` projection/commit seams, which removes the old `Only Empaths can circle this way.` block for classes like Cleric without widening into per-class progression content. The bounded implementation touched four existing infrastructure files plus one focused regression file, Step 0a reconfirmed healthy test discovery at `1069` collected nodeids, the focused regression slice passed at `5 passed`, the required preservation batch passed at `197 passed, 15 subtests passed`, and live `/play` smoke proved the new Cleric path end-to-end on SmokeClericLive with `learn`, `learn bless from esuin`, `spells`, and non-Empath `circle` behavior after reload. Empath live smoke remains a documented follow-up only because browser session handoff repeatedly reattached the Cleric fixture instead of yielding a clean `SmokeEmpathLive` session; focused tests still preserved the Empath command path in code.

- Completed DRG-CLERIC-08 as the canonical Cleric utility sub-book slice: added `gsl_2004` registry rows for Spirit Beacon and Uncurse in `domain/spells/spell_definitions.py`, captured the dispatch's verified CASTMOD values in the canonical spell metadata, and routed both spells through the existing structured utility path instead of widening into new command-only behavior. Spirit Beacon now anchors bounded beacon metadata on the caster through the existing recovery-point seam, refuses to anchor while favor still leaves non-forced departure open, and clears automatically when the caster leaves the realms through the live death handler. Uncurse now routes through a new structured `StateService.apply_uncurse(...)` helper that reuses the existing cleanse/effect-removal seam, preserves Death's Sting relief from the legacy `uncurse` command surface, and clears hostile debilitation state without widening into a full curse taxonomy. Focused service/runtime/presenter/access coverage landed, the preservation batch validated green at `197 passed, 15 subtests passed`, and live `/play` smoke confirmed Uncurse end-to-end on SmokeClericLive after in-band registry/service reload by teaching the spell, applying a temporary Burden payload to `Iirc Probe`, casting `uncurse`, and reading the target's live `active_effects` back as `{}`. Centering, Persistence of Mana, Shield of Light, Phelim's Sanction, Soul Attrition, and broader Spirit Beacon discoverability UX were all explicitly deferred into the Cleric deferred-mechanics tracker rather than widened into this dispatch.

## 2026-05-14

- Completed DRG-CLERIC-07 as the canonical Cleric divine intervention sub-book: added `gsl_2004` registry rows for Aesrela Everild, Revelation, and Hand of Tenemlor in `domain/spells/spell_definitions.py` using the dispatch's verified CASTMOD values, extended the existing structured contest path so targeted divine intervention spells can override their contest profile, damage location, and simple on-hit side effects through metadata, and routed Revelation through the existing hidden-state reveal seam without widening perception into a new subsystem. Aesrela Everild now uses a bounded theurgy-vs-attack contest profile and applies stun on a successful hit, Revelation forces hidden targets into plain sight through the existing `reveal()` seam, and Hand of Tenemlor now deals holy fire damage through the left-hand wound path. Glythtide's Gift stayed excluded because it is auction-scroll content rather than standard Cleric progression, and Huldah's Pall was explicitly deferred because the grandfather policy still does not implement SAF/uncleanliness. Hand of Tenemlor's deterministic scar mechanic was also deferred into the cumulative Cleric deferred-mechanics tracker because the current wound seam supports left-hand damage but not the canonical guaranteed scar without widening scope. Focused DI service/runtime/presenter/access coverage landed, the required preservation batch validated green at `188 passed, 15 subtests passed`, repo memory now tracks the cumulative Cleric deferred queue, and live `/play` smoke confirmed Hand of Tenemlor end-to-end on SmokeClericLive after restart and in-band reteach by casting it on the armored training dummy and seeing the new DI damage messaging in the feed.

- Completed DRG-CLERIC-06 as the canonical Cleric resurrection sub-book: added `gsl_2004` registry rows for Rejuvenation and Mass Rejuvenation in `domain/spells/spell_definitions.py` using the dispatch's verified CASTMOD values, introduced a bounded `resurrection` spell family that routes Rejuvenation straight into the existing grandfathered cleric corpse-revive seam instead of reimplementing resurrection logic, mapped the new family onto the structured cast metadata path, and added focused service/runtime/presenter/access coverage for corpse-targeted resurrection casts. Mass Rejuvenation's held-mana room ritual was explicitly deferred at the registry layer because there is no cheap existing sustained pulse seam to reuse without widening scope; it currently returns a clear placeholder failure instead of silently pretending the ritual exists. Canon class-spell boundaries were recorded in repo memory so wound-healing stays with the Empath program rather than drifting back into Cleric content. The required preservation batch validated green at `177 passed, 15 subtests passed`, and live `/play` smoke confirmed Rejuvenation on SmokeClericLive end-to-end by teaching the spell in-band, creating a temporary dead target, casting on the corpse, and verifying the revived target reappeared in the room.

- Completed DRG-CLERIC-05 as the canonical Cleric wards sub-book follow-up to CLERIC-04: added `gsl_2004` registry rows for Major Physical Protection, Halo, and Divine Radiance in `domain/spells/spell_definitions.py` using the dispatch's verified CASTMOD values, extended the existing warding path so higher-tier physical wards can scale via metadata and light-emitting wards can mirror into the live light-state view, added three-audience presenter coverage plus focused runtime/effect/combat/access tests, and generalized the undead ward-bonus combat hook so Divine Radiance can reuse the same live defensive seam as Protection from Evil. Halo's full engaged-target pulse mechanic was intentionally deferred from this slice because it would require a broader runtime effect loop than the bounded CLERIC-05 budget allowed; the spell ships now as a documented ward-state placeholder under the existing infrastructure rather than as a silent scope expansion. The focused ward slice validated green at `165 passed, 15 subtests passed`, the requested preservation batch validated green at `170 passed, 15 subtests passed`, and live `/play` smoke confirmed Divine Radiance casts end-to-end on SmokeClericLive after restart and in-band reteach, with the browser showing the self-message plus `Barrier Active` and `Light Spell` state.

- Completed DRG-CLERIC-04 as the first bounded canonical Cleric content dispatch: added `gsl_2004` structured spell rows for Bless, Protection from Evil, Minor Physical Protection, and Holy Light in `domain/spells/spell_definitions.py`, routed them through live structured utility/warding state, added three-audience presenter coverage plus focused runtime/effect/combat tests, and added narrow undead-specific combat hooks so Bless and Protection from Evil affect live resolution instead of existing as inert registry metadata. Vigil was explicitly deferred from this sub-book because the verified spell shape is a spirit-link conduit rather than a simple blessing/buff and would require separate sustained-link mechanics.

- Completed DRG-CLERIC-03 as the final Cleric audit-shaped dispatch before content work: the Crossing Cleric guildhall bootstrap in `world/areas/crossing/cleric_guild/build.py` was audited as `directengine_canon`, the live guildhall inventory was confirmed at 12 rooms with Guildleader Esuin, the Guild Archivist, and the Chapel Acolyte present, and the one surfaced infrastructure gap was closed by consecrating the existing guild chapel as the live Cleric shrine surface for grandfathered devotion/favor prayer. No object-backed sacred items were found beyond chapel altar/world dressing, so sacred-object expansion remains deferred rather than blocking CLERIC-04. The post-edit Cleric preservation batch stayed green at `83 passed, 58 subtests passed`.

- Completed DRG-CLERIC-02 as the Cleric spell-registry provenance cleanup identified by DRG-CANON-AUDIT-002 System 8: existing Cleric-accessible non-canonical spell rows in `domain/spells/spell_definitions.py` no longer inherit false `gsl_2004` authority, bespoke DireEngine Cleric roster entries are now explicitly tagged `directengine_canon`, the four approved Analogous Patterns exceptions remain `magic_3_0_design`, and focused registry assertions were added so this provenance split stays locked. Step-0 verification also closed the prior DRG-CLERIC-01 learning residual cleanly at `129 passed`, and the post-edit Cleric preservation batch stayed green at `83 passed, 58 subtests passed`.

- Completed DRG-CLERIC-01 as a bounded audit of Cleric profession identity and Holy realm routing: the existing `cleric` profession profile and Holy mana-realm seams were verified end-to-end and explicitly tagged in code as `directengine_canon` per DRG-CANON-POLICY-001, no behavior-level gap in the routing foundation required a refactor, and the live SmokeClericLive fixture was confirmed present with Cleric profession, guild tag, Holy mana realm, and preserved Cleric subsystem state. Preservation validation stayed green on the targeted mana, runtime, spellbook, and learning slices. The only surfaced smoke limitation is fixture loadout rather than routing itself: SmokeClericLive currently knows only `gauge_flow` and `manifest_force`, so a live `/play` Holy-spell cast could not be exercised without teaching the fixture a Cleric Holy spell first.

- Resolved DRG-WEBAUTH-001 as an operational stale-cache seam rather than a code defect: local `/auth/login` failures after shell-side password changes were caused by stale in-memory Account state, and a clean Evennia restart restored live browser login against the same database with no auth code changes.
- Completed the stabilization punchdown required to recover the `/play` magic smoke loop: `typeclasses/characters.py` now sorts legacy uncategorized skills safely for `health`/`stats`, `SKILL_REGISTRY` now includes the runtime magic skills `cyclic` and `healing`, `SmokeClericLive` and `SmokeEmpathLive` were re-normalized through the EXP persistence seam, and `commands/cmd_woundadmin.py` adds deterministic `@wound` setup for live healing smoke.
- Re-ran the recovered live smoke after those repairs and cleared the previously blocked browser path: `spells`, `slots`, and `feats` rendered cleanly, Gauge Flow, Manifest Force, and Strange Arrow completed live, wounded Regenerate sustained and healed successfully, and Burden applied cleanly on a living target. The earlier Burden miss on `SmokeEmpath` was reclassified as target-specific contest failure rather than a broken debilitation application path.

- Completed DRG-CANON-001A-FOLLOWUP profession-modifier correction in `domain/mana/backlash.py`: the GSL caller-context re-read for `MANADIFF` now applies commoner/barbarian as a 50% effective-skill penalty and thief/trader as an 80% penalty instead of accidentally buffing low-magic professions, the commoner mana-service fixtures were retuned to the corrected scale, and the broader stale cyclic/presenter/schema expectations were updated to current runtime behavior.
- Revalidated the full repo suite after the follow-up repair at `1006 passed, 1 skipped, 52 subtests passed`; the remaining closure gate is the recovered `/play` smoke matrix, which is currently blocked by a local web auth seam where real HTTP `/auth/login` rejects valid `jekar` credentials even though Django `authenticate(...)`, `AuthenticationForm`, and the in-process test client accept the same username/password against the same database.

- Completed DRG-CANON-001A cast-resolution correction: `domain/mana/backlash.py` now uses GSL Magic v2.1-style scaled primary-magic control, excess-mana difficulty, ratio-based failure versus backlash separation, and canonical backfire severity mapping instead of the older heuristic multi-skill pressure model.
- Threaded the canonical spell-profile data needed for that math through the live cast seam: `engine/services/mana_service.py` and `typeclasses/characters.py` now preserve `mana_min`, `mana_max`, `diff_per_extra_mana`, and `provenance` across prepared spell state, and the focused mana plus runtime/service preservation slices validated green at 19 domain tests and 85 service/runtime tests plus 15 subtests.
- Recalibrated the four approved DireEngine Magic 3.0 starter spells in `domain/spells/spell_definitions.py` to low-difficulty canonical cast ranges while preserving their bespoke live behavior, and tagged Burden, Gauge Flow, Strange Arrow, and Manifest Force as explicit grandfathered exceptions through per-spell provenance rather than treating them as generic 2004 GSL spell rows.

- Executed DRG-RUNTIME-003 as fixture-only maintenance with no runtime code edits: `SmokeClericLive` and `SmokeEmpathLive` were rebalanced to rank 50 across the runtime cast-resolution skills required by the recovered-session smoke matrix, and the durable persistence seam for those live fixtures is now the exp-skill handler plus `_persist_exp_skill_state(...)` rather than `Character.update_skill(...)` alone.
- Revalidated the preserved post-maintenance slices after the live fixture rebalance: the requested learning preservation batch finished clean at 49 tests, and the requested magic/runtime preservation batch finished with 122 passed plus 15 subtests passed before pytest was interrupted during teardown rather than by an assertion failure.
- Re-ran the six-scenario recovered `/play` smoke matrix against the normalized fixtures. Gauge Flow and Manifest Force both completed end-to-end in-browser, while Burden, Strange Arrow, and SmokeEmpathLive Regenerate still backlashed live after recovery, and `learn feat focused preparation` triggered a separate live traceback in `commands/cmd_mindstate.py` via `Character.get_skill_entries()`. DRG-RUNTIME-003 therefore confirms the fixture imbalance was real and corrected, but it does not close the remaining live runtime smoke defects.

- Completed DRG-RUNTIME-002 cooldown serialization repair in `world/area_forge/character_api.py`: `_get_cooldowns()` now treats persisted spell cooldown entries as generic mappings instead of builtin `dict` only, so Evennia `_SaverDict` cooldown payloads read their `duration` field correctly, flat scalar fallback remains intact for backward compatibility, and malformed cooldown values now degrade to `0` instead of crashing browser payload generation.
- Added focused regression coverage in `tests/test_character_api.py` for empty cooldown state, builtin dict cooldowns, real Evennia `_SaverDict` cooldowns, malformed values, runtime `ndb.cooldowns` merging, and `get_character_payload()` integration; the new focused slice validated green across 10 tests, the requested magic preservation slice validated green across 133 tests, and the requested LEARN preservation slice validated green across 49 tests.
- Live validation after restarting the web stack confirmed the original `_SaverDict` traceback no longer reproduces on recovered `/play` sessions: `get_character_payload(SmokeClericLive)` now succeeds with live `_SaverDict` cooldown state present, recovered browser commands such as `target`, `prepare burden 5`, `prepare strange_arrow 5`, and `prepare manifest_force 5` no longer explode in `character_api.py`, and Manifest Force completed end-to-end in-browser with Barrier Active state visible and payload reads still clean afterward. Gauge Flow remained entangled with a separate stale live cooldown gate on `SmokeClericLive`, and `SmokeEmpathLive` browser smoke verified the held-mana harness path but not the full cyclic sustain path because Regenerate backlashed twice before sustain initialized; those live-smoke wrinkles are separate from the repaired cooldown reader.

- Completed DRG-WEBCLIENT-002 send-guard plus bootstrap-latch repair in `web/static/webclient/js/dragonsire-browser-v2.js` and cache-busted the served play template in `web/templates/webclient/webclient.html`: disconnected `/play` commands now queue instead of fake-echoing as sent against a closed transport, `requestInitialRefresh()` now defers through `initialRefreshPending` and only latches `initialRefreshSent` on actual delivery, and reconnect bootstrap drains before queued user commands.
- Revalidated the post-restart recovery seam across three full `startWeb.bat` stop/start cycles on canonical `localhost`: after restart the page still entered the expected disconnected state, queued commands showed explicit `Queued; reconnecting...` feedback instead of local fake-send echo, and manual reconnect consistently returned to a fully populated playable session with queued commands delivered after recovery.
- Preserved executable coverage while landing DRG-WEBCLIENT-002: the DRG-RUNTIME slot bootstrap regression slice stayed green at 27 tests, the LEARN preservation slice stayed green at 128 tests, and the magic preservation slice stayed green at 158 passed plus 15 subtests passed. Recovery-smoke execution on the recovered session confirmed working `spells`, `slots`, apprentice spell visibility, `feats`, and recovered casting command transport, while surfacing separate magic-runtime defects in `world/area_forge/character_api.py::_get_cooldowns()` during Gauge Flow, Strange Arrow, and Manifest Force browser smoke that should be filed as follow-up maintenance rather than treated as webclient regressions.

- Completed DRG-RUNTIME-001 slot-pool bootstrap recursion fix: `engine/services/slot_service.py::_get_circle()` now reads persisted `db.circle` directly instead of re-entering `Character.get_circle()` during slot-pool initialization, breaking the deterministic `get_circle()` → `ensure_core_defaults()` → `ensure_magic_slot_pool_defaults()` → `SlotService.get_pool()` → `_get_circle()` recursion loop that affected legacy magic users with `magic_slot_pool=None`.
- Added focused recursion regression coverage in `tests/services/test_slot_service.py` and new `tests/services/test_slot_pool_bootstrap_recursion.py`; the targeted slot suite validated green across 27 tests, the requested adjacent magic preservation slice validated green across 133 tests, and the requested LEARN preservation slice validated green across 49 tests.
- Live verification confirmed the originally affected legacy characters (`Khreos`, `Debug Ranger`, `TMP_EMPATH`, `TMP_EMPATH_2`, `TMP_EMPATH_3`, `SIM_FULL_EMPATH_03`, `SIM_FULL_EMPATH2_03`, `SIM_FULL_CLERIC_03`, `SIM_FULL_EMPATH_28`, `SIM_FULL_EMPATH2_28`, and `Wufgar`) now self-heal from `magic_slot_pool=None` to a normalized persisted slot-pool mapping on first access with no migration. Browser-side `ic Wufgar` on `/play` remained blocked by the separate disconnected-handshake state already deferred to DRG-WEBCLIENT-002, but the recursion failure itself no longer reproduced.

- Completed DRG-024.5d-3a cyclic canon correction: `engine/services/spell_effect_service.py`, `engine/services/state_service.py`, `engine/services/mana_service.py`, and `typeclasses/characters.py` now treat cyclic upkeep as a sustain-source problem instead of an attunement-only drain, selecting `held_mana` by default, allowing `attunement` only through Raw Channeling, carrying `sustain_source` plus `sustain_ref` on active cyclic state, and enforcing canon's one-active-cyclic-at-a-time rule before cast-time mana resolution.
- Corrected DRG-024.5d-2 feat scope around cyclic upkeep: `domain/feats/feat_definitions.py` now registers `raw_channeling` as a capability-unlock feat with Bard circle-2 free grant semantics, `efficient_channeling` still reduces cyclic pulse cost regardless of sustain source, and `efficient_harnessing` now only affects attunement-direct cyclic upkeep rather than held-mana sustain. Cambrinth sustain is schema-valid but still returns a clean deferred-subsystem error until DRG-024.5d-4.
- Added cyclic-correction regression coverage across `tests/services/test_mana_service.py`, `tests/services/test_spell_effect_service.py`, `tests/services/test_character_spell_runtime.py`, `tests/services/test_feat_runtime_integration.py`, and `tests/services/test_feat_training_service.py`; focused and preserved validation slices finished green across 90 cyclic/feat service tests, 72 runtime/mana tests plus 15 subtests, 158 adjacent magic/feat/circle tests plus 15 subtests, 18 slot/spellbook/feat service tests, 128 learning preservation tests, and 60 combat preservation tests.

- Completed DRG-024.5d-2 magical feats starter-set integration: `domain/feats/feat_definitions.py` now registers seven starter feats in a dedicated feat catalog, `engine/services/feat_service.py` exposes passive modifier lookup over learned plus granted feats, and `engine/services/feat_training_service.py` now owns feat learning, forgetting, and profession-granted feat flow on top of the shared `magic_slot_pool`.
- Integrated feats into the live magic runtime and world surfaces: `engine/services/mana_service.py`, `engine/services/state_service.py`, `engine/services/circle_service.py`, and `typeclasses/characters.py` now apply feat modifiers at attunement regeneration, harness/cast spend, prepared expiry, cyclic drain, backlash injury, prep-time calculation, and circle advancement, while `typeclasses/feat_trainer.py` plus `world/areas/the_landing/feat_trainers/build.py` add the first Landing feat trainer and bootstrap path.
- Added public feat commands and focused regression coverage: `commands/cmd_feats.py`, `commands/cmd_learn_feat.py`, and `commands/cmd_forget_feat.py` are now registered in `commands/default_cmdsets.py`, and the new feat-focused and adjacent preservation slices validated green across 23 feat tests plus 59 neighboring mana/circle/spell/trainer tests.

- Completed DRG-024.5d-1 spell-slot foundation and apprentice expiration: `domain/spells/spell_definitions.py` now carries `slot_cost` and `apprentice_until_circle`, `engine/services/slot_service.py` now owns the generic `magic_slot_pool` keyed by allocation category, and the canonical Analogous Patterns seed registrations are corrected so Burden, Strange Arrow, and Manifest Force derive apprentice access through circle 10 while Gauge Flow does not.
- Integrated the slot economy into live learning and circle progression: `engine/services/spellbook_service.py` now gates permanent memorization on available slots and allocates spell costs into the shared pool, `engine/services/spell_access_service.py` now merges permanent and apprentice access without persisting apprentice spells into `db.spellbook`, and `engine/services/circle_service.py` plus `typeclasses/characters.py` now recompute slot maxima on advancement, privately warn at circle 10, and privately expire unmemorized apprentice spells at circle 11.
- Added player-facing slot visibility and focused regression coverage: `commands/cmd_slots.py` now reports the magic-slot pool instead of worn equipment slots, `commands/cmd_spellbook.py` now exposes the public `spells` command with permanent-versus-apprentice sections, and the new slot/apprentice validation slices are green across 60 focused tests plus the preserved Manifest Force magic slice at 131 passed and 15 subtests passed.

- Completed DRG-024.5c Manifest Force and physical barrier combat integration: `domain/spells/spell_definitions.py` now registers canonical `manifest_force` metadata, `engine/services/spell_effect_service.py` computes its mana-scaled capacity and duration with replace-on-recast behavior, and `engine/services/state_service.py` mirrors physical-only wards through the structured active-effects model without widening prototype wards into physical absorption.
- Integrated physical barrier consumption into the live combat seam: `domain/combat/resolution.py` now consumes physical-only wards after armor and before wound shaping, `engine/services/combat_service.py` threads `barrier_event` through the combat payload, `engine/presenters/combat_presenter.py` renders shielded, weakened, and depleted barrier narration, and `typeclasses/characters.py` now keeps magic-only ward consumption from accidentally falling through to Manifest Force's mirrored state.
- Added DRG-024.5c presenter and runtime coverage across `tests/services/test_spell_effect_service.py`, `tests/combat/test_resolution.py`, `tests/services/test_character_spell_runtime.py`, `tests/presenters/test_combat_presenter.py`, and `tests/presenters/test_spell_effect_presenter.py`; the focused Manifest Force validation slice is green at 131 passed.

- Completed DRG-024.5b starter spell catalog seeding: `domain/spells/spell_definitions.py` now carries explicit `mana_min`, `mana_max`, `min_prep_time`, `expiry_window`, and `canon_status` metadata, marks the legacy registry entries as `prototype` by default, and adds canonical Analogous Patterns seed spells for `burden`, `gauge_flow`, and `strange_arrow`.
- Extended the structured magic runtime for the new seed families: `engine/services/state_service.py` and `typeclasses/characters.py` now carry stat and encumbrance debuff payloads through the existing active-effects model for Burden, `engine/services/spell_effect_service.py` now supports Gauge Flow capability-state application, and `engine/services/spell_contest_service.py` now supports mixed typed damage components so Strange Arrow lands as puncture plus electrical damage without widening into combat-resolution changes.
- Added spell-specific presentation and expiry coverage for the starter spells in `engine/presenters/spell_effect_presenter.py`, expanded focused and adjacent magic regression coverage across presenter, service, pipeline, runtime, interaction, PvP, access, and mana suites, and validated the widened preservation slices green across 167 magic tests plus 15 subtests, 63 learning tests, and 63 combat tests. Manifest Force remains split to DRG-024.5c.

- Completed DRG-024.5a magic canon reconciliation: `engine/services/mana_service.py` now forms spell patterns without spending attunement during `prepare`, draws attunement during `cast`, tracks independent harnessed mana, and adds scheduler-backed full-prep and prepared-expiry seams that sync back into `typeclasses/characters.py` prepared state.
- Added the public `harness` verb in `commands/cmd_harness.py`, rewrote `commands/cmd_release.py` into a polymorphic release surface for prepared spells, held mana, cyclic effects, and empathic links, and registered the new verb in `commands/default_cmdsets.py` while preserving the existing prepare/cast routers.
- Updated lifecycle-facing runtime coverage in `tests/services/test_mana_service.py` and `tests/services/test_character_spell_runtime.py`, validating the corrected spend-on-cast loop, full-prep transition seam, held-mana release behavior, cyclic shutdown, and empath-link fallback green across 61 runtime/service tests plus 15 subtests.

- Completed DRG-LEARN-006 defense XP canon parity: `domain/combat/resolution.py` now resolves parry and shield defenses through `parry_ability` and `shield_usage`, `engine/services/combat_xp.py` now routes parry XP into `parry_ability`, adds shield XP into `shield_usage`, and awards opportunistic `multiple_engaged_opponent` XP when `incoming_attackers > 1`, and `engine/services/defense_verb_service.py` now treats remedial parry learning as canonical `parry_ability` training rather than a weapon-skill bridge.
- Added focused LEARN-006 regression coverage in `tests/combat/test_resolution.py`, `tests/combat/test_defense_verbs.py`, and `tests/services/test_combat_xp.py`; the defense slice validated green across 31 tests, the broader learning preservation slice reran green across 123 tests, and the adjacent combat/messaging preservation slice reran green across 80 tests.
- Live verification for LEARN-006 reached partial browser smoke only: in-band `spawndummy` combat and defense messaging were exercised on Jekar, but the post-restart websocket session did not stay attached cleanly enough to finish canonical pool accrual proof in-browser, so the authoritative validation for the new routing remains the executable test slices above.

- Completed DRG-SKILL-001 engine skill identity alignment: `typeclasses/characters.py::SKILL_REGISTRY` now carries canonical `display_name` metadata across all live skills, the defense identities `shield_usage`, `parry_ability`, and `multiple_engaged_opponent` now exist as first-class registry entries under the new `defense` learning category, and `commands/cmd_experience.py` plus `world/systems/skills.py` now render registry-backed display names instead of relying on ad hoc titleization and bridge overrides.
- Realigned `domain/learning/skill_aliases.py` and `domain/learning/skill_groups.py` around the live registry: `exp parry`, `exp shield`, and `exp moe` now resolve to dedicated defense skills, every canonical pulse-group `skill_id` now maps to a real registry entry, `tactics` and `trading` moved into the live lore pulse group, and group 9 is back to an empty profession-reserved state for future profession dispatches.
- Added DRG-SKILL-001 regression coverage in `tests/learning/test_skill_identity_alignment.py`, updated the focused alias/group/experience expectations, validated the expanded learning preservation slice green across 123 tests, reran the adjacent combat and messaging preservation slice green across 72 tests, and completed live browser smoke for `exp parry`, `exp shield`, `exp moe`, `exp light_edge`, and `exp all` after a full Evennia restart.
- Completed DRG-LEARN-004 sleep and rested EXP runtime integration: characters now persist `sleep_state`, rested EXP bank/cycle fields, and offline timestamps on `typeclasses/characters.py`; the new `engine/services/rexp_service.py` owns online banking, per-group REXP consumption, cycle enforcement, and static offline drain against the live `SkillState` plus `db.exp_skill_state` seam.
- Added `sleep` and `awake` command surfaces, automatic wake-on-action through `commands/command.py`, sleep-aware XP blocking in `engine/services/skill_service.py`, deep-sleep pulse suppression plus light-sleep drain continuation in `engine/services/pulse_service.py`, and rested EXP status lines in `commands/cmd_experience.py`.
- Added focused LEARN-004 regression coverage in `tests/learning/test_sleep_rexp_runtime.py` and extended `tests/learning/test_exp_command.py`; the combined sleep/rested EXP and adjacent learning command slice validated green across 22 tests.
- Completed DRG-LEARN-003b pulse runtime replacement: `world/systems/skills.py` now consumes canonical pool-size and wisdom helpers from `domain/learning/pool_size.py`, profession-driven skillset tier routing now flows through `world/professions/professions.py`, and the live EXP runtime now uses the LEARN-003a 35-band mindstate table instead of the older sparse threshold map.
- Replaced the old five-offset EXP pulse rotation with the canonical 10-group rotation from `domain/learning/skill_groups.py` while preserving the existing transient `SkillState`, persisted `db.exp_skill_state`, and `Character.on_skill_rank_gained()` TDP accrual seam.
- Added actor-only private mindstate milestone and mind-lock notifications through the shared messaging helper, and mind-locked skills now reject new XP grants while continuing to drain normally through the pulse.
- Added focused LEARN-003b runtime regression coverage in `tests/learning/test_runtime_learning.py`, then validated the preserved learning/TDP slices green across 111 tests, the focused `experience`/trainer/circle preservation batch green across 40 tests, and the adjacent combat plus messaging preservation slices green across 72 tests.
- Added the first DRG-LEARN-003a canon-data slice: `domain/learning/mindstate.py` now owns the full 35-band mindstate table, `domain/learning/skill_groups.py` now captures the canonical 10 pulse groups, `domain/learning/pool_size.py` now exposes canonical pool-size plus wisdom helpers, and profession metadata now includes per-guild primary/secondary/tertiary skillset placement tables.
- Migrated the old 10-second global learning ticker to teaching-only processing while preserving a compatibility wrapper for legacy `process_learning_tick` references; the retired per-character learning-pulse branch is no longer invoked from startup ticker wiring.
- Added focused LEARN-003a regression coverage for canonical mindstates, pulse groups, pool-size math, profession skillset placement, and the teaching-only ticker slice, with the 21-test infrastructure slice validated green.
- Added DRG-MSG-001 three-audience messaging remediation: `engine/services/messaging.py` now centralizes actor/target/room delivery, `train`/`study` and guildleader advancement flows now surface room-visible observer lines, `target`, `disengage`, and `combatreset` now emit canonical split messaging, and combat presentation now distinguishes parry, shield, evade, mitigation, and force-of-impact narration.
- Added focused messaging regression coverage across helper behavior, stat training, circle advancement, command-level audience routing, and combat presenter semantics, with the combined 46-test messaging slice validated green.
- Added DRG-LEARN-002b mechanics on top of the 002a infrastructure: deterministic player-facing skill aliases, eight direct stat info commands (`strength`, `stamina`, `agility`, `reflex`, `charisma`, `discipline`, `wisdom`, `intelligence`), `Character.spend_tdp()`, stat-training consult/commit flow, and guildleader-driven circle projection/commit services.
- Expanded `experience` to support `exp <skill>` detail views, the new `exp circle` progression projection, and bridged `parry`/`shield` lookups that intentionally map through the current combat track until dedicated defense-skill parity ships in LEARN-006.
- Context-routed `train` and `study`: at stat trainers they now consult and commit stat gains, and at guild leaders they now project and commit placeholder circle advancement using the guildhall locator plus `db.coins` rather than the nonexistent older `db.silver` field.
- Added focused LEARN-002b regression coverage for aliases, stat info output, stat training, circle advancement, and the expanded experience command, then validated the adjacent LEARN-001, LEARN-002a, and DRG-024 combat slices still pass.
- Added DRG-LEARN-002a stat-training infrastructure: a parallel `RACIAL_TDP_MODIFIERS` table for all 11 races across the full 8 modern DR training stats, plus `domain/learning/tdp_cost.py` cost utilities for single-step and projected TDP spend.
- Added fresh `StatTrainerNPC` and `GuildLeaderNPC` typeclasses without refactoring the existing Empath, Cleric, or Ranger guildleader classes, preserving current profession-specific behavior while establishing the new shared infrastructure seam.
- Added eight stat trainer rooms in The Landing with `region_name = "The Landing"`, stat-specific room tags, one trainer NPC per room, and a startup bootstrap hook so the trainer hub is rebuilt alongside the Landing world content.
- Added `engine/services/guildhall_locator.py` with pre-registered Empath, Cleric, and Ranger guildhalls, and added focused regression coverage for TDP cost math, trainer infrastructure, and guildhall lookup in `tests/learning/`.
- Added DRG-LEARN-001 TDP foundation wiring: `Character` now persists `db.tdp` and `db.tdp_pool`, seeds new and migrated characters to the modern DR 600-starting-TDP baseline, and converts reached ranks into spendable TDPs through the shared 200-point hidden pool.
- Hooked TDP accrual into `world/systems/skills.py::process_rank()` so every actual rank crossed contributes its reached rank value without changing the existing pulse scheduler.
- Added the player-facing `tdp` command, exposed TDP totals at the bottom of `experience`, and restricted hidden-pool display to `Admin` and `Developer` viewers.
- Added focused regression coverage for TDP defaults, canonical 50-rank and 100-rank examples, rank-up hook integration, and both command surfaces in `tests/test_tdp_foundation.py`.

## 2026-05-12

- Completed DRG-WEBCLIENT-001 webclient lifecycle maintenance: `web/static/webclient/js/dragonsire-browser-v2.js`, `web/static/webclient/css/dragonsire-browser.css`, `web/templates/base.html`, `web/templates/webclient/base.html`, and `web/templates/webclient/webclient.html` now canonicalize loopback browsing to `localhost`, correct the stale Popper SRI hash, hide the draggable right rail while disconnected so reconnect controls are reachable in the attached browser viewport, and route browser-side recovery through the authenticated `/play` flow instead of depending on a dead websocket console call.
- Revalidated the restart failure path against Evennia 5.0.1, recollected static assets during implementation, and confirmed the canonical browser recovery path: after full `startWeb.bat` stop/start, browser-driven recovery through `localhost` plus the authenticated `/play` redirect restores the selected Jekar session without JS console intervention, and stale `127.x` loopback tabs now canonicalize back onto the same cookie context.
- Preserved executable coverage while landing DRG-WEBCLIENT-001: the LEARN preservation suite and the focused magic preservation suite were rerun after the webclient changes, with long-running slices left to finish from the active terminals because they exceeded the initial timeout window.

- Added the DireEngine Phase 4 master roadmap at `docs/roadmap/direngine-phase-4.md` as the canonical planning reference for Phase 4 dispatches.
- Added `DATA-GAP-AUDIT.md` with the Phase 4 audit note and sequencing summary.
- Recorded the current validation snapshot for DireLore connectivity, canon table counts, authority architecture, and profession registry coverage in the roadmap.
- Added the DRG-022 stub inventory at `docs/roadmap/stub-inventory.md` and recorded the grouped hardcoded-content violations driving Phase 4 migration work.
- Added the bundle extension architecture contract at `docs/architecture/bundle-extension-api.md` and implemented the initial `engine/bundles/` registry and loader package.
- Migrated Character stat defaults to the new `stat_registry`, backed by DireLore `public.canon_stats` on port `5432` with a logged fallback path when DireLore is unavailable.
- Wired `skill_registry` from DireLore `public.canon_skills` through `engine/bundles/builtin_skills.py` and replaced `SKILL_GROUPS` pulse metadata reads with registry-backed helpers.
- Added focused tests for skill registry population and pulse-service integration, and verified live Evennia boot both with canon available and with DireLore temporarily unavailable.
- Replaced the pre-GSL flat hit-chance combat resolver with the canon-correct OF minus EDF subtractive contest from S00041/S00042/S00043/S00046/S00091/S00092, backed by a new S00265-style combat RNG helper in `domain/combat/rng.py`.
- Preserved the existing `AttackResolution.details` compatibility surface while adding canonical combat state fields such as offensive factor, evasion defense factor, leftover OF, force of impact, parry, shield, and combat outcome.
- Updated `engine/services/combat_service.py` and `engine/services/combat_xp.py` to consume the new combat core without breaking legacy callers, then added focused combat tests plus regression coverage for ammo depletion and bundle wiring.
- Followed up DRG-024 with resolver hardening for placeholder criticals, injected RNG determinism, and fallback hit-location selection so valid targets without initialized injury maps no longer crash the damage path.
- Verified Evennia restarts cleanly after DRG-024 via `startWeb.bat` and `evennia status`; live shell smoke reached the new resolver path, with remaining harness friction isolated to thin test dummy methods rather than the combat core itself.
- Added DRG-024b attack verb routing via `domain/combat/verbs.py`, `engine/services/attack_verb_service.py`, and `commands/cmd_attack_verbs.py`, wiring `thrust`, `lunge`, `slice`, `chop`, `sweep`, `feint`, and `jab` through the canonical combat pipeline with explicit verb RT.
- Preserved the verb-specific GSL branches for DRG-024b: S00033 slice defender hook, S00034 tree/vine chop guard, and S00036 feint engagement-target fallback, while keeping generic `attack` as the default path.
- Added focused verb-routing tests and reran the broader combat plus bundle-registry regression slices; the initial live browser smoke confirmed explicit verb text for thrust/slice/chop and the `chop trees` guard.
- Shipped DRG-INFRA-001 by exposing `Character.sync_state_to_client()`, fixing the separate Character-level dead-state command gate for `combatreset` and `cmbreset`, and validating same-session dead-state recovery in the browser with no logout required.
- Closed the remaining DRG-024b live smoke after the sync fix: live browser runs confirmed `lunge`, `sweep`, `jab`, and targetless `feint`, with `feint` correctly falling back to the active engagement target.
- Added DRG-024c defensive stances via `commands/cmd_defense_verbs.py` and `engine/services/defense_verb_service.py`, wiring `parry` and `dodge` to canonical maneuver IDs `13` and `17` with persisted `Character.last_maneuver` state.
- Integrated the S09449 defender maneuver table into `domain/combat/resolution.py`, so evasion, parry, and shield calculations now scale off the defender's last maneuver rather than a flat bridge model.
- Expanded combat regression coverage for defensive stances and added a minimal parry-success XP bridge on top of the existing evasion defense-XP path; the broader S00509 armor/shield learning model remains a follow-on rather than silently implied.
- Added the DRG-024a post-penetration combat domain split across `domain/combat/hit_area.py`, `damage.py`, `armor.py`, `wounds.py`, and `cleanup.py`, then rewired `domain/combat/resolution.py` plus weapon and armor profiles so hit location, damage typing, armor reduction, wound application, and cleanup now flow through source-backed helpers instead of the old placeholder path.
- Added focused DRG-024a regression coverage for hit-area selection, raw damage shaping, armor reduction, wound application, cleanup handling, and the updated combat resolution expectations, then verified the combat slices continue to pass alongside the earlier verb and defense coverage.
- Added the in-band `spawndummy` and `combatreset` admin helpers, documented the structured browser sync path in `docs/architecture/client-state-sync.md`, and fixed Character-level dead-state recovery so live browser combat smoke can reset impaired sessions without shell-only recovery steps.
- Captured the DRG-LEARN-AUDIT findings in `tmp/drg-learn-audit-report.md`, confirming the repo already has real stat and pooled skill progression wiring while documenting the remaining canon blockers: no TDP loop, no sleep absorb behavior, incomplete S00509 defense-learning parity, and non-canonical `fieldexp/current/goal` semantics.