# DRG-LEARN-AUDIT - Learning System & Stat Influence Audit

## Scope and Method

This audit is read-only. It compares the current repo against the canonical learning loop surfaces anchored in the required GSL scripts:

- Sleep / absorb-only behavior: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L3)
- Field-to-rank conversion loop: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L189)
- Field XP award path: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L825)
- EXP display / operator tooling: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L1498) and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L2280)
- Chargen / initial stat and TDP setup: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L3910)
- Stat training by TDP spend: [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4536)

Repo surfaces inspected include the Character storage and access layer, the EXP pool engine, the scheduler pulse, chargen/stat allocation, combat XP awards, circle progression, and the registry-backed skill/stat wiring introduced by DRG-023.

## Executive Verdict

The repo already has a real progression substrate, but it is not canon-parity DragonRealms learning yet.

- It **does** have persistent character stats, persistent skill ranks, a live per-skill learning pool, a 20-second global pulse, wisdom-based draining into rank progress, and cross-system award hooks into combat, magic, stealth, fishing, tending, appraisal, scholarship, locksmithing, and athletics.
- It **does not** have the canonical `fieldexp/current/goal` model, the canonical global sleep/awake absorb behavior, or the canonical TDP loop where skill rank gains mint TDP and TDP are then spent to raise stats.
- The current system is therefore best described as **a modernized partial bridge**, not a completed port of the GSL learning loop.

## A/B/C Map

| Audit Surface | Status | Repo Reality | Canon Gap |
| --- | --- | --- | --- |
| Stat storage and access | A | Eight core stats persist in `db.stats`, are normalized by defaults, read through `get_stat`, written through `set_stat`, and applied during chargen/finalization. See [typeclasses/characters.py](typeclasses/characters.py#L1236), [typeclasses/characters.py](typeclasses/characters.py#L2216), [typeclasses/characters.py](typeclasses/characters.py#L8754), [systems/character/creation.py](systems/character/creation.py#L105), and [systems/character/creation.py](systems/character/creation.py#L225). | Canon uses direct per-stat fields like `pwisdom`, `pdiscipline`, `pintelligence`, and trainable TDP-backed stat mutation in S147/S157/S871 rather than a dict-backed abstraction. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L244), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L956), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4726). |
| Skill rank storage and access | B | Skill rank persistence exists in both legacy `db.skills` and authoritative `db.exp_skill_state`, with sync through `_sync_exp_skill_state`, persistence through `_persist_exp_skill_state`, and access through `get_skill_rank` / `get_skill`. See [typeclasses/characters.py](typeclasses/characters.py#L1381), [typeclasses/characters.py](typeclasses/characters.py#L1424), [typeclasses/characters.py](typeclasses/characters.py#L15431), and [typeclasses/characters.py](typeclasses/characters.py#L18081). | Canon skill state includes at least `rank`, `current`, `goal`, and `fieldexp`, and both S147 and S227 assume those surfaces exist directly. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L204), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L232), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L1784). The repo has no equivalent `goal` or `current` persistence surface. |
| Field XP storage and grants | B | The repo stores per-skill field learning as `SkillState.pool`, computes mindstate from pool, and grants via `SkillService.award_xp()` / `train()`. Award call sites already exist across Character actions and services. See [world/systems/skills.py](world/systems/skills.py#L180), [world/systems/skills.py](world/systems/skills.py#L220), [engine/services/skill_service.py](engine/services/skill_service.py#L44), [typeclasses/characters.py](typeclasses/characters.py#L1462), and [engine/services/combat_xp.py](engine/services/combat_xp.py#L34). | Canon S157 awards explicit `fieldexp`, uses discipline and intelligence in the grant path, applies profession/pool-size logic, and contains sleeping-specific award behavior. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L930), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L956), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L1126), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L1288). The repo does not expose canon `fieldexp` directly and does not implement sleep-gated award suppression. |
| Field XP to ranks conversion | B | The repo has a real 20-second pulse and per-skill drain/rank-up loop: scheduled global EXP pulse, `PulseService.process_skill_pulse()`, `drain_skill()`, `process_rank()`, and wisdom-based drain modifiers. See [world/systems/exp_pulse.py](world/systems/exp_pulse.py#L11), [world/systems/exp_pulse.py](world/systems/exp_pulse.py#L58), [engine/services/pulse_service.py](engine/services/pulse_service.py#L1), [world/systems/skills.py](world/systems/skills.py#L377), and [world/systems/skills.py](world/systems/skills.py#L397). | Canon S147 is broader: it handles overall mind decay, field-to-rank transfer, `goal` updates, and TDP minting on rank gain. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L189), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L196), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L387), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L443). The repo explicitly retires `Character.process_learning_pulse()` in favor of the new transient EXP ticker. See [typeclasses/characters.py](typeclasses/characters.py#L18184). |
| TDP system | C | No repo code path was found that stores, accrues, displays, or spends TDPs. The current progression economy instead records `total_xp`, `unabsorbed_xp`, and `exp_debt`. See [engine/services/skill_service.py](engine/services/skill_service.py#L32), [typeclasses/characters.py](typeclasses/characters.py#L2611), and [commands/cmd_xp.py](commands/cmd_xp.py#L1). | Canon depends on TDP end to end: rank gain grants TDP in S147, chargen seeds starting TDP in S868, and S871 spends TDP to raise stats. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L655), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4132), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4831). |
| DRG-023 wiring sanity check | B | DRG-023 successfully moved skill identity to the registry-backed bundle path; `skill_registry` boots from canon with fallback, and the migrated consumers include the pulse layer and experience command. See [DATA-GAP-AUDIT.md](DATA-GAP-AUDIT.md#L83), [engine/bundles/builtin_skills.py](engine/bundles/builtin_skills.py#L177), [world/systems/skills.py](world/systems/skills.py#L7), and [commands/cmd_experience.py](commands/cmd_experience.py#L57). | The registry wiring is only identity and metadata. It does not by itself complete the learning model. Repo docs already note that `Shield Usage` and `Parry Ability` still do not exist as skills in the registry or pipeline. See [docs/second_wave_skill_batch_research.md](docs/second_wave_skill_batch_research.md#L12). |
| Cross-system integration | B | Cross-system award plumbing is real: combat calls `CombatXP.award()`, defense verbs use `SkillService`, spell contests award skill XP, stealth and fishing award through the same shared system, and stats are already read inside combat and magic services. See [engine/services/combat_service.py](engine/services/combat_service.py#L17), [engine/services/combat_xp.py](engine/services/combat_xp.py#L8), [engine/services/defense_verb_service.py](engine/services/defense_verb_service.py#L93), [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L8), and [engine/services/mana_service.py](engine/services/mana_service.py#L718). | The progression side is still incomplete: no sleep command, no TDP loop, incomplete S00509 defense learning, and profession advancement is still specialized and thin rather than full canon profession progression. See [CHANGELOG.md](CHANGELOG.md#L25), [AS_BUILT.md](AS_BUILT.md#L75), and [typeclasses/characters.py](typeclasses/characters.py#L15519). |

## Section Findings

### 1. Stat Storage and Access

The repo has a solid stat substrate already. `Character` initializes `db.stats` from registry-provided defaults, normalizes missing keys through `ensure_stat_defaults()`, and reads/writes through `get_stat()` and `set_stat()`. See [typeclasses/characters.py](typeclasses/characters.py#L1236), [typeclasses/characters.py](typeclasses/characters.py#L2216), and [typeclasses/characters.py](typeclasses/characters.py#L8754).

Chargen and creation also require a complete eight-stat payload and apply it directly to the character. See [systems/character/creation.py](systems/character/creation.py#L105), [systems/character/creation.py](systems/character/creation.py#L225), and [systems/character/creation.py](systems/character/creation.py#L503).

This means DRG-024c and later combat or magic math are **not** reading from placeholders. They already consume meaningful persistent stats. Examples include combat XP difficulty using target reflex and agility, spell contests using a defense stat, and mana regeneration using wisdom/intelligence/discipline surfaces. See [engine/services/combat_xp.py](engine/services/combat_xp.py#L64), [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L20), and [engine/services/mana_service.py](engine/services/mana_service.py#L370).

The gap is not storage. The gap is **how those stats change over time**.

### 2. Skill Rank Storage and Access

The repo has a split model:

- `db.skills` remains the legacy compatibility store for rank, pool, and mindstate. See [typeclasses/characters.py](typeclasses/characters.py#L14361).
- `db.exp_skill_state` is the richer persisted surface for `rank`, `rank_progress`, `pool`, `skillset`, `mindstate`, and `last_trained`. See [typeclasses/characters.py](typeclasses/characters.py#L1424).
- `SkillHandler` / `SkillState` are the runtime objects used by the live learning system. See [world/systems/skills.py](world/systems/skills.py#L438).

That is enough for ranks, live learning display, and cross-system reads. It is **not** enough for strict canon parity because canon scripts assume `rank`, `current`, `goal`, and `fieldexp` are all first-class mutable attributes per skill. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L204), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L232), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L2173).

### 3. Field XP Storage and Grants

The repo definitely grants learning today. The main award surfaces are:

- `Character.award_skill_experience()` -> `SkillService.award_xp()`: [typeclasses/characters.py](typeclasses/characters.py#L1462) and [engine/services/skill_service.py](engine/services/skill_service.py#L44)
- combat XP: [engine/services/combat_xp.py](engine/services/combat_xp.py#L8)
- defense-verb remedial parry XP: [engine/services/defense_verb_service.py](engine/services/defense_verb_service.py#L93)
- spell contests: [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L62)
- stealth/fishing/other skills via the same shared service: [engine/services/skill_service.py](engine/services/skill_service.py#L83)

The repo also tracks a second economy on top of per-skill pools: `total_xp`, `unabsorbed_xp`, and `exp_debt`. See [engine/services/skill_service.py](engine/services/skill_service.py#L32) and [typeclasses/characters.py](typeclasses/characters.py#L2611).

That is useful gameplay state, but it is not the same thing as canon `fieldexp`. Canon S157 directly mutates per-skill `fieldexp`, uses discipline/intelligence to scale gain, and incorporates sleeping behavior. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L930), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L956), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L1288).

### 4. Field XP to Ranks Conversion

This is the strongest parity-adjacent area in the repo.

The repo already has:

- a 20-second scheduled pulse: [world/systems/exp_pulse.py](world/systems/exp_pulse.py#L11)
- runtime registration of active EXP characters: [world/systems/exp_pulse.py](world/systems/exp_pulse.py#L36)
- skill-group staggering across the full 200-second cycle: [world/systems/exp_pulse.py](world/systems/exp_pulse.py#L17)
- per-skill drain into rank progress plus rank-up processing: [world/systems/skills.py](world/systems/skills.py#L377) and [world/systems/skills.py](world/systems/skills.py#L397)

The repo therefore already has the controlling runtime abstraction for a learning ticker.

But the conversion semantics are not canon S147 semantics. Canon S147 performs field-to-rank conversion while also managing overall mind decay, per-skill goals, and TDP minting. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L196), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L387), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L655).

The repo explicitly retired `Character.process_learning_pulse()` and moved the real work into the new transient EXP ticker, so any downstream work should hook the scheduler-driven EXP path, not the legacy Character method. See [typeclasses/characters.py](typeclasses/characters.py#L18184).

### 5. TDP System

This is the clearest hard gap.

I found no repo implementation for:

- persisted TDP state
- TDP minting on rank gain
- TDP display
- TDP-based stat training

What exists instead is `unabsorbed_xp` and `exp_debt`, which are valuable but non-canonical economies. See [typeclasses/characters.py](typeclasses/characters.py#L2611), [typeclasses/characters.py](typeclasses/characters.py#L2631), and [commands/cmd_xp.py](commands/cmd_xp.py#L1).

Canon requires all of the missing pieces. Rank gain in S147 increments `np0:tdp`; S868 seeds initial TDP; S871 spends TDP to raise a selected stat. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L655), [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4132), and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L4989).

### 6. DRG-023 Wiring Sanity Check

DRG-023 is not the current blocker. It did its job.

The registry-backed skill identity path is live and consumed by the EXP system. Repo documentation and code agree on that point. See [DATA-GAP-AUDIT.md](DATA-GAP-AUDIT.md#L83), [engine/bundles/builtin_skills.py](engine/bundles/builtin_skills.py#L189), and [world/systems/skills.py](world/systems/skills.py#L7).

The real limitation is that DRG-023 wires **identity and metadata**, not the missing progression semantics. That distinction matters. A valid skill registry does not automatically create canon `fieldexp`, `goal`, `TDP`, or missing skills like `Shield Usage` and `Parry Ability`. Repo research already calls those defense skills absent from the registry and combat pipeline. See [docs/second_wave_skill_batch_research.md](docs/second_wave_skill_batch_research.md#L12).

### 7. Cross-System Integration

The repo is already consistently routing learning through shared engine services instead of scattering bespoke XP math.

That is good architecture and should be preserved. Combat, magic, stealth, empathy actions, fishing, appraisal, and scholarship all flow into the same learning substrate. See [engine/services/combat_service.py](engine/services/combat_service.py#L17), [engine/services/combat_xp.py](engine/services/combat_xp.py#L8), [engine/services/spell_contest_service.py](engine/services/spell_contest_service.py#L62), and [typeclasses/characters.py](typeclasses/characters.py#L1462).

But three integration gaps still matter:

1. There is no sleep/awake gameplay loop implementing canon absorb-without-gain behavior. Canon S74 and S157 both rely on it. See [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L3) and [tmp/drg_learn_audit_canon.txt](tmp/drg_learn_audit_canon.txt#L930). No repo `sleep` command or `sleeping` learning surface was found in command or Character code.
2. Defense learning parity is still intentionally incomplete relative to S00509. The repo itself documents that DRG-024c only added a minimal parry XP bridge and that armor/shield learning remains follow-on work. See [CHANGELOG.md](CHANGELOG.md#L25) and [AS_BUILT.md](AS_BUILT.md#L75).
3. Profession progression is still thin and specialized. For Empaths, circle progression is driven by circle requirement tables and persisted skill rank, not by the full canon skill + TDP + stat training loop. See [typeclasses/characters.py](typeclasses/characters.py#L15519) and [world/systems/circles.py](world/systems/circles.py#L1).

## Critical-Path Blockers

### Blockers for DRG-024c Follow-On Parity

The shipped DRG-024c stance work is mechanically valid, but full learning parity downstream is blocked by:

1. **Missing TDP loop**. Canon defense learning is part of a larger progression economy where ranks ultimately feed TDP and stat growth. The repo has no such sink/source pair.
2. **Missing defense skills**. `Shield Usage` and `Parry Ability` are still absent as real skills, so S00509-style defense learning cannot land cleanly on canonical skill identities yet. See [docs/second_wave_skill_batch_research.md](docs/second_wave_skill_batch_research.md#L12).
3. **Non-canonical skill state model**. Current combat XP awards go into `pool`/`rank_progress`, not `fieldexp`/`goal`. That is workable, but any parity work must choose either a compatibility adapter or a broader model migration first.

### Blockers for DRG-024.5 and Downstream Profession Dispatches

These are more structural:

1. **Stats already influence runtime math, but there is no canonical long-term stat progression path.** Downstream profession balance will be hard to judge if wisdom, intelligence, discipline, reflex, and agility can be read but not trained through canon systems.
2. **Circle / profession advancement is not yet backed by the full learning economy.** Current circle logic is specialized and does not reflect the complete profession requirement surface implied by canon progression.
3. **Sleep behavior is missing.** Any profession or magic dispatch that assumes the canonical absorb-only rest loop will be building on different player behavior than canon expects.

## Recommended Dispatch Sequence

1. **DRG-LEARN-FOUNDATION-TDP**
   Implement persisted TDP state, rank-gain TDP minting, and a single authoritative TDP spend API.

2. **DRG-LEARN-PARITY-ADAPTER**
   Decide whether to expose canon-compatible `fieldexp/current/goal` as an adapter over the current pool engine or to migrate the underlying persistence model. Do this before adding more profession-specific learning behavior.

3. **DRG-SLEEP-ABSORB**
   Add `sleep` / `awake` behavior and enforce canon-style absorb-without-new-gain semantics on the shared award path.

4. **DRG-DEFENSE-LEARNING-S00509**
   Add canonical defense learning identities and finish the armor/shield/parry distribution work that DRG-024c deliberately left for follow-on.

5. **Only after 1-4** continue with deeper profession dispatches or DRG-024.5 parity-sensitive work.

## Bottom Line

The current repo is **not standing on quicksand**, but it **is standing on a different progression model than canon**.

Combat and magic already read meaningful stats and real skill ranks. What is missing is the canon progression loop that changes those stats over time: sleep absorb behavior, `fieldexp/current/goal` parity, TDP minting, and TDP-based stat training. Those are the real blockers for canon-faithful downstream profession work.