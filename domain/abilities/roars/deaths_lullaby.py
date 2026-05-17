from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class DeathsLullabyRoar:
    bit_index = 5
    name = "deathslullaby"
    canonical_display_name = "Death's Lullaby"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("deathslullaby", "death's lullaby", "lullaby")

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
        messages = ["Death's Lullaby ripples out from your throat, carrying enough fear to still enemy limbs."]
        rng = randomizer or (lambda low, _high: low)
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            attack = roar_service.get_stat(actor, "discipline") + (roar_service.get_stat(actor, "charisma") * 2)
            resist = (roar_service.get_stat(target, "discipline") * 2) + roar_service.get_stat(target, "reflex")
            margin = int((attack * modifier) / 100) - resist + int(rng(-5, 10))
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = 5
            roundtime = int(rng(1, 6))
            strength = min(5, max(1, int(margin / 6)))
            if hasattr(target, "set_roundtime"):
                target.set_roundtime(roundtime)
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "roundtime": roundtime,
                "fear_strength": strength,
                "margin": margin,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_deaths_lullaby", payload)
            roar_service.set_target_effect(target, "effect_11812001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Death's Lullaby leaves {', '.join(applied)} trembling in fear.")
        if resisted:
            messages.append(f"{', '.join(resisted)} laugh off your attempt to freeze them with fear.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})