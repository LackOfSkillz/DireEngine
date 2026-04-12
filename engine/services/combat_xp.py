from engine.services.skill_service import SkillService


OFFENSE_XP_MULT = 1.15
DEFENSE_XP_MULT = 0.75
CONTEST_XP_FLOOR = 0.25


class CombatXP:

    @staticmethod
    def award(attacker, target, context, hit):
        final_chance = context.get("final_chance")
        if final_chance is None:
            final_chance = 95
        final_chance = int(final_chance)
        difficulty_scale = max(CONTEST_XP_FLOOR, 1.0 - (final_chance / 100.0))
        if final_chance < 95:
            SkillService.award_xp(
                target,
                "evasion",
                max(10, int(context.get("accuracy", 0) or 0)),
                source={"mode": "difficulty"},
                success=not bool(hit),
                context_multiplier=DEFENSE_XP_MULT * difficulty_scale,
            )

        if not hit or final_chance >= 95:
            return

        skill_name = str(context.get("skill_name", "") or "").strip().lower()
        if not skill_name:
            return

        difficulty = target.get_stat("reflex") + target.get_stat("agility")
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