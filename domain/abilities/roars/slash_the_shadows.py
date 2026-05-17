from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class SlashTheShadowsRoar:
    bit_index = 17
    name = "slashtheshadows"
    canonical_display_name = "Slash the Shadows"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("slashtheshadows", "slash the shadows", "shadows")

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
        messages = ["Slash the Shadows cuts through concealment and makes secrecy harder to hold."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            broke_stealth = False
            if hasattr(target, "is_hidden") and target.is_hidden() and hasattr(target, "break_stealth"):
                target.break_stealth()
                broke_stealth = True
            if bool(getattr(getattr(target, "db", None), "invisible", False)):
                target.db.invisible = False
                broke_stealth = True
            if hasattr(target, "clear_state") and getattr(target, "get_state", lambda *_args, **_kwargs: None)("invisible"):
                target.clear_state("invisible")
                broke_stealth = True
            penalty = -min(30, max(10, margin))
            duration = min(45, max(10, 10 + margin))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "broke_stealth": broke_stealth,
                "skill_modifiers": {"stealth": penalty},
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_slash_the_shadows", payload)
            roar_service.set_target_effect(target, "effect_11824001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Slash the Shadows strips concealment and stealth from {', '.join(applied)}.")
        if resisted:
            messages.append(f"{', '.join(resisted)} preserve their secrets despite your roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})