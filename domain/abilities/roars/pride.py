from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class PrideRoar:
    bit_index = 21
    name = "pride"
    canonical_display_name = "Pride"
    category = "inspiration"
    aliases = ("pride",)

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        strength = inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer)
        balance_bonus = min(20, max(5, strength))
        rt_bonus = -min(2.0, max(0.5, round(strength / 12.0, 2)))
        wisdom_penalty = -min(5, max(1, strength // 5))
        duration = 30 + strength
        applied = []
        for target in list(targets or []):
            if hasattr(target, "get_balance") and hasattr(target, "set_balance"):
                current_balance, max_balance = target.get_balance()
                target.set_balance(min(int(max_balance or 100), int(current_balance or 0) + balance_bonus))
            payload = {"name": cls.name, "expires_at": roar_service.now() + duration, "duration": duration, "attack_roundtime_penalty": rt_bonus, "stat_modifiers": {"wisdom": wisdom_penalty}, "source_id": getattr(actor, "id", None)}
            roar_service.set_target_effect(target, roar_service.PRIDE_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_11828001", payload)
            applied.append(getattr(target, "key", "someone"))
        return ActionResult.ok(messages=["Pride braces your allies and drives their timing sharper.", f"Pride steadies {', '.join(applied)} while demanding a little wisdom in return."], data={"targets": applied, "roar": cls.name})