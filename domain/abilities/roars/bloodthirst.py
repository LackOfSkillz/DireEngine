from collections.abc import Mapping

from engine.services.result import ActionResult

from domain.abilities.roars.inspiration_shared import add_inspiration_vocal_damage, inspiration_strength, standard_vocal_damage_check


class BloodthirstRoar:
    bit_index = 24
    name = "bloodthirst"
    canonical_display_name = "Bloodthirst"
    category = "inspiration"
    aliases = ("bloodthirst",)

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        return standard_vocal_damage_check(vocal_profile)

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return add_inspiration_vocal_damage(actor, vocal_service, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        strength = inspiration_strength(roar_service, actor, vocal_profile=vocal_profile, randomizer=randomizer)
        stat_bonus = min(8, max(2, strength // 4))
        offense_bonus = min(20, max(5, strength))
        saf_reduction = min(25, max(5, strength))
        fatigue_cost = min(12, max(3, strength // 2))
        duration = 25 + strength
        applied = []
        berserked = []
        for target in list(targets or []):
            active_berserk = getattr(target, "get_active_barbarian_berserk", lambda: None)()
            if isinstance(active_berserk, Mapping) and hasattr(target, "get_inner_fire") and hasattr(target, "set_inner_fire"):
                target.set_inner_fire(max(0, int(target.get_inner_fire() or 0) - saf_reduction), emit_messages=False)
                berserked.append(getattr(target, "key", "someone"))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "fatigue_cost": fatigue_cost,
                "stat_modifiers": {"strength": stat_bonus, "stamina": stat_bonus},
                "penalties": {
                    "melee_accuracy": -offense_bonus,
                    "melee_damage": -offense_bonus,
                    "missile_accuracy": -max(1, offense_bonus // 2),
                    "missile_damage": -max(1, offense_bonus // 2),
                },
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, roar_service.BLOODTHIRST_STATE_KEY, payload)
            roar_service.set_target_effect(target, "effect_8932001", payload)
            applied.append(getattr(target, "key", "someone"))
        messages = ["Bloodthirst ignites raw killing force in your allies.", f"Bloodthirst surges through {', '.join(applied)}, sharpening strength, stamina, and offense."]
        if berserked:
            messages.append(f"The berserking rage in {', '.join(berserked)} feeds on the cry, burning away some inner fire.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "berserked": berserked, "roar": cls.name})