from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class InsaneLaughterRoar:
    bit_index = 14
    name = "insanelaughter"
    canonical_display_name = "Insane Laughter"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("insanelaughter", "insane laughter", "laughter")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        total = int((vocal_profile or {}).get("total", 0) or 0)
        if total > 20:
            return ActionResult.fail(errors=["Strain though you might, you cannot muster enough energy to vocalize your fighting spirit."])
        return ActionResult.ok(data={"modifier": int((vocal_profile or {}).get("modifier", 100) or 100)})

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return vocal_service.add_vocal_damage(actor, cls.vocal_damage_code, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        messages = ["Insane Laughter ripples through the room and turns enemy timing against itself."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = min(30, max(8, 8 + margin))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "attack_roundtime_penalty": min(3.0, max(0.5, round(float(margin) / 12.0, 2))),
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_insane_laughter", payload)
            roar_service.set_target_effect(target, "effect_11821001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Insane Laughter leaves {', '.join(applied)} slower to bring their attacks to bear.")
        if resisted:
            messages.append(f"{', '.join(resisted)} refuse to lose their timing to your laughter.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})