from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class MagicsBaneRoar:
    bit_index = 7
    name = "magicsbane"
    canonical_display_name = "Magic's Bane"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("magicsbane", "magic's bane", "magics bane")

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
        messages = ["Magic's Bane spills from your throat, aimed at unraveling enemy confidence in mana itself."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        rng = randomizer or (lambda _l, _h: 0)
        applied, resisted = [], []
        for target in list(targets or []):
            attack = roar_service.get_stat(actor, "discipline") + roar_service.get_stat(actor, "charisma") + roar_service.get_stat(actor, "strength")
            resist = (roar_service.get_stat(target, "discipline") * 2) + roar_service.get_stat(target, "reflex")
            margin = int((attack * modifier) / 100) - resist + int(rng(-5, 10))
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            penalty = min(100, max(3, margin * 3))
            duration = min(60, max(8, margin * 2))
            skill_modifiers = {"primary_magic": -penalty, "magical_devices": -penalty}
            if margin > 50:
                skill_modifiers["harness"] = -penalty
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "skill_modifiers": skill_modifiers,
                "modifiers": {"magic_attack": penalty, "magic_defense": penalty},
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_magics_bane", payload)
            roar_service.set_target_effect(target, "effect_11814001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Magic's Bane leaves {', '.join(applied)} less confident in their ability to manipulate mana streams.")
        if resisted:
            messages.append(f"{', '.join(resisted)} shrug off the thinning edge of your anti-magic roar.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})