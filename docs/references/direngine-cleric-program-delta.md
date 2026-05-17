# DireEngine Cleric Program Delta

## Program scope delta (as of 2026-05-14)

### Summary

- (a) Already done: 0 dispatches
- (b) Partial: 7 dispatches
- (c) Untouched: 1 dispatch
- (d) Conflict: 7 dispatches

### Canon alignment summary (for a/b dispatches)

- Canon-aligned: 0
- Provenance-unknown: 6
- Non-canon: 1

### Per-dispatch classification

#### DRG-CLERIC-01: Profession identity + Holy mana realm

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** Cleric already exists as a string-keyed profession profile in `world/professions/professions.py:74-82`, and `Character.get_profession_mana_realm()` maps Cleric to `holy` in `typeclasses/characters.py:13228-13236`.
- **Conflict:** The existing implementation already carries the concept, but it uses string profession and realm identifiers rather than the program scope's canon numeric framing (`profession 3`, `realm 2`), so DRG-CLERIC-01 cannot be treated as a greenfield identity dispatch.

#### DRG-CLERIC-02: SAF attribute foundation

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** Cleric resource state is currently modeled through `CLERIC_DEVOTION_CONFIG` and `get_devotion()` / `set_devotion()` in `typeclasses/characters.py:933-960` and `typeclasses/characters.py:3254-3299`.
- **Conflict:** The repo already has a devotion-based persistent Cleric resource model, but it is not SAF, does not expose 100M stage thresholds, and would have to be replaced or explicitly bridged to the canon uncleanliness system.

#### DRG-CLERIC-03: Deity registry

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** `Character.commune_with_divine()` already exists in `typeclasses/characters.py:4017-4065`, but it recognizes `solace`, `ward`, and `vigil` through `get_commune_profile()` at `typeclasses/characters.py:3971-3974`, not deity alignment.
- **Conflict:** The `commune` seam is already occupied by non-deity effect abilities, so a canon deity registry cannot be added exactly as scoped without reconciling command meaning, stored state, and downstream call sites.

#### DRG-CLERIC-04: Ritual stage engine + cooldown handling

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** Existing ritual handling lives in `get_cleric_ritual_profile()`, `get_cleric_ritual_cooldown_remaining()`, and `perform_cleric_ritual()` at `typeclasses/characters.py:3938-3969`, and live corpse-ritual chains are exercised in `diretest.py:7870-7950`.
- **Conflict:** There is already Cleric ritual and cooldown logic, but it is built around devotion rites and corpse-stage actions rather than the canon S00963 stage-one/stage-two/stage-three ritual engine with SAF rewards and deity gates.

#### DRG-CLERIC-05: Starter ritual world content

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** A substantial Cleric guild area already exists in `world/areas/crossing/cleric_guild/build.py:1-280`, including a `chapel` room whose description references an altar in `world/areas/crossing/cleric_guild/build.py:72-79`; generic shrine behavior already exists through `Character.is_in_shrine()` / `pray_at_shrine()` in `typeclasses/characters.py:3201-3252`.
- **Gaps:**
- No explicit altar object or altar interaction verbs (`kiss`, `pour`, `wash`) were found.
- No holy water item or sprinkle-path support was found.
- No room-script ritual hooks for `dance` or `poem` were found.
- No evidence was found that the Cleric guild rooms are currently marked as shrine rooms by default.

#### DRG-CLERIC-06: First three canonical rituals

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** `perform_cleric_ritual()` only exposes `prayer`, `focus`, and `devotion` via `CLERIC_DEVOTION_CONFIG["rituals"]` in `typeclasses/characters.py:933-955` and `typeclasses/characters.py:3956-3969`.
- **Conflict:** The existing rite vocabulary is not the canon kiss/pour/sprinkle ritual set, and the current system regenerates devotion/favor instead of reducing SAF through canonical ritual actions.

#### DRG-CLERIC-07: UNCLEAN_CHECK and UNCLEAN_ADJUST integration

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** Cleric spell power currently scales through `get_devotion_effect_multiplier()` in `typeclasses/characters.py:13237-13243`, and resurrection / commune logic consumes or checks devotion in `typeclasses/characters.py:4017-4065` and `typeclasses/characters.py:5092-5124`.
- **Conflict:** The current magic seam is a positive devotion-based modifier, not a canon uncleanliness gate; there is no stage-4 cast block, no DI-at-stage-1 block, and no `$UNCLEAN_CHECK` / `$UNCLEAN_ADJUST` equivalent.

#### DRG-CLERIC-08: Blessings & Buffs sub-book

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** The registry already contains holy/cleric-adjacent spell content such as `shielding` (`domain/spells/spell_definitions.py:126-137`) and `shared_guard` (`domain/spells/spell_definitions.py:367-379`), and runtime spell coverage exists in `tests/services/test_character_spell_runtime.py:444-496`.
- **Gaps:**
- No canon `206xxx` buff roster such as Glythtide's Gift or Ring of Blessings is present.
- Existing buffs are mixed between generic `Fundamentals` spells and prototype holy spells rather than a canonical Cleric sub-book.
- No evidence was found for a DI/buff separation model matching the scoped canon plan.

#### DRG-CLERIC-09: Wards & Defensive sub-book

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** `minor_barrier` is a Cleric-only holy ward in `domain/spells/spell_definitions.py:109-121`, and `minor_barrier` / `shared_guard` are covered by runtime and effect tests in `tests/services/test_character_spell_runtime.py:166-248` and `tests/services/test_spell_effect_service.py:256-324`.
- **Gaps:**
- The ward roster does not match the scoped canonical lineup such as Halo or Soul Ward.
- Existing ward spells are partly generic cross-profession spells rather than a dedicated canonical Cleric defensive book.
- No canon audit has confirmed that the current holy warding spells correspond to 2004-GSL Cleric content.

#### DRG-CLERIC-10: Healing sub-book

- **Classification:** b
- **Canon alignment:** non-canon
- **Evidence:** `cleric_minor_heal` exists in `domain/spells/spell_definitions.py:69-81`, and the current healing pipeline is exercised in `tests/services/test_character_spell_runtime.py:135-139` and `tests/services/test_structured_spell_pipeline.py:178-199`.
- **Gaps:**
- No canonical Cleric healing roster such as Rejuvenation or Mass Rejuvenation is present.
- The current healing path is generic HP restoration, not canon-specific wound or spirit handling.
- No evidence was found for wound-targeted Cleric healing behavior tied to the current wound system.

#### DRG-CLERIC-11: Divine Intervention sub-book

- **Classification:** c
- **Canon alignment:** n/a
- **Evidence:** The current registry includes holy offensive and debilitation spells such as `radiant_burst` and `slow` in `domain/spells/spell_definitions.py:182-194` and `domain/spells/spell_definitions.py:262-280`, but no spell IDs in the canon `206xxx` DI set and no DI-specific flagging or gating seam were found.

#### DRG-CLERIC-12: Utility sub-book

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** `cleanse` already exists as a holy utility spell in `domain/spells/spell_definitions.py:407-423`, with structured runtime coverage in `tests/services/test_character_spell_runtime.py:482-496` and `tests/services/test_spell_effect_service.py:413-423`.
- **Gaps:**
- No canonical utility lineup such as Revelation, Abeyance, or Mass Persistence of Memory is present.
- Existing utility content is mostly generic prototype magic rather than an identified Cleric utility sub-book.
- No evidence was found for deity, memory, or doctrinal utility behaviors from the scoped canon list.

#### DRG-CLERIC-13: Cleric Guild Guy / learning path

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** `ClericGuildmaster` already exists in `typeclasses/npcs.py:741-770`, the Cleric guildhall is registered in `tests/learning/test_guildhall_locator.py:12-21`, and generic learning/circle infrastructure already exists in `engine/services/spellbook_service.py:52-118` and `engine/services/circle_service.py:35-193`.
- **Gaps:**
- No S00465-style Cleric-specific `learn <spell>` dialogue or guild-guy teaching surface was found.
- Circle advancement requirements are still placeholder values in `engine/services/circle_service.py:19-24`.
- No dedicated newbie-introduction or Cleric spell-learning progression script was found.

#### DRG-CLERIC-14: Additional canonical rituals

- **Classification:** d
- **Canon alignment:** n/a
- **Evidence:** The existing ritual model already commits to devotion rites (`prayer`, `focus`, `devotion`) and corpse-stage rites in `typeclasses/characters.py:3938-3969` and `diretest.py:7870-8190`.
- **Conflict:** Additional canonical rituals cannot just be layered onto the current system as-written because the existing ritual vocabulary, reward model, and stored cooldown/state semantics are already tied to a different devotion/corpse design.

#### DRG-CLERIC-15: Cleric program closeout + comprehensive smoke

- **Classification:** b
- **Canon alignment:** provenance-unknown
- **Evidence:** There is already meaningful Cleric smoke around revive and devotion flows in `diretest.py:7912-8190`, and spell runtime coverage exists for current holy spells in `tests/services/test_character_spell_runtime.py:135-496` and `tests/services/test_structured_spell_pipeline.py:178-439`.
- **Gaps:**
- No end-to-end smoke exists for SAF accumulation/reduction, deity commune, or uncleanliness-based casting penalties.
- No comprehensive smoke covers all five planned Cleric sub-books.
- No closeout artifact yet verifies a canon Cleric gameplay loop from creation through ritual recovery and deity alignment.

### Highest-impact findings

- The program scope is not overestimating missing infrastructure; it is underestimating existing conflicting infrastructure. The biggest risk is duplication, not absence.
- The current Cleric core is organized around devotion, commune abilities, corpse rituals, and resurrection quality, not SAF, deity alignment, and S00963 ritual stages.
- Later spellbook dispatches are not blank, but the current roster is a prototype mix of holy Cleric spells, shared cross-profession spells, and Magic 3.0-era content rather than a canon `206xxx` Cleric library.
- Guild and world scaffolding already exist, so DRG-CLERIC-13 and DRG-CLERIC-05 should be treated as gap-closing passes rather than first implementations.
- DRG-CLERIC-01 through DRG-CLERIC-07 are tightly coupled by schema conflict; changing one without first deciding how to reconcile devotion vs. SAF and commune vs. deity alignment would create parallel Cleric systems.