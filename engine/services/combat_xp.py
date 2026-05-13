from engine.services.skill_service import SkillService
from domain.combat.resolution import CombatOutcome


OFFENSE_XP_MULT = 1.15
DEFENSE_XP_MULT = 0.75
CONTEST_XP_FLOOR = 0.25


class CombatXP:

    @staticmethod
    def award(attacker, target, context, hit):
        leftover_of = context.get("leftover_of")
        offensive_total = context.get("offensive_factor_total", context.get("accuracy", 0))
        defensive_total = context.get("evasion_defense_factor_total", context.get("evasion", 0))

        if leftover_of is None:
            final_chance = context.get("final_chance")
            if final_chance is None:
                final_chance = 95
            final_chance = int(final_chance)
            difficulty_scale = max(CONTEST_XP_FLOOR, 1.0 - (final_chance / 100.0))
        else:
            offensive_total = max(1, int(offensive_total or 0))
            defensive_total = max(0, int(defensive_total or 0))
            difficulty_scale = max(CONTEST_XP_FLOOR, min(2.0, defensive_total / offensive_total if offensive_total else 1.0))

        should_award_defense = int(defensive_total or 0) > 0
        if leftover_of is None:
            should_award_defense = int(95 if final_chance is None else final_chance) < 95

        if should_award_defense:
            SkillService.award_xp(
                target,
                "evasion",
                max(10, int(offensive_total or 0)),
                source={"mode": "difficulty"},
                success=not bool(hit),
                context_multiplier=DEFENSE_XP_MULT * difficulty_scale,
            )

        parry = dict(context.get("parry") or {})
        parry_block_pct = int(parry.get("block_pct", 0) or 0)
        if parry_block_pct > 0 and str(context.get("combat_outcome", "")) in {CombatOutcome.PARTIALLY_PARRIED.value, CombatOutcome.FULLY_PARRIED.value}:
            weapon_profile = target.get_weapon_profile() if hasattr(target, "get_weapon_profile") else {}
            parry_skill = str((weapon_profile or {}).get("skill") or "combat").strip().lower() or "combat"
            SkillService.award_xp(
                target,
                parry_skill,
                max(10, int(offensive_total or 0)),
                source={"mode": "difficulty"},
                success=True,
                context_multiplier=DEFENSE_XP_MULT * difficulty_scale,
            )

        if not hit:
            return

        skill_name = str(context.get("skill_name", "") or "").strip().lower()
        if not skill_name:
            return

        difficulty = max(int(defensive_total or 0), target.get_stat("reflex") + target.get_stat("agility"))
        if skill_name in {"brawling", "light_edge"}:
            SkillService.award_xp(
                attacker,
                skill_name,
                max(10, int(target.get_skill("evasion") + difficulty)),
                source={"mode": "difficulty"},
                success=True,
                context_multiplier=OFFENSE_XP_MULT * difficulty_scale,
            )
            return

        SkillService.award_practice(
            attacker,
            skill_name,
            difficulty,
            learning_multiplier=OFFENSE_XP_MULT * difficulty_scale,
        )