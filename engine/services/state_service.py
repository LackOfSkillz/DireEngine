from engine.services.injury_service import InjuryService
from engine.services.result import ActionResult


class StateService:

    @staticmethod
    def apply_damage(target, damage, location=None, damage_type="impact", critical=False):
        damage = int(damage or 0)
        if damage <= 0:
            return ActionResult.ok(data={"amount": 0, "location": location, "damage_type": damage_type, "critical": bool(critical)})

        final_damage = damage
        if location is not None and hasattr(target, "apply_empath_unity_share"):
            final_damage = int(target.apply_empath_unity_share(location, damage, damage_type=damage_type) or 0)
        if final_damage <= 0:
            return ActionResult.ok(data={"amount": 0, "location": location, "damage_type": damage_type, "critical": bool(critical)})

        target.set_hp((target.db.hp or 0) - final_damage)
        wound_result = ActionResult.ok(data={})
        if location is not None:
            wound_result = InjuryService.apply_hit_wound(target, location, final_damage, damage_type=damage_type, critical=critical)

        if getattr(target, "is_empath", lambda: False)() and target.get_empath_link_state(require_local=False, emit_break_messages=False):
            target.decay_empath_link_stability(amount=None, reason="damage", emit_message=True)
        if getattr(target, "is_empath", lambda: False)() and target.get_empath_unity_state():
            target.decay_empath_unity_stability(event_key="damage", emit_message=True)

        data = {"amount": final_damage, "location": location, "damage_type": damage_type, "critical": bool(critical)}
        data.update(dict(wound_result.data or {}))
        data.setdefault("injury_events", list((wound_result.data or {}).get("injury_events", []) or []))
        return ActionResult.ok(data=data)

    @staticmethod
    def apply_roundtime(character, duration, ambush=False):
        if ambush:
            character.apply_thief_roundtime(duration)
            return ActionResult.ok(data={"roundtime": float(duration or 0.0), "ambush": True})
        character.set_roundtime(duration)
        return ActionResult.ok(data={"roundtime": float(duration or 0.0), "ambush": False})

    @staticmethod
    def apply_balance(character, amount):
        character.set_balance(amount)
        return ActionResult.ok(data={"balance": amount})

    @staticmethod
    def apply_fatigue(character, amount):
        character.set_fatigue(amount)
        return ActionResult.ok(data={"fatigue": amount})