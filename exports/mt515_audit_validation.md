# MT-515-audit validation

Status: SHIPPED

Deliverable: `docs/audits/skill_system_state.md`

Phase A: Skill inventory complete. 38 skills documented.
Phase B: Per-skill paths documented for all 38 skills.
Phase C: Shared infrastructure documented.
Phase D: DR taxonomy mapping complete within the repo evidence available to this audit.
Phase E: Gap analysis classifies all 38 skills.
Phase F: Report checked in.
Phase G: This artifact.

## Summary Of Findings

The current skill system has one explicit 38-skill registry, but runtime training is split across generic practice (`use_skill`), direct difficulty XP awards (`SkillService.award_xp`), and legacy wrapper calls (`award_skill_experience`). Character persistence also keeps both `db.skills` and `db.exp_skill_state` / `SkillHandler` active at the same time. Outdoorsmanship already implements the low-rank failure-learning pattern in forage, while many other skills either train only on success, hard-fail through profession/guild checks, or have no concrete runtime attempt path yet.

The full audit lives at `docs/audits/skill_system_state.md`.

## Implications For MT-515-impl Scope

This audit shows MT-515-impl is broader than a tiny single-pattern cleanup. The skill surface is 38 rows wide, several training paths are dynamic, and multiple gating systems coexist. The codebase is ready for a design dispatch, but the implementation dispatch will need to account for both generalized helpers and the current split between direct XP calls, practice calls, and dynamic combat/spell routing.

## Verification Checklist

1. Phase A inventory captures all 38 skills present in `SKILL_REGISTRY`.
2. Phase B records concrete attempt/training ownership where found and marks registry-only / unclear cases explicitly.
3. Phase C documents `SkillService`, lower-level EXP state, profession helpers, and ability gates.
4. Phase D maps current registry state to the DR skillset / guild-skill taxonomy named in the dispatch and local DR research files.
5. Phase E classifies every registry skill against the MT-515 principle.
6. Phase F report is checked in at `docs/audits/skill_system_state.md`.
7. Phase G validation tracker is checked in.
8. No code files were edited by this audit.
9. The audit report stays descriptive rather than prescribing implementation.
10. Open questions are captured in the report for MT-515-impl.