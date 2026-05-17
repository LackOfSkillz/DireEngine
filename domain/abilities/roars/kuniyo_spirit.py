from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class KuniyoSpiritRoar:
    bit_index = 0
    name = "kuniyo"
    canonical_display_name = "Kuniyo's Spirit"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("kuniyo", "kuniyosspirit", "kuniyos", "kuniyospirit", "kuniyo's spirit")

    @classmethod
    def vocal_damage_check(cls, actor, vocal_profile):
        total = int((vocal_profile or {}).get("total", 0) or 0)
        if total > 20:
            return ActionResult.fail(
                errors=[
                    "Strain though you might, you cannot muster enough energy to vocalize your fighting spirit.",
                ]
            )
        return ActionResult.ok(data={"modifier": int((vocal_profile or {}).get("modifier", 100) or 100)})

    @classmethod
    def add_vocal_damage(cls, actor, vocal_service):
        return vocal_service.add_vocal_damage(actor, cls.vocal_damage_code, cls.bit_index)

    @classmethod
    def begin_roar(cls, actor, targets, roar_service, *, vocal_profile=None, randomizer=None):
        messages = [
            "Visualizing the technique as you were taught, you focus your entire being into expressing the Spirit of Kuniyo to your adversaries.",
        ]
        if not targets:
            messages.append("Your roar rolls outward, but there is no foe nearby to feel its bite.")
            return ActionResult.ok(messages=messages, data={"targets": [], "roar": cls.name})

        applied = []
        resisted = []
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            if margin <= 0:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = max(6, int((margin * 3) / 2))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "stun_vulnerability_pct": int((margin * 2) + 100),
                "source_id": getattr(actor, "id", None),
                "source_key": getattr(actor, "key", None),
            }
            roar_service.set_target_effect(target, "effect_2077001", payload)
            roar_service.set_target_effect(target, "barbarian_roar_kuniyo", payload)
            applied.append(getattr(target, "key", "someone"))

        if applied:
            messages.append(f"Kuniyo's Spirit tears into {', '.join(applied)}, leaving them easier to stun.")
        if resisted:
            messages.append(f"{', '.join(resisted)} laugh off your attempt to weaken their will to fight.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})