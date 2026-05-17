from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


VOCAL_EXHAUSTION_ERROR = "Strain though you might, you cannot muster enough energy to vocalize your fighting spirit."


def standard_vocal_damage_check(vocal_profile):
    total = int((vocal_profile or {}).get("total", 0) or 0)
    if total > 20:
        return ActionResult.fail(errors=[VOCAL_EXHAUSTION_ERROR])
    return ActionResult.ok(data={"modifier": int((vocal_profile or {}).get("modifier", 100) or 100)})


def add_inspiration_vocal_damage(actor, vocal_service, bit_index):
    return vocal_service.add_vocal_damage(actor, VocalDamageService.INSPIRATION_CODE, bit_index)


def inspiration_strength(roar_service, actor, *, vocal_profile=None, randomizer=None):
    modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
    modifier = int((modifier * int(roar_service.get_roar_power_modifier(actor, "inspiration") or 100)) / 100)
    rng = randomizer or (lambda _low, _high: 0)
    base = roar_service.get_stat(actor, "discipline") + roar_service.get_stat(actor, "charisma") + roar_service._get_circle(actor)
    return max(1, int((base * modifier) / 30) + int(rng(-2, 5)))