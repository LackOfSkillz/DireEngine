# DireEngine Cleric State Reference

Reference snapshot captured during DRG-CLERIC-00 to describe the actual Cleric-related state already present in the repo before DRG-CLERIC-01 planning.

## Baseline Triage Snapshot

- `pytest --collect-only tests/ -q` completed cleanly with `1012 tests collected in 5.02s`.
- A bounded full-suite probe ran for 90 seconds, reached roughly 6% progress, and timed out without reproducing a fast import, syntax, or collection blocker.
- Practical reading: the suite is not yet re-certified green end-to-end in this dispatch, but there is no immediate baseline blocker preventing targeted Cleric planning.

## Profession Identity State

- Cleric is already a registered profession in `world/professions/professions.py`.
- The current profession system is string-keyed, not numeric. Runtime identity is `"cleric"`, not a stored canon profession number.
- The Cleric profession profile already declares:
  - display name `Cleric`
  - primary skillset `magic`
  - secondary skillset `lore`
  - tertiary skillset `weapons`
  - guild tag `cleric_guildhall`
- `Character.at_object_creation()` initializes generic profession state through `db.profession`, `db.profession_rank`, and `db.circle`.
- `SmokeClericLive` currently exists as a real fixture with:
  - `profession = cleric`
  - `guild = cleric`
  - `circle = 10`
  - `profession_rank = 1`

## Mana Realm State

- `domain/mana/constants.py` already defines four named realms: `holy`, `life`, `elemental`, and `lunar`.
- `typeclasses/characters.py` already routes profession affinity by name. Cleric resolves to the `holy` realm.
- This means the codebase already has a live Holy realm concept, but it is represented by named string realms rather than the canon numeric framing in the new program scope.

## Spellbook And Spell Content State

- `SpellbookService` already exists and enforces profession eligibility, acquisition method, circle capture, and slot allocation.
- `commands/cmd_spellbook.py` already exposes `spells` and `spellbook` command surfaces.
- The current registry contains 21 total spells.
- 16 currently allow Cleric as an eligible profession.
- 7 currently use the `holy` mana realm.
- No currently registered spell IDs are in the canon `206xxx` Cleric range described in the new program scope.
- Current spell provenance values are limited to `gsl_2004` and `magic_3_0_design`.
- `SmokeClericLive` currently has raw spellbook entries for `gauge_flow` and `manifest_force` in `db.spellbook["known_spells"]`.

## Guild And Progression Infrastructure State

- Cleric guild infrastructure already exists in more than placeholder form.
- `world/areas/crossing/cleric_guild/build.py` builds a full Cleric guildhall package, not a single stub room.
- The guildhall locator test suite expects Cleric guild lookup to resolve to `Cleric Guild`.
- `typeclasses/npcs.py` already contains `ClericGuildmaster` with profession-specific inquiry text.
- `engine/services/circle_service.py` already includes Cleric-aware guild leader lookup and generic circle advancement projection/commit flow.
- Guild infrastructure across professions is still partial overall. Current tests indicate built guildhall locator entries for Cleric, Empath, and Ranger, while many other professions still return `None`.

## Existing Cleric-Specific Mechanics

- `typeclasses/characters.py` already contains a Cleric devotion subsystem.
- Current Cleric devotion state includes:
  - baseline/max devotion configuration
  - shrine regeneration hooks
  - per-ritual cooldown timestamps in `db.cleric_ritual_timestamps`
  - devotion spending and adjustment helpers
- `SmokeClericLive` currently shows live Cleric resource state with:
  - `devotion = 100`
  - `favor = 1`
  - `deaths_since_last_shrine = 0`
- Shrine interaction is already implemented through `pray_at_shrine()`.
- Cleric commune support already exists with named communes:
  - `solace`
  - `ward`
  - `vigil`
- Cleric corpse and resurrection-related mechanics already exist, including corpse preparation, memory preservation, and resurrection profile helpers.
- `typeclasses/characters.py` also already defines Cleric specialization vocabulary: `stabilizer`, `restorer`, and `binder`.
- `@wound` already exists as an admin/testing command and is relevant to future Cleric healing smoke.

## Fixture And World-State Notes

- `SmokeClericLive` currently sits in `Intake Chamber`, not inside a Cleric guildhall room and not inside a shrine room.
- The fixture still has devotion access because devotion is profession-gated, not room-gated.
- This means any future ritual or guild-guy smoke that assumes the fixture starts inside the Cleric guild will need explicit setup.

## Missing Or Mismatched Relative To The New Cleric Program Scope

- No SAF attribute or canon uncleanliness stage model was found.
- No deity registry or named deity alignment system was found.
- No evidence was found for a canon S00963-style staged ritual engine with explicit stage-one, stage-two, and stage-three ritual identity.
- No evidence was found for canon `UNCLEAN_CHECK` and `UNCLEAN_ADJUST` spellcasting gates.
- No canon `206xxx` Cleric spellbook is present yet.
- Existing Cleric ritual/devotion code is real, but it is not the same model as the newly scoped SAF-based canon implementation.

## Main Surprises

- Cleric is not starting from zero. The repo already has meaningful Cleric-specific runtime code.
- The biggest planning risk is not missing scaffolding; it is semantic overlap between existing devotion, commune, shrine, and resurrection systems and the newly scoped canon SAF/deity/ritual program.
- DRG-CLERIC-01 should be framed as a reconciliation dispatch, not a greenfield identity dispatch.

## Planning Implications For DRG-CLERIC-01

- First decide whether current devotion/favor/commune mechanics are temporary placeholders, reusable primitives, or systems that must be replaced.
- Treat the current Holy realm as existing-but-noncanonical in representation: the concept is present, the canon numbering model is not.
- Audit current spell access and guild interactions before adding new Cleric-specific learn/circle work, because generic spellbook and circle services already exist.
- Use `@wound` and the existing smoke fixtures when the program reaches healing and resurrection smoke, but do not assume `SmokeClericLive` begins in a Cleric-valid location.