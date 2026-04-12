import time

from domain.combat import rules
from engine.services.result import ActionResult
from engine.services.skill_service import SkillService
from engine.services.state_service import StateService


OFFENSE_XP_MULT = 1.15
DEFENSE_XP_MULT = 0.75
CONTEST_XP_FLOOR = 0.25


class CombatService:

    @staticmethod
    def _award_combat_experience(attacker, target, context, hit):
        final_chance = int(context.get("final_chance", 95) or 95)
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

    @staticmethod
    def attack(attacker, target, attack_type="basic", context=None):
        context = dict(context or {})
        hit = rules.calculate_hit(attacker, target, context)
        context["hit"] = hit
        roundtime = rules.calculate_roundtime(attacker, target, context)
        CombatService._award_combat_experience(attacker, target, context, hit)

        fatigue_cost = int(context.get("fatigue_cost", 0) or 0)
        clear_state_keys = ["warrior_surge", "warrior_crush", "warrior_press", "warrior_sweep", "warrior_whirl", "ranger_pounce"]

        if not hit:
            StateService.apply_fatigue(attacker, attacker.db.fatigue + fatigue_cost)
            if hasattr(attacker, "gain_war_tempo"):
                attacker.gain_war_tempo(5)
            if hasattr(attacker, "advance_combat_rhythm"):
                attacker.advance_combat_rhythm(hit=False)
            for state_key in clear_state_keys:
                if hasattr(attacker, "clear_state"):
                    attacker.clear_state(state_key)
            StateService.apply_roundtime(attacker, roundtime, ambush=bool(context.get("ambush")))
            if context.get("is_ranged_weapon") and hasattr(attacker, "consume_loaded_ammo"):
                attacker.consume_loaded_ammo()
            return ActionResult.ok(data={"hit": False, "damage": 0, "roundtime": roundtime, "details": context})

        damage = rules.calculate_damage(attacker, target, context)
        target_was_dead = bool(getattr(target.db, "is_dead", False))
        damage_result = StateService.apply_damage(
            target,
            damage,
            context["hit_location"],
            context["attack_context"]["damage_type"],
            critical=bool(context.get("critical")),
        )
        applied_damage = damage_result.data.get("amount", damage)
        if not target_was_dead and bool(getattr(target.db, "is_dead", False)) and hasattr(attacker, "register_empath_offensive_action"):
            attacker.register_empath_offensive_action(target=target, context="kill", amount=30)

        StateService.apply_balance(attacker, attacker.db.balance - context["profile"]["balance_cost"])
        StateService.apply_fatigue(attacker, attacker.db.fatigue + fatigue_cost)
        if hasattr(attacker, "gain_war_tempo"):
            attacker.gain_war_tempo(8)
        if hasattr(attacker, "advance_combat_rhythm"):
            attacker.advance_combat_rhythm(hit=True)
        for state_key in clear_state_keys:
            if hasattr(attacker, "clear_state"):
                attacker.clear_state(state_key)
        attacker.db.recent_action = True
        attacker.db.recent_action_timer = time.time()
        StateService.apply_roundtime(attacker, roundtime, ambush=bool(context.get("ambush")))
        if context.get("is_ranged_weapon") and hasattr(attacker, "consume_loaded_ammo"):
            attacker.consume_loaded_ammo()

        return ActionResult.ok(data={"hit": True, "damage": applied_damage, "roundtime": roundtime, "details": context})