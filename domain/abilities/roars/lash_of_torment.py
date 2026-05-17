from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class LashOfTormentRoar:
    bit_index = 11
    name = "lashoftorment"
    canonical_display_name = "Lash of Torment"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("lashoftorment", "lash of torment", "lash")

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
        messages = ["Lash of Torment cracks out of your throat and into the nerves of your enemies."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = min(8, max(2, int(margin / 8) + 2))
            if hasattr(target, "db"):
                target.db.stunned = True
                target.db.stunned_until = roar_service.now() + duration
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_lash_of_torment", payload)
            roar_service.set_target_effect(target, "effect_11818001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Lash of Torment leaves {', '.join(applied)} stunned and reeling.")
        if resisted:
            messages.append(f"{', '.join(resisted)} shake off the lash before it can stun them.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})