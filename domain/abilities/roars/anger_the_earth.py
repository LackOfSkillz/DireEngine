from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class AngerTheEarthRoar:
    bit_index = 16
    name = "angertheearth"
    canonical_display_name = "Anger the Earth"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("angertheearth", "anger the earth", "earth")

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
        messages = ["Anger the Earth rolls out under your roar and steals away your enemy's footing."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            balance_penalty = min(25, max(8, int(margin / 2)))
            current_balance, _max_balance = target.get_balance() if hasattr(target, "get_balance") else (100, 100)
            if hasattr(target, "set_balance"):
                target.set_balance(max(0, int(current_balance or 0) - balance_penalty))
            duration = min(30, max(8, 8 + margin))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "balance_penalty": balance_penalty,
                "balance_recovery_penalty": max(1, int(balance_penalty / 8)),
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_anger_the_earth", payload)
            roar_service.set_target_effect(target, "effect_11823001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Anger the Earth knocks the balance out of {', '.join(applied)}.")
        if resisted:
            messages.append(f"{', '.join(resisted)} keep their footing despite the earthbound fury in your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})