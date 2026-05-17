from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class BansheesWailRoar:
    bit_index = 13
    name = "bansheeswail"
    canonical_display_name = "Banshee's Wail"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("bansheeswail", "banshee's wail", "banshees wail")

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
        messages = ["Banshee's Wail pours raw dread into the room and nails enemies where they stand."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = min(12, max(3, int(margin / 6) + 2))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "immobilized": True,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_banshees_wail", payload)
            roar_service.set_target_effect(target, "effect_11820001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Banshee's Wail leaves {', '.join(applied)} frozen in place by fear.")
        if resisted:
            messages.append(f"{', '.join(resisted)} keep moving despite the force of your wail.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})