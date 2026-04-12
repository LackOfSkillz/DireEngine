from collections.abc import Mapping
import time

from world.systems.skills import MINDSTATE_MAX, award_xp as award_skill_pool_xp, calculate_mindstate as calculate_skill_mindstate, normalize_skill_name, train

from engine.services.result import ActionResult


class SkillService:

    @staticmethod
    def calculate_mindstate(pool, capacity):
        return max(0, min(MINDSTATE_MAX, int(calculate_skill_mindstate(pool or 0.0, capacity or 0.0))))

    @staticmethod
    def _normalize_source(source):
        if isinstance(source, Mapping):
            return dict(source)
        if source is None:
            return {}
        return {"kind": str(source or "")}

    @staticmethod
    def _get_exp_skill(character, skill_name):
        normalized = normalize_skill_name(skill_name)
        exp_skill = character._sync_exp_skill_state(normalized)
        exp_skill.skillset = character.get_exp_skillset_tier(normalized)
        exp_skill.recalc_pool()
        return exp_skill

    @staticmethod
    def _record_field_xp(character, amount):
        tracked_amount = max(0, int(round(float(amount or 0.0))))
        if tracked_amount <= 0:
            return 0
        character.db.total_xp = int(getattr(character.db, "total_xp", 0) or 0) + tracked_amount
        if hasattr(character, "adjust_unabsorbed_xp"):
            character.adjust_unabsorbed_xp(tracked_amount)
        if hasattr(character, "reduce_exp_debt"):
            character.reduce_exp_debt(tracked_amount)
        return tracked_amount

    @staticmethod
    def award_xp(character, skill, amount, source=None, success=True, outcome=None, event_key=None, context_multiplier=1.0):
        if character is None:
            return ActionResult.fail(errors=["Missing character."])
        if hasattr(character, "ensure_core_defaults"):
            character.ensure_core_defaults()

        normalized_skill = normalize_skill_name(skill)
        source_data = SkillService._normalize_source(source)
        mode = str(source_data.get("mode", "flat") or "flat").strip().lower()
        exp_skill = SkillService._get_exp_skill(character, normalized_skill)

        if mode == "difficulty":
            gained = train(
                exp_skill,
                max(1, int(amount or 0)),
                success=success,
                outcome=outcome,
                event_key=event_key,
                context_multiplier=context_multiplier,
            )
        else:
            exp_skill.last_trained = time.time()
            gained = award_skill_pool_xp(exp_skill, max(0.0, float(amount or 0.0)))

        if hasattr(character, "_persist_exp_skill_state"):
            character._persist_exp_skill_state(exp_skill)

        if source_data.get("track_field_xp"):
            SkillService._record_field_xp(character, gained)

        return ActionResult.ok(
            data={
                "amount": float(gained or 0.0),
                "skill": normalized_skill,
                "source": source_data,
            }
        )

    @staticmethod
    def award_practice(character, skill, difficulty, learning_multiplier=1.0, source=None):
        if character is None:
            return ActionResult.fail(errors=["Missing character."], data={"amount": 0.0, "band": "trivial"})

        normalized_skill = normalize_skill_name(skill)
        amount, band = character.get_learning_amount(normalized_skill, difficulty)
        skillset = character.get_skillset(normalized_skill)
        weight = character.get_skill_weight(skillset)
        amount *= weight
        amount *= max(0.0, float(learning_multiplier or 0.0))
        amount *= character.get_scholarship_learning_multiplier()
        amount *= character.get_race_learning_modifier(skill_name=normalized_skill)
        amount = int(amount) if amount > 0 else 0
        if amount > 0:
            amount = max(1, amount)

        debt_multiplier = character.get_xp_debt_gain_multiplier()
        if amount > 0 and debt_multiplier < 1.0:
            amount = max(1, int(round(amount * debt_multiplier)))

        if band == "trivial" or amount <= 0:
            return ActionResult.ok(data={"amount": 0.0, "band": band, "skill": normalized_skill})

        result = SkillService.award_xp(
            character,
            normalized_skill,
            amount,
            source=dict(SkillService._normalize_source(source)) | {"track_field_xp": True},
        )
        return ActionResult(
            success=result.success,
            data={"amount": result.amount, "band": band, "skill": normalized_skill},
            messages=list(result.messages),
            errors=list(result.errors),
        )