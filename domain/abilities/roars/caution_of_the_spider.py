from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class CautionOfTheSpiderRoar:
    bit_index = 9
    name = "cautionofthespider"
    canonical_display_name = "Caution of the Spider"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("cautionofthespider", "caution of the spider", "spider")

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
        messages = ["Caution of the Spider snaps through the room with enough menace to drive enemies backward."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 5:
                resisted.append(getattr(target, "key", "someone"))
                continue
            if hasattr(target, "disengage"):
                target.disengage(emit_message=False)
            elif hasattr(target, "set_target"):
                target.set_target(None)
                if getattr(getattr(target, "db", None), "in_combat", None) is not None:
                    target.db.in_combat = False
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + 5,
                "duration": 5,
                "margin": margin,
                "disengaged": True,
                "retreat_steps": 2 if margin > 25 else 1,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_caution_of_the_spider", payload)
            roar_service.set_target_effect(target, "effect_11816001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Caution of the Spider forces {', '.join(applied)} to break away from the fight.")
        if resisted:
            messages.append(f"{', '.join(resisted)} hold their ground despite the warning in your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})