from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class ScreechOfMadnessRoar:
    bit_index = 12
    name = "screechofmadness"
    canonical_display_name = "Screech of Madness"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("screechofmadness", "screech of madness", "screech")

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
        messages = ["Screech of Madness tears at the mind, leaving enemies more vulnerable to fear."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = min(45, max(10, 10 + margin))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "fear_amplification_pct": min(60, max(10, margin)),
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_screech_of_madness", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Screech of Madness leaves {', '.join(applied)} dangerously open to further terror.")
        if resisted:
            messages.append(f"{', '.join(resisted)} keep their wits despite your maddening screech.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})