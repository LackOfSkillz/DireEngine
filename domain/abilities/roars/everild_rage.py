from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class EverildRageRoar:
    bit_index = 1
    name = "everild"
    canonical_display_name = "Everild's Rage"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("everild", "everildsrage", "everild's rage")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        total = int((vocal_profile or {}).get("total", 0) or 0)
        if total > 20:
            return ActionResult.fail(
                errors=[
                    "Strain though you might, you cannot muster enough energy to vocalize your fighting spirit.",
                ]
            )
        return ActionResult.ok(data={"modifier": int((vocal_profile or {}).get("modifier", 100) or 100)})

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return vocal_service.add_vocal_damage(actor, cls.vocal_damage_code, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        messages = [
            "The fury of Everild's Rage burns in your soul, and your roar is filled with that fury.",
        ]
        if not targets:
            messages.append("Your fury rolls across the room, but there is no foe nearby to weaken.")
            return ActionResult.ok(messages=messages, data={"targets": [], "roar": cls.name})

        applied = []
        resisted = []
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            charisma = roar_service.get_stat(actor, "charisma")
            penalty = min(20, int((charisma / 3) + (margin / 10)))
            duration = int((penalty * 3 / 2) + 15)
            penalties = {"shield": penalty}
            if margin > 10:
                penalties["parry"] = penalty
            if margin > 30:
                penalties["evasion"] = penalty
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "penalties": penalties,
                "source_id": getattr(actor, "id", None),
                "source_key": getattr(actor, "key", None),
                "margin": margin,
            }
            roar_service.set_target_effect(target, "barbarian_roar_everild", payload)
            roar_service.set_target_effect(target, "effect_11808001", payload)
            if "parry" in penalties or "evasion" in penalties:
                roar_service.set_target_effect(target, "effect_11808002", payload)
            applied.append(getattr(target, "key", "someone"))

        if applied:
            messages.append(f"Everild's Rage weakens {', '.join(applied)}, eroding their defenses.")
        if resisted:
            messages.append(f"{', '.join(resisted)} resist the weakening edge of your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})