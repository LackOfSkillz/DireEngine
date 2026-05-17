from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class SerpentHissRoar:
    bit_index = 10
    name = "serpenthiss"
    canonical_display_name = "Serpent's Hiss of Warning"
    category = "intimidation"
    vocal_damage_code = VocalDamageService.INTIMIDATION_CODE
    aliases = ("serpenthiss", "serpent's hiss of warning", "serpents hiss")

    @staticmethod
    def _pick_flee_destination(target):
        room = getattr(target, "location", None)
        if room is None:
            return None
        for obj in list(getattr(room, "contents", []) or []):
            destination = getattr(obj, "destination", None)
            if destination and destination != room:
                return destination
        return None

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
        messages = ["Serpent's Hiss of Warning lashes out with enough terror to send enemies fleeing."]
        modifier = int((vocal_profile or {}).get("modifier", 100) or 100)
        applied, resisted = [], []
        for target in list(targets or []):
            margin = roar_service.calculate_margin(actor, target, style=cls.name, modifier=modifier, randomizer=randomizer)
            destination = cls._pick_flee_destination(target)
            if margin <= 8 or destination is None:
                resisted.append(getattr(target, "key", "someone"))
                continue
            origin = getattr(target, "location", None)
            if hasattr(target, "disengage"):
                target.disengage(emit_message=False)
            elif hasattr(target, "set_target"):
                target.set_target(None)
                if getattr(getattr(target, "db", None), "in_combat", None) is not None:
                    target.db.in_combat = False
            if hasattr(target, "move_to"):
                target.move_to(destination, quiet=True, move_type="barbarian_roar_flee")
            duration = min(12, max(5, int(margin / 4)))
            payload = {
                "name": cls.name,
                "expires_at": roar_service.now() + duration,
                "duration": duration,
                "margin": margin,
                "origin_room_id": int(getattr(origin, "id", 0) or 0),
                "destination_room_id": int(getattr(destination, "id", 0) or 0),
                "source_id": getattr(actor, "id", None),
            }
            roar_service.set_target_effect(target, "barbarian_roar_serpent_hiss", payload)
            roar_service.set_target_effect(target, "effect_11817001", payload)
            applied.append(getattr(target, "key", "someone"))
        if applied:
            messages.append(f"Serpent's Hiss sends {', '.join(applied)} running for the nearest exit.")
        if resisted:
            messages.append(f"{', '.join(resisted)} resist the urge to flee your warning hiss.")
        return ActionResult.ok(messages=messages, data={"targets": applied, "resisted": resisted, "roar": cls.name})