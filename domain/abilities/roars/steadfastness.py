from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class SteadfastnessRoar:
    bit_index = 20
    name = "steadfastness"
    canonical_display_name = "Steadfastness"
    category = "inspiration"
    aliases = ("steadfastness", "steadfast")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        strength = inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer)
        hp_bonus = min(25, max(5, strength))
        fatigue_relief = min(20, max(4, strength))
        duration = 30 + strength
        applied = []
        for target in list(targets or []):
            if hasattr(target, "db"):
                target.db.hp = int(getattr(target.db, "hp", 0) or 0) + hp_bonus
                target.db.fatigue = max(0, int(getattr(target.db, "fatigue", 0) or 0) - fatigue_relief)
            payload = {"name": cls.name, "expires_at": roar_service.now() + duration, "duration": duration, "hp_bonus": hp_bonus, "fatigue_relief": fatigue_relief, "source_id": getattr(actor, "id", None)}
            roar_service.set_target_effect(target, roar_service.STEADFASTNESS_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_11827001", payload)
            applied.append(getattr(target, "key", "someone"))
        return ActionResult.ok(messages=["Steadfastness rolls out like a wall against exhaustion and pain.", f"Steadfastness leaves {', '.join(applied)} harder to wear down."], data={"targets": applied, "roar": cls.name})