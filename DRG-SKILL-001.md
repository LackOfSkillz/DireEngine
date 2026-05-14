# DRG-SKILL-001 — Engine Skill Identity Migration

**Type:** Targeted alignment dispatch — closes the identity drift between SKILL_REGISTRY, SKILL_ALIASES, and SKILL_GROUPS; adds the defense skills LEARN-006 requires; adds `display_name` field across the registry; resolves group 9 placement
**Output:** Defense skills (`shield_usage`, `parry_ability`, `multiple_engaged_opponent`) added as proper registry entries; pulse group references aligned with registry (weapon-merge IDs unchanged, defense IDs newly resolved, survival/magic case-by-case); `display_name` field added to every registry entry; group 9 cleared back to profession-reserved empty state; cross-module alignment regression test added
**Estimated touch:** ~10-14 modified/new files, ~800-1200 LOC including tests
**Sequencing:** First DireEngine dispatch after LEARN-004 ships. After this dispatch, LEARN-006 (defense XP canon parity) is unblocked, the canonical pulse runtime no longer silently skips 32 skill_ids, the LEARN arc has clean identity infrastructure, and future profession dispatches inherit a clean group-9 surface to populate.

---

## Provenance note

DRG-SKILL-001-AUDIT findings:

- **SKILL_REGISTRY** in `typeclasses/characters.py` contains 38 entries with format `lowercase_with_underscores`. Fields: `category`, `visibility`, `description`, `starter_rank`, optional `guilds`. **No `display_name` field.**
- **SKILL_ALIASES** in `domain/learning/skill_aliases.py` is internally clean against the registry (zero alias targets reference non-existent keys), but bridges defense skills to combat (`parry` -> `combat`, `shield` -> `combat`) as a placeholder.
- **CANONICAL_PULSE_GROUPS** in `domain/learning/skill_groups.py` defines 63 distinct `skill_id` references; **32 of those don't exist in SKILL_REGISTRY.** Pulse silently no-ops for those 32 IDs.
- **Group 9** ("Guild-Only") is currently populated with `performance`, `tactics`, `astrology`, `backstab`, `bardic_lore`, `conviction`, `empathy`, `expertise`, `instinct`, `summoning`, `thanatology`, `theurgy`, `trading`. LEARN-003a's design intent was to reserve group 9 empty for profession-specific skills; current state contradicts intent.
- **S00209 canonical comparison:** SKILL_REGISTRY has 38 entries; S00209 has 63 trainable canonical skills; 50 canonical skills missing from registry; 25 registry entries don't appear in S00209 (merged abstractions, modernized names, or homegrown DireEngine concepts).

**Strategic decisions locked from pre-flight discussion:**

1. **Targeted alignment scope (Option C).** Don't decide canonical-vs-merged for weapons (e.g., keep `light_edge` rather than splitting into `small_edged`/`large_edged`/`twohanded_edged`). That's a deeper vocabulary question best resolved when profession dispatches surface a forcing function. DRG-SKILL-001 just makes existing references consistent.

2. **Add defense skills as proper registry entries.** `shield_usage`, `parry_ability`, `multiple_engaged_opponent` become first-class identities. LEARN-006 needs them; the audit found pulse groups already reference them. Removing the SKILL_ALIASES bridge to `combat` for parry/shield is part of this.

3. **Fix pulse group references via middle path.** For each missing skill_id in CANONICAL_PULSE_GROUPS:
   - **Defense:** ADD to registry (becomes first-class)
   - **Weapon canonical splits** (`small_edged`, `large_edged`, etc.): REPLACE in pulse groups with merged registry keys (`light_edge`, `heavy_edge`)
   - **Survival/magic:** Case-by-case based on whether DireEngine intends to support the skill

4. **Group 9 reserved for profession-only skills.** Move non-profession skills from current group 9 contents to appropriate canonical groups (0-8). Move profession-specific skills to a "profession-deferred" state — registered but not in any pulse group until their profession dispatch arrives. Group 9 ends as empty/reserved.

5. **`display_name` field from canonical S00209 where applicable, DireEngine-native where not.** For skills matching canonical names: use canonical display (e.g., `shield_usage` -> "Shield Usage"). For merged abstractions: use DireEngine-native (e.g., `light_edge` -> "Light Edged Weapons" since it represents the merged category).

**This dispatch unblocks:**

- **LEARN-006** (defense XP canon parity) — requires `shield_usage` and `parry_ability` as proper skills with their own learning state
- **Future profession dispatches** (DRG-025+) — inherit a clean group 9 reserved for their profession-specific skills
- **Future pulse work** — every skill_id in pulse groups will resolve to a real registry entry, ending the silent no-op coverage gap

---

## Background

Three identity surfaces drifted apart over LEARN dispatches:

| When | Surface | What landed |
|---|---|---|
| Pre-LEARN | `SKILL_REGISTRY` | 38 entries with `category`/`visibility`/`description`/`starter_rank`. Hand-authored over time with merged abstractions (`light_edge` collapsing canonical light/medium/heavy/twohanded edged weapons) |
| LEARN-002b | `SKILL_ALIASES` | Player-friendly abbreviations. Bridges defense skills to `combat` as placeholder |
| LEARN-003a | `CANONICAL_PULSE_GROUPS` | 10-group rotation referencing 63 canonical skill_ids — many of which don't exist in registry |
| LEARN-003b | Pulse runtime | Iterates groups; silently no-ops for skill_ids without registry entries |

The audit caught the drift before LEARN-006 forces a confrontation. Right now:

- Pulse iterates over `shield_usage` every tick but finds no skill state for it (no registry entry -> no instance state -> no work done)
- Players' `exp` for defense skills returns "Combat" because the alias bridges parry/shield to that merged identity
- LEARN-006's design assumes Shield Usage and Parry Ability are proper learning-tracked skills, with their own pools and mindstates

DRG-SKILL-001 lands the missing identities, fixes the pulse references, and adds `display_name` so future skill-display surfaces (LEARN-006's defense field XP display, profession dispatches' skill summaries, etc.) inherit a consistent layer.