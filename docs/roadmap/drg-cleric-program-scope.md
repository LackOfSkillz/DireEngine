# DRG-CLERIC - Class Completion Program Scope

**Type:** Program scope document, not a dispatch. Defines the full sequence of work to deliver a playable DireEngine Cleric class under hybrid-leaning-grandfather canon authority. Each numbered item below is a separate dispatch that will be drafted and shipped one at a time with strict closure discipline.
**Output:** A playable Cleric class that preserves working DireEngine Cleric systems as project canon, adds missing canonical 2004-GSL Cleric content where absent, and closes with smoke-verified end-to-end behavior plus a class-boundary policy review.
**Total estimated dispatches:** 8, with 1 optional follow-up dispatch if closeout smoke surfaces a bounded extra slice
**Total estimated session count:** 5-10 sessions depending on spell dispatch size and whether the optional follow-up is needed
**Sequencing:** Runs after DRG-CLERIC-00, DRG-CLERIC-00-DELTA, DRG-CANON-AUDIT-002, and DRG-CANON-POLICY-001. Replaces the original 15-dispatch greenfield Cleric roadmap.

---

## Purpose

The original Cleric roadmap assumed a largely empty class surface and aimed to build a canonical 2004-GSL Cleric from scratch. Subsequent discovery and policy work invalidated that assumption.

The following are now established:

- DRG-CLERIC-00 documented that DireEngine already has substantial Cleric implementation: profession identity, Holy routing, guildhall scaffolding, guildmaster presence, devotion, commune, shrine interactions, corpse rites, resurrection hooks, and Cleric-facing runtime/tests.
- DRG-CLERIC-00-DELTA classified the original 15-dispatch roadmap as 7 conflicts, 7 partials, 1 untouched, and 0 already-done dispatches.
- DRG-CANON-AUDIT-002 found that most existing Cleric systems are DireEngine-bespoke or Elanthipedia-era inspired rather than clean 2004-GSL reproductions.
- DRG-CANON-POLICY-001 set the controlling policy: grandfather working class systems as `directengine_canon`, add missing canonical 2004-GSL content as `gsl_2004`, and use `hybrid_design` only for deliberate bridge cases.

This roadmap therefore no longer tries to replace devotion with SAF, repurpose `commune` into a deity-alignment command, or rebuild the ritual layer around S00963 staging. Instead it preserves working DireEngine Cleric systems and concentrates implementation effort on missing canonical spellbook, guild, provenance, and closeout coverage.

---

## Definition of done

"Complete Cleric" for this program now means:

1. **Profession identity and Holy routing are verified complete.** Cleric remains the working DireEngine profession identity, and Holy routing is confirmed end-to-end with any obvious gaps closed.
2. **Existing Cleric piety and ritual systems are project-canonical.** Devotion, commune, shrine behavior, ritual handling, resurrection hooks, and related tests are explicitly treated as `directengine_canon` rather than replacement targets.
3. **Cleric spell provenance is corrected.** Existing Cleric-facing spell rows no longer imply false `gsl_2004` authority, and provenance expectations are aligned in tests and documentation.
4. **Canonical 206xxx Cleric spell content exists alongside inherited DireEngine Cleric content.** Missing 2004-GSL Cleric spells are added with correct `gsl_2004` provenance and integrated into the live spell pipeline.
5. **Cleric world scaffolding is complete enough to support the shipped class.** Shrines and other sacred-object world seams are audited, and any obvious content gaps blocking the Cleric gameplay loop are filled.
6. **Cleric guild progression is complete enough to support a playable class.** The existing guildhall and guildmaster scaffolding is extended with Cleric-specific learn-spell flow, circle progression, and basic guild dialogue where still missing.
7. **Smoke verification matches the grandfather-plus-canonical-additions model.** A Cleric fixture can use existing DireEngine Cleric systems and also exercise the new canonical spellbook additions end-to-end.
8. **Policy revisit checkpoint is executed.** At program closeout, Cleric gameplay is assessed explicitly so Empath planning inherits a documented judgment, not just a default.

Out of scope for this program (deferred to future work):

- replacing devotion with SAF or introducing S00963 uncleanliness stages
- a formal deity registry unless a concrete gameplay need surfaces during implementation
- replacing the current ritual engine with stage-one/stage-two/stage-three ritual machinery
- quest-locked or high-circle Cleric content beyond the targeted canonical starter/intermediate spell additions
- large-scale rework of the repo-wide death pipeline just because Cleric hooks already exist inside it

---

## Authority references established

This roadmap is controlled by both canon-source references and project-policy references.

### Project-policy references

- [docs/references/direngine-cleric-state.md](c:/Users/gary/dragonsire/docs/references/direngine-cleric-state.md) - current repo reality for Cleric before implementation planning
- [docs/references/direngine-cleric-program-delta.md](c:/Users/gary/dragonsire/docs/references/direngine-cleric-program-delta.md) - original 15-dispatch classification against repo reality
- [docs/references/direngine-cleric-canon-audit.md](c:/Users/gary/dragonsire/docs/references/direngine-cleric-canon-audit.md) - provenance audit plus per-system Cleric policy decisions
- [docs/references/direngine-class-canon-policy.md](c:/Users/gary/dragonsire/docs/references/direngine-class-canon-policy.md) - class-wide hybrid-leaning-grandfather canon authority policy

### Canon-source references that still matter in the rewritten program

- **Profession number:** 3 (still relevant as canon metadata even though the runtime uses string profession identity)
- **Mana realm:** Holy = realm 2 (still relevant as canon metadata and spell provenance context)
- **Spell ID range:** 206xxx (the main missing canonical Cleric content surface)
- **Cleric guild:** S00465 / S00466 / S00464 (still relevant because guild scaffolding exists but canonical learning/progression depth is incomplete)
- **Canonical spell roster sources:** S04463, S07085, S07081, S07118, S11205, S09118, S09117, S09120, S11895 and adjacent verified Cleric spell scripts from DireLore

### Canon-source references explicitly not used as replacement mandates in this roadmap

- S00963 SAF / ritual stage model
- `$UNCLEAN_CHECK` / `$UNCLEAN_ADJUST` as replacement gates for the current devotion-based magic seam
- deity-alignment rewrite of the current `commune` command

These remain useful comparative references, but DRG-CANON-POLICY-001 removed them as default implementation targets for Cleric.

---

## Original-to-new conversion summary

The original roadmap had 15 dispatches. Their conversion under the new policy is:

- **REMOVE:** 5
- **KEEP:** 6
- **REDUCE:** 3
- **REPLACE:** 1
- **NEW dispatches added from audit/policy findings:** 2

### Conversion detail

#### DRG-CLERIC-01 - Profession identity + Holy mana realm

- **Operation:** REDUCE
- **Result in new roadmap:** becomes a completeness audit and gap-closure pass, not a greenfield identity build

#### DRG-CLERIC-02 - SAF attribute foundation

- **Operation:** REMOVE
- **Reason:** devotion is grandfathered as the Cleric piety seam

#### DRG-CLERIC-03 - Deity registry

- **Operation:** REPLACE
- **Result in new roadmap:** the old concept is retired as a default deliverable; existing divinity/commune framing is treated as `directengine_canon`, and a formal deity registry is deferred unless later gameplay demands it

#### DRG-CLERIC-04 - Ritual stage engine + cooldown handling

- **Operation:** REMOVE
- **Reason:** existing ritual model is grandfathered

#### DRG-CLERIC-05 - Starter ritual world content

- **Operation:** REDUCE
- **Result in new roadmap:** becomes a small Cleric world-content audit for shrines, altars, and sacred objects rather than a first implementation of ritual-world support

#### DRG-CLERIC-06 - First three canonical rituals

- **Operation:** REMOVE
- **Reason:** the canonical ritual-stage path is no longer the Cleric default

#### DRG-CLERIC-07 - UNCLEAN_CHECK / UNCLEAN_ADJUST integration

- **Operation:** REMOVE
- **Reason:** devotion's existing positive modifier role is grandfathered as the project-canonical Cleric piety-to-magic seam

#### DRG-CLERIC-08 - Blessings & Buffs sub-book

- **Operation:** KEEP
- **Result in new roadmap:** still ships as canonical `gsl_2004` spell content added into the current spell pipeline

#### DRG-CLERIC-09 - Wards & Defensive sub-book

- **Operation:** KEEP, then combined
- **Result in new roadmap:** combined with Healing for efficiency after the first canonical spellbook dispatch establishes the pattern

#### DRG-CLERIC-10 - Healing sub-book

- **Operation:** KEEP, then combined
- **Result in new roadmap:** combined with Wards

#### DRG-CLERIC-11 - Divine Intervention sub-book

- **Operation:** REDUCE, then combined
- **Result in new roadmap:** spells stay; uncleanliness-gating requirement is removed; combined with Utility

#### DRG-CLERIC-12 - Utility sub-book

- **Operation:** KEEP, then combined
- **Result in new roadmap:** combined with DI

#### DRG-CLERIC-13 - Cleric Guild Guy / learning path

- **Operation:** KEEP, rescope
- **Result in new roadmap:** finishes Cleric-specific progression on top of the existing guildhall/guildmaster scaffolding

#### DRG-CLERIC-14 - Additional canonical rituals

- **Operation:** REMOVE
- **Reason:** additional ritual expansion is no longer a separate Cleric program deliverable under the grandfather policy

#### DRG-CLERIC-15 - Program closeout + comprehensive smoke

- **Operation:** KEEP, rescope
- **Result in new roadmap:** smoke and closeout now validate the grandfather-plus-canonical-additions model and execute the class-boundary policy review

### Audit/policy-surfaced additions

- **NEW:** spell registry provenance cleanup
- **NEW:** Cleric world-content audit

---

## Dispatch sequence

The rewritten Cleric program is ordered to close risk early and avoid reopening grandfathered systems unnecessarily.

### Foundation and cleanup (dispatches 1-3)

These dispatches validate and normalize the inherited Cleric surface before canonical content expansion begins.

**DRG-CLERIC-01: Profession identity + Holy realm completeness audit**
- Verify Cleric profession registration is complete end-to-end under the current string-keyed runtime model
- Verify Holy routing is correct through profession assignment, spell preparation/casting, state sync, and tests
- Add or document canonical metadata where useful without forcing a numeric-only identity rewrite
- Close any obvious compatibility gaps surfaced by the audit
- Provenance outcome: existing identity/routing remains `directengine_canon`
- Tests/smoke: focused identity and Holy-routing checks only
- Prerequisites: DRG-CANON-POLICY-001, rewritten roadmap landed
- Estimated size: small

**DRG-CLERIC-02: Spell registry provenance cleanup**
- Audit existing Cleric-facing spell rows in `domain/spells/spell_definitions.py`
- Retag kept bespoke Cleric spells as `directengine_canon` where appropriate instead of inheriting false `gsl_2004` assumptions
- Preserve the standing four-spell Magic 3.0 exception policy where relevant
- Update tests to assert the corrected provenance model rather than the prior implicit default
- This dispatch closes the audit's category-(e) GSL-mismatched finding before more Cleric spell content is added
- Prerequisites: DRG-CLERIC-01
- Estimated size: small-medium

**DRG-CLERIC-03: Cleric world content audit (shrines, altars, sacred objects)**
- Audit existing shrine rooms, altar/sacred-object presence, and any obvious missing world hooks that block the shipped Cleric gameplay loop
- Preserve working shrine behavior as `directengine_canon`
- Fill only clear, bounded world-content gaps needed for the current program
- If findings are trivial, this may stay small enough to fold into a later dispatch, but it should be drafted as a standalone pass first
- Prerequisites: DRG-CLERIC-01
- Estimated size: small

### Canonical spellbook additions (dispatches 4-6)

These dispatches add missing `gsl_2004` Cleric spell content into the current spell pipeline without replacing inherited Cleric runtime behavior.

**DRG-CLERIC-04: Canonical Blessings & Buffs sub-book (206xxx)**
- Add the first 4-5 canonical Cleric buff spells from the 206xxx surface
- Tag new canonical entries `gsl_2004`
- Use the current structured spell pipeline, effect system, messaging model, and Holy routing rather than inventing a parallel Cleric-only cast path
- Decide spell-by-spell coexistence with inherited Cleric-facing buff rows instead of wholesale replacing them
- Smoke surface: prepare, cast, apply, expire, and three-audience messaging
- Prerequisites: DRG-CLERIC-02
- Estimated size: medium

**DRG-CLERIC-05: Canonical Wards & Healing sub-books (combined)**
- Add the next 6-7 canonical Cleric spells across ward and healing roles
- Reuse the DRG-CLERIC-04 content pattern to reduce dispatch overhead
- Preserve working inherited healing and ward behavior where it already serves gameplay, but add the missing canonical roster explicitly
- Smoke surface: defensive effects and healing effects resolve correctly under the current live engine
- Prerequisites: DRG-CLERIC-04
- Estimated size: medium-large, but still intended to fit one implementation slice; if Step 0 finds this is too large, it must be split before execution

**DRG-CLERIC-06: Canonical DI & Utility sub-books (combined)**
- Add the next 6-8 canonical Cleric spells across Divine Intervention and utility roles
- Do not add S00963 uncleanliness gating as a prerequisite for these spells
- Integrate the new spells with the inherited devotion/Holy seam and current effect pipeline
- Mark any truly deliberate post-DR3 presentation bridge as `hybrid_design`; otherwise canonical additions stay `gsl_2004`
- Smoke surface: varied utility effects plus DI-like spell behavior resolve cleanly in the live model
- Prerequisites: DRG-CLERIC-05
- Estimated size: medium-large, with the same Step 0 split-if-too-big rule as DRG-CLERIC-05

### Progression and closeout (dispatches 7-8)

**DRG-CLERIC-07: Cleric guild progression completion**
- Finish Cleric-specific spell learning flow through the existing `ClericGuildmaster`
- Fill the Cleric-specific parts of circle advancement and baseline guild dialogue that are still placeholder/generic today
- Preserve the existing guildhall and guildmaster scaffolding as `directengine_canon`
- Add canonical guild behavior where the class currently lacks it entirely
- Smoke surface: basic learn-spell path, progression gate, and guild interaction loop
- Prerequisites: DRG-CLERIC-06
- Estimated size: medium

**DRG-CLERIC-08: Cleric program closeout + comprehensive smoke**
- Run the end-to-end Cleric smoke matrix for the grandfather-plus-canonical-additions model
- Verify a playable loop that includes inherited Cleric class systems plus the new canonical spellbook content
- Update CHANGELOG, AS_BUILT, and repo memory with Cleric closure facts
- Execute the class-boundary revisit checkpoint required by DRG-CANON-POLICY-001: did grandfathering the existing Cleric core produce acceptable gameplay?
- If the answer is yes, record that as input for Empath planning; if no, record the adjustment needed before Empath scope is drafted
- Prerequisites: DRG-CLERIC-07
- Estimated size: small-medium

**Optional DRG-CLERIC-09: Post-closeout bounded follow-up**
- Reserved only if DRG-CLERIC-08 smoke surfaces one additional bounded slice worth shipping before the Cleric program is considered done
- This is not a default dispatch and should remain unused unless closeout evidence justifies it

---

## Reusable patterns for Empath / Ranger / Thief programs

This rewritten Cleric program establishes a different reusable pattern from the original greenfield roadmap.

**Reusable as-is:**
- class audit first, then scope draft
- grandfather working class systems as `directengine_canon`
- add missing canonical 2004-GSL content where absent rather than replacing working systems
- perform provenance cleanup before large content expansion if inherited registry/data rows imply false authority
- keep class closeout as both smoke verification and class-boundary policy review

**Reusable with modification:**
- canonical spellbook expansion pattern (spell roster and interaction mix differ by class)
- guild progression completion pattern (existing scaffolding differs by class)
- world-content audit pattern (use only when the class has meaningful location/item hooks)

**Class-specific and not assumed reusable:**
- devotion/commune/shrine/resurrection model
- Cleric-specific spell coexistence decisions between inherited rows and canonical additions
- Holy-routing details and Cleric death-support integration

The reusable question for later classes is now: "what already works and should be grandfathered?" not "how do we rebuild the class from raw GSL?"

---

## Process notes

**Dispatch tempo.** Each dispatch should still fit within 1-2 sessions including Step 0, implementation, and validation. If DRG-CLERIC-05 or DRG-CLERIC-06 cannot realistically close in one bounded slice, they must be split at draft time rather than allowed to sprawl.

**Step 0 discipline.** Each dispatch begins with a Step 0 that includes:
- verify prior dispatches in the program closed cleanly
- verify prerequisites are present
- check whether the target surface is inherited `directengine_canon`, missing `gsl_2004`, or a deliberate `hybrid_design` case
- identify any conflict between new canonical additions and grandfathered Cleric behavior before editing code

**Strict closure.** Same rules as the maintenance group: a dispatch does not close until smoke or tests prove the new or clarified functionality works end-to-end. Documentation-only closure is valid only for documentation dispatches.

**Pause points.** Natural pause points where the program can rest without leaving the codebase in a broken state:
- after DRG-CLERIC-02: inherited Cleric surface is normalized and provenance is no longer ambiguous
- after DRG-CLERIC-04: the first canonical Cleric spellbook slice has landed cleanly in the live pipeline
- after DRG-CLERIC-06: the canonical spellbook expansion is materially complete
- after DRG-CLERIC-08: program complete, policy revisit recorded

**Risk areas.** The dispatches most likely to expand scope or surface unexpected issues:
- DRG-CLERIC-02: provenance cleanup may reveal more inherited spell rows tied to wrong authority assumptions than expected
- DRG-CLERIC-05: combined Wards + Healing may prove too large if healing behavior needs more engine adaptation than expected
- DRG-CLERIC-06: combined DI + Utility may reveal hidden gating assumptions or effect-surface gaps
- DRG-CLERIC-08: closeout smoke has the widest integration surface and is the policy-review checkpoint

**Revisit rule.** Cleric is the first class under hybrid-leaning-grandfather. Its closeout is not only a feature milestone but also the evidence base for whether Empath should inherit the same default unchanged.

---

## Next step

Draft **DRG-CLERIC-01** against this rewritten roadmap.

That dispatch is no longer a greenfield identity build. It is a bounded completeness audit and gap-closure pass over the already-live Cleric profession identity and Holy routing seams, with explicit provenance framing under DRG-CANON-POLICY-001.