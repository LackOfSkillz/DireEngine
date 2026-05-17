from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class TrothfangButcheryRoar:
    bit_index = 2
    name = "trothfang"
    canonical_display_name = "Trothfang's Butchery"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("trothfang", "trothfangsbutchery", "trothfang's butchery")

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
        messages = ["Trothfang's Butchery surges through your roar, intent on sapping your enemies' physical surety."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            attack = roar_service.get_stat(actor, "discipline") + roar_service.get_stat(actor, "charisma") + roar_service.get_stat(actor, "strength") + roar_service.get_stat(actor, "agility")
            resist = roar_service.get_stat(target, "discipline") + roar_service.get_stat(target, "stamina") + roar_service.get_stat(target, "reflex")
            margin = int((attack * modifier) / 100) - resist + int((randomizer or (lambda _l, _h: 0))(-5, 10))
            if margin <= 1:
                resisted.append(getattr(target, "key", "someone"))
                continue
            penalty = -min(5, max(1, int(margin / 2)))
            duration = min(45, margin * 5)
            stat_modifiers = {"reflex": penalty}
            if margin > 10:
                stat_modifiers["agility"] = penalty
            if margin > 20:
                stat_modifiers["strength"] = penalty
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "stat_modifiers": stat_modifiers,
                "margin": margin,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_trothfang", payload)
            roar_service.set_target_effect(target, "effect_11809001", payload)
            if len(stat_modifiers) > 1:
                roar_service.set_target_effect(target, "effect_11809002", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Trothfang's Butchery leaves {', '.join(applied)} palpably weaker.")
        if resisted:
            messages.append(f"{', '.join(resisted)} weather the butchery in your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})