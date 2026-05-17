from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class HonorRoar:
    bit_index = 18
    name = "honor"
    canonical_display_name = "Honor"
    category = "inspiration"
    aliases = ("honor",)

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        bonus = min(10, max(2, inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer) // 4))
        duration = 40 + (bonus * 2)
        applied = []
        for target in list(targets or []):
            payload = {"name": cls.name, "expires_at": roar_service.now() + duration, "duration": duration, "stat_modifiers": {"charisma": bonus}, "source_id": getattr(actor, "id", None)}
            roar_service.set_target_effect(target, roar_service.HONOR_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_11825001", payload)
            applied.append(getattr(target, "key", "someone"))
        return ActionResult.ok(messages=["Honor swells through your allies, hardening conviction into presence.", f"Honor lends greater force of personality to {', '.join(applied)}."], data={"targets": applied, "roar": cls.name})