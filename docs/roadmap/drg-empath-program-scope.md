# DRG-EMPATH - Class Completion Program Scope

**Type:** Program scope document, not a dispatch. Defines the full sequence of work to deliver a playable DireEngine Empath class under the post-Cleric `B` policy posture.
**Output:** A playable Empath class that preserves working DireEngine Empath identity where it already functions, adds missing canonical 2004-GSL Empath content where absent, and closes with live command-boundary and wound-transfer verification.
**Total estimated dispatches:** 9 after the audit closeout documented here
**Estimated session count:** 6-11 sessions depending on how much spell content is grouped per sub-book dispatch
**Sequencing:** Runs after DRG-EMPATH-AUDIT. Because the audit produced a Class II result, DRG-EMPATH-FOUNDATION-001 comes first.

---

## Purpose

Empath does not need a greenfield class build.

The audit established the following:

- DireEngine already has substantial Empath implementation: profession identity, Life routing, Empathy skill, a real guildhall, a guildmaster, a dedicated command surface, and a live wound-transfer loop.
- The class-identity mechanic was verified live: `touch`, `link`, `take`, and `mend self` produce a real patient-to-empath transfer cycle in `/play`.
- The guild progression layer is **not** ready to inherit the Cleric pattern unchanged: Merla currently refuses even present Empath spell rows because her `teach_spell(...)` seam is wired to the Cleric allowlist.
- The canonical 401-404 Empath spell inventory is mostly absent from the structured spell registry.

This roadmap therefore follows **Path B**:

- grandfather what already works
- repair the small but critical identity/guild seam mismatch up front
- then add missing canonical Empath content in a bounded sequence

---

## Definition of done

"Complete Empath" for this program now means:

1. Empath profession identity and Life routing are explicitly audited and tagged.
2. The wound-transfer loop is treated as the authoritative class-identity seam and is reconciled with spell/guild infrastructure.
3. Existing Empath-accessible spell rows are retagged correctly by provenance.
4. Missing canonical 401-404 Empath content is added with correct `gsl_2004` provenance.
5. Empath guild progression works through Merla, including live off-class spell refusal and live on-class learn success.
6. Empath closeout includes live command-boundary smoke and a live wound-transfer loop proof, not just fixture-level tests.

Out of scope for this program:

- replacing the whole wound-transfer system with a new design just because the current command/spell seam is mismatched
- rebuilding the Empath guildhall from scratch
- implementing Ranger spellbooks during Empath work
- rewriting the global magic/runtime infrastructure that already supports Empath abilities

---

## Controlling audit results

These findings from `docs/references/direngine-empath-canon-audit.md` control the sequence:

1. **Wound-transfer classification is II, not III.**
   The class identity exists and works live. This avoids a halt, but it also means one small foundation dispatch is required before content dispatches.

2. **Merla's teaching seam is broken for Empath.**
   Off-class refusal works, but current Empath rows (`empath_heal`, `regenerate`) are also refused. Guild progression cannot be treated as already solved.

3. **Empath circle remains custom and empathy-only.**
   It should be preserved during the early program, but the audit leaves its exact canon posture as `hybrid_design` rather than settled `gsl_2004`.

4. **Canonical 401-404 coverage is sparse.**
   Existing structured coverage is mostly `Heal` plus `Regenerate`; the rest of the core book remains a genuine content gap.

---

## Dispatch sequence

### Dispatch 1: DRG-EMPATH-FOUNDATION-001

Purpose:
- reconcile the class-identity loop with spell/guild infrastructure before normal program work begins

Scope:
- decide and document the authoritative relationship between:
  - command-driven wound transfer
  - current `Heal` spell row
  - canonical healing-book naming
- repair Merla's teach-spell seam so live Empath learning is possible
- preserve the live wound-transfer identity while making the supporting spell/guild layer coherent enough for later content work

Why first:
- this is the only way to turn the audit's Class II result into a stable base for the rest of the program

Estimated size:
- small-medium

### Dispatch 2: DRG-EMPATH-01

Purpose:
- profession audit-and-tag, analogous to DRG-CLERIC-01

Scope:
- verify string-key Empath identity
- verify Life routing and any obvious profession metadata gaps
- audit/tag Empath-specific runtime identity as `directengine_canon`, `gsl_2004`, or `hybrid_design` where appropriate
- preserve the custom Empath circle path while documenting its current status explicitly

Estimated size:
- small

### Dispatch 3: DRG-EMPATH-02

Purpose:
- spell registry provenance cleanup, analogous to DRG-CLERIC-02

Scope:
- audit every Empath-accessible row in `domain/spells/spell_definitions.py`
- separate class-specific Empath coverage from shared fundamentals and the approved Analogous Patterns exceptions
- retag rows so canonical claims are explicit rather than inherited from defaults
- document which current rows stay `directengine_canon`, which are `gsl_2004`, and which are `hybrid_design`

Estimated size:
- small-medium

### Dispatch 4: DRG-EMPATH-03

Purpose:
- world and guildhall audit, analogous to DRG-CLERIC-03

Scope:
- preserve the existing Empath guildhall build as `directengine_canon`
- audit Merla, training rooms, infirmary/recovery spaces, and any join/tutorial scaffolding
- fill only obvious world-content gaps that block the class gameplay loop

Estimated size:
- small

### Dispatch 5: DRG-EMPATH-04

Purpose:
- canonical Healing book implementation

Scope:
- add or reconcile `Vitality Healing`, `Heal Wounds`, `Heal Scars`, and `Heal`
- route them through the now-reconciled wound-transfer / healing seam from FOUNDATION-001
- resolve naming conflicts such as current `Heal` versus older `External Wound Healing` / `Internal Wound Healing` language

Estimated size:
- medium

### Dispatch 6: DRG-EMPATH-05

Purpose:
- canonical Cleansing and Vitality books combined

Scope:
- add `Flush Poisons`
- add `Cure Disease`
- add `Refresh`
- add `Raise Power`
- add `Gift of Life`

Why combined:
- these five spells are a bounded mid-program bundle and fit together mechanically around restoration / cleansing identity

Estimated size:
- medium-large

### Dispatch 7: DRG-EMPATH-06

Purpose:
- canonical Protection book

Scope:
- add `Innocence`
- add `Zone of Protection`
- verify Ranger-only adjacent protection/animal content remains out of Empath scope

Estimated size:
- medium

### Dispatch 8: DRG-EMPATH-07

Purpose:
- Empath guild progression completion

Scope:
- finish Empath-specific learning flow through Merla
- add any needed Empath tier / circle / apprentice access handling not already covered by the shared infrastructure
- verify live on-class learning works and live off-class refusal still holds

Estimated size:
- medium

### Dispatch 9: DRG-EMPATH-08

Purpose:
- Empath program closeout, analogous to DRG-CLERIC-10

Scope:
- run the full live smoke matrix
- prove wound-transfer end-to-end again on the final shipped class
- verify command-level class boundaries against Cleric and other off-class spell surfaces
- update docs, memory, and policy notes for the next class program

Estimated size:
- small-medium

---

## Why the count is 9

Without the Class II finding, Empath would likely have fit a normal 8-dispatch Cleric-like pattern.

The extra dispatch is required because:
- the class identity exists already
- but the spell/guild seam around that identity is not coherent enough yet

That is exactly the kind of bounded, high-leverage fix the Path B posture is meant to surface early.

---

## Sequencing rationale

The sequence is intentionally front-loaded toward coherence rather than raw spell count.

Why this order works:

1. Fix the identity/guild seam before adding more spell rows.
2. Lock provenance and profession/world audit early so later spell additions are not built on ambiguous policy.
3. Ship healing first, because healing is the canonical Empath heart and the most likely place where naming/mechanics conflicts appear.
4. Leave closeout until after Merla and the live class boundary are both real, not assumed.

---

## Recommended next step

Recommended immediate next dispatch:
- **DRG-EMPATH-FOUNDATION-001**

Recommended dispatch after that:
- **DRG-EMPATH-01**

Reason:
- the audit did not halt
- but Merla's current teach-spell seam and the mismatch between wound-transfer gameplay and structured healing rows make a straight jump to normal content work premature