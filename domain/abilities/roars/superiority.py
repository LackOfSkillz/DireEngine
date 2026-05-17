from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class SuperiorityRoar:
    bit_index = 25
    name = "superiority"
    canonical_display_name = "Superiority"
    category = "inspiration"
    aliases = ("superiority", "superior")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        bonus = min(20, max(5, inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer)))
        duration = 35 + bonus
        applied = []
        for target in list(targets or []):
            payload = {"name": cls.name, "expires_at": roar_service.now() + duration, "duration": duration, "penalties": {"evasion": -bonus, "parry": -bonus, "shield": -bonus}, "source_id": getattr(actor, "id", None)}
            roar_service.set_target_effect(target, roar_service.SUPERIORITY_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_11832001", payload)
            applied.append(getattr(target, "key", "someone"))
        return ActionResult.ok(messages=["Superiority rings out with a promise that your allies will not be easy prey.", f"Superiority reinforces the defensive factors of {', '.join(applied)}."], data={"targets": applied, "roar": cls.name})