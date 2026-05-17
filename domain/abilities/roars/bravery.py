from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class BraveryRoar:
    bit_index = 23
    name = "bravery"
    canonical_display_name = "Bravery"
    category = "inspiration"
    aliases = ("bravery", "brave")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        bonus = min(60, max(10, inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer) * 2))
        duration = 35 + (bonus // 3)
        applied = []
        for target in list(targets or []):
            payload = {"name": cls.name, "expires_at": roar_service.now() + duration, "duration": duration, "fear_resistance_pct": bonus, "source_id": getattr(actor, "id", None)}
            roar_service.set_target_effect(target, roar_service.BRAVERY_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_11830001", payload)
            applied.append(getattr(target, "key", "someone"))
        return ActionResult.ok(messages=["Bravery strips hesitation out of the room.", f"Bravery leaves {', '.join(applied)} harder to shake with fear."], data={"targets": applied, "roar": cls.name})