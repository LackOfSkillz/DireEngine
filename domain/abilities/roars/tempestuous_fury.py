from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class TempestuousFuryRoar:
    bit_index = 3
    name = "tempestuous"
    canonical_display_name = "Tempestuous Fury"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("tempestuous", "tempestuousfury", "tempestuous fury")

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
        messages = ["You let loose the contained violence of Tempestuous Fury in a single roar."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            attack = roar_service.get_stat(actor, "discipline") + roar_service.get_stat(actor, "charisma") + (roar_service.get_stat(actor, "strength") * 2)
            resist = roar_service.get_stat(target, "discipline") + (roar_service.get_stat(target, "reflex") * 2)
            margin = int((attack * modifier) / 100) - resist + int((randomizer or (lambda _l, _h: 0))(-5, 10))
            if margin <= 8:
                resisted.append(getattr(target, "key", "someone"))
                continue
            penalty = min(20, max(1, int(margin / 3)))
            duration = min(40, penalty * 2)
            penalties = {"missile_accuracy": penalty}
            if margin > 32:
                penalties["missile_damage"] = penalty
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "penalties": penalties,
                "margin": margin,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_tempestuous", payload)
            roar_service.set_target_effect(target, "effect_11810001", payload)
            if "missile_damage" in penalties:
                roar_service.set_target_effect(target, "effect_11810002", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Tempestuous Fury strips certainty from {', '.join(applied)} whenever they loose a missile.")
        if resisted:
            messages.append(f"{', '.join(resisted)} keep their missile discipline despite your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})