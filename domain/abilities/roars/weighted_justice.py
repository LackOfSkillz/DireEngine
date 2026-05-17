from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class WeightedJusticeRoar:
    bit_index = 15
    name = "weightedjustice"
    canonical_display_name = "Weighted Justice"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("weightedjustice", "weighted justice", "justice")

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
        messages = ["Weighted Justice crashes down in your roar, aimed at tearing weapons from enemy hands."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            weapon = target.get_wielded_weapon() if hasattr(target, "get_wielded_weapon") else (target.get_weapon() if hasattr(target, "get_weapon") else None)
            if margin <= 0 or weapon is None or getattr(target, "location", None) is None:
                resisted.append(getattr(target, "key", "someone"))
                continue
            if hasattr(target, "clear_equipped_weapon"):
                target.clear_equipped_weapon()
            weapon.move_to(target.location, quiet=True, use_destination=False)
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + 3,
                "duration": 3,
                "margin": margin,
                "dropped_weapon": getattr(weapon, "key", "weapon"),
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_weighted_justice", payload)
            roar_service.set_target_effect(target, "effect_11822001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Weighted Justice tears weapons free from {', '.join(applied)}.")
        if resisted:
            messages.append(f"{', '.join(resisted)} keep hold of their weapons despite the roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})