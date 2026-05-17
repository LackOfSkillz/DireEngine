from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class DeathsShriekRoar:
    bit_index = 6
    name = "deathsshriek"
    canonical_display_name = "Death's Shriek"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    prerequisite_bits = (4,)
    aliases = ("deathsshriek", "death's shriek", "shriek")

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
        messages = ["You hurl Death's Shriek into the room, aiming to drive foes to their knees with terror."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        rng = randomizer or (lambda _l, _h: 0)
        applied, resisted = [], []
        for target in list(targets or []):
            attack = roar_service.get_stat(actor, "discipline") + roar_service.get_stat(actor, "charisma") + roar_service.get_stat(actor, "agility") + roar_service.get_stat(actor, "strength")
            resist = roar_service.get_stat(target, "discipline") + roar_service.get_stat(target, "reflex") + roar_service.get_stat(target, "stamina")
            margin = int((attack * modifier) / 100) - resist + int(rng(-5, 10))
            if margin <= 10:
                resisted.append(getattr(target, "key", "someone"))
                continue
            duration = 3
            if hasattr(target, "db"):
                target.db.position = "kneeling"
            if hasattr(target, "set_position_state"):
                target.set_position_state("exposed")
            if hasattr(target, "set_roundtime"):
                target.set_roundtime(3)
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "position": "kneeling",
                "margin": margin,
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_deaths_shriek", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Death's Shriek forces {', '.join(applied)} to their knees in fear.")
        if resisted:
            messages.append(f"{', '.join(resisted)} refuse to bow before your shriek.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})