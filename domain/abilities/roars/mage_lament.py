from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class MagesLamentRoar:
    bit_index = 8
    name = "mageslament"
    canonical_display_name = "Mage's Lament"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("mageslament", "mage's lament", "mages lament")

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
        messages = ["Mage's Lament peals out with a promise to leave enemy magic blunted against resistance."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            penalty = min(25, max(5, int(margin / 2)))
            duration = min(45, max(10, 12 + margin))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "modifiers": {"magic_attack": penalty},
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_mages_lament", payload)
            roar_service.set_target_effect(target, "effect_11815001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Mage's Lament leaves {', '.join(applied)} worse at forcing magic through resistance.")
        if resisted:
            messages.append(f"{', '.join(resisted)} endure the lament without losing their magical edge.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})