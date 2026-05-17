from collections.abc import Mapping
import random
import time

from engine.services.barbarian_saf_service import BarbarianSafService
from engine.services.result import ActionResult


class BerserkService:
    STATE_KEY = "barbarian_berserk"
    BLOODTHIRST_CODE = 8932001
    DANCE_CODE = 3387100
    BERSERK_CODE = 1740001
    FULL_STRENGTH_SKILL_CODE = 1740004
    DEFAULT_BERSERK = "berserk"

    @classmethod
    def _get_circle(cls, actor) -> int:
        getter = getattr(actor, "get_circle", None)
        if callable(getter):
            return max(1, int(getter() or 1))
        return max(1, int(getattr(getattr(actor, "db", None), "circle", 1) or 1))

    @classmethod
    def ensure_berserk_learned(cls, actor) -> bool:
        if not getattr(actor, "is_profession", None) or not actor.is_profession("barbarian"):
            return False
        if cls._get_circle(actor) < 2:
            return False
        abilities = list(getattr(getattr(actor, "db", None), "barbarian_abilities", None) or [])
        if cls.DEFAULT_BERSERK not in abilities:
            abilities.append(cls.DEFAULT_BERSERK)
            actor.db.barbarian_abilities = sorted(set(str(entry or "").strip().lower() for entry in abilities if str(entry or "").strip()))
            return True
        return False

    @classmethod
    def knows_berserk(cls, actor) -> bool:
        cls.ensure_berserk_learned(actor)
        abilities = {str(entry or "").strip().lower() for entry in list(getattr(getattr(actor, "db", None), "barbarian_abilities", None) or [])}
        return cls.DEFAULT_BERSERK in abilities

    @classmethod
    def _room_has_flag(cls, room, flag_name: str) -> bool:
        if room is None:
            return False
        normalized = str(flag_name or "").strip().lower()
        if not normalized:
            return False
        db_holder = getattr(room, "db", None)
        if db_holder is not None and bool(getattr(db_holder, normalized, False)):
            return True
        tags = getattr(room, "tags", None)
        if tags is not None:
            try:
                if bool(tags.has(normalized)):
                    return True
            except Exception:
                pass
        return False

    @classmethod
    def _is_droughtmans_maze(cls, room) -> bool:
        room_id = int(getattr(room, "id", getattr(room, "dbid", 0)) or 0)
        return 1051000 <= room_id <= 1053999

    @classmethod
    def _has_effect_code(cls, actor, code: int) -> bool:
        state_key = f"effect_{int(code)}"
        getter = getattr(actor, "get_state", None)
        if callable(getter) and getter(state_key):
            return True
        active_effects = getter("active_effects") if callable(getter) else {}
        if isinstance(active_effects, dict):
            for effect_map in active_effects.values():
                if isinstance(effect_map, dict) and str(code) in effect_map:
                    return True
        return False

    @classmethod
    def _set_effect_code(cls, actor, code: int, payload: dict):
        setter = getattr(actor, "set_state", None)
        if callable(setter):
            setter(f"effect_{int(code)}", dict(payload or {}))

    @classmethod
    def _clear_effect_code(cls, actor, code: int):
        clearer = getattr(actor, "clear_state", None)
        if callable(clearer):
            clearer(f"effect_{int(code)}")

    @classmethod
    def _clean_expired_state(cls, actor):
        getter = getattr(actor, "get_state", None)
        clearer = getattr(actor, "clear_state", None)
        if not callable(getter):
            return None
        data = getter(cls.STATE_KEY)
        if not isinstance(data, Mapping):
            return None
        expires_at = float(data.get("expires_at", 0.0) or 0.0)
        if expires_at and time.time() < expires_at:
            return dict(data)
        mm_bonus = int(data.get("mm_bonus", 0) or 0)
        current_mm = int(getattr(getattr(actor, "db", None), "mm", 1) or 1)
        actor.db.mm = max(1, current_mm - mm_bonus)
        current_hp = int(getattr(getattr(actor, "db", None), "hp", 0) or 0)
        max_hp = int(getattr(getattr(actor, "db", None), "max_hp", 0) or 0)
        if current_hp > max_hp:
            actor.db.hp = max_hp
        if callable(clearer):
            clearer(cls.STATE_KEY)
        cls._clear_effect_code(actor, cls.BERSERK_CODE)
        cls._clear_effect_code(actor, cls.FULL_STRENGTH_SKILL_CODE)
        return None

    @classmethod
    def get_active_berserk(cls, actor):
        return cls._clean_expired_state(actor)

    @classmethod
    def _get_melee_critter_target(cls, actor):
        target = actor.get_target() if hasattr(actor, "get_target") else None
        if cls._is_valid_melee_critter(actor, target):
            return target
        room = getattr(actor, "location", None)
        if room is None:
            return None
        for obj in list(getattr(room, "contents", []) or []):
            if cls._is_valid_melee_critter(actor, obj):
                return obj
        return None

    @classmethod
    def _is_valid_melee_critter(cls, actor, target) -> bool:
        if target is None or target == actor:
            return False
        if getattr(target, "location", None) != getattr(actor, "location", None):
            return False
        if not bool(getattr(getattr(target, "db", None), "is_npc", False)):
            return False
        if hasattr(target, "is_alive") and not target.is_alive():
            return False
        if hasattr(actor, "get_range") and actor.get_range(target) != "melee":
            return False
        return True

    @classmethod
    def _get_strength_percent(cls, saf_value: int) -> int:
        return max(0, 100 - max(0, int(saf_value or 0)))

    @classmethod
    def _get_tier_message(cls, saf_value: int) -> str:
        saf = max(0, int(saf_value or 0))
        if 76 <= saf <= 115:
            return "You gnash your teeth and tense every muscle in your body, but the violent rage lingers just beyond your grasp."
        if 0 <= saf <= 25:
            return "You sense the rage within you well up and explode in a violent whirlwind of dangerous power. The world dissolves in blood-red shadow, a blur of crimson and death fueled by bone, sinew, and muscle with savage strength!"
        if 26 <= saf <= 50:
            return "You unleash a savage war cry and draw upon reserves of bitter anger and innate bloodlust, snarling like a ravenous wolf before the kill!"
        return "You summon the vengeful wrath within you, bending every ounce of strength to feed your frenzied battlelust!"

    @classmethod
    def _get_hidden_message(cls) -> str:
        return "You leap from hiding, attempting to summon a Berserker Fury!"

    @classmethod
    def _get_stats(cls, actor) -> dict:
        get_stat = getattr(actor, "get_stat", None)
        if callable(get_stat):
            return {
                "strength": int(get_stat("strength") or 0),
                "reflex": int(get_stat("reflex") or 0),
                "discipline": int(get_stat("discipline") or 0),
                "stamina": int(get_stat("stamina") or 0),
                "charisma": int(get_stat("charisma") or 0),
                "agility": int(get_stat("agility") or 0),
            }
        stats = dict(getattr(getattr(actor, "db", None), "stats", {}) or {})
        return {
            "strength": int(stats.get("strength", 0) or 0),
            "reflex": int(stats.get("reflex", 0) or 0),
            "discipline": int(stats.get("discipline", 0) or 0),
            "stamina": int(stats.get("stamina", 0) or 0),
            "charisma": int(stats.get("charisma", 0) or 0),
            "agility": int(stats.get("agility", 0) or 0),
        }

    @classmethod
    def _calculate_of_bonus(cls, actor, strength_percent: int, *, roll: int) -> int:
        stats = cls._get_stats(actor)
        raw = stats["strength"] + stats["charisma"] + stats["reflex"] - (stats["discipline"] * 2)
        amount = int((raw * strength_percent) / 100)
        amount = int((amount * int(roll or 100)) / 100)
        return max(1, min(100, amount))

    @classmethod
    def _calculate_hp_bonus(cls, actor, strength_percent: int) -> int:
        max_hp = int(getattr(getattr(actor, "db", None), "max_hp", 0) or 0)
        return max(0, int((max_hp * strength_percent * 3 / 2 / 100) - 1))

    @classmethod
    def _calculate_mm_bonus(cls, actor) -> int:
        agility = cls._get_stats(actor)["agility"]
        return min(int(agility / 10) + 2, 8)

    @classmethod
    def _calculate_duration(cls, actor, strength_percent: int, *, roll: int) -> int:
        stats = cls._get_stats(actor)
        circle = cls._get_circle(actor)
        raw = int((stats["stamina"] * stats["reflex"] / 4) + stats["strength"] - (stats["discipline"] * 2) + stats["charisma"])
        raw = int((raw * int(roll or 100)) / 100)
        raw = int((raw * strength_percent) / 100)
        _circle = circle
        return max(20, raw)

    @classmethod
    def _calculate_stat_bonus(cls, actor, strength_percent: int, *, roll: int) -> int:
        stats = cls._get_stats(actor)
        circle = cls._get_circle(actor)
        raw = int(stats["strength"] + (stats["reflex"] / 2) - stats["discipline"] + (circle / 10))
        raw = int((raw * strength_percent) / 200)
        raw = int((raw * int(roll or 100)) / 100)
        cap = min(int((stats["strength"] + stats["discipline"]) / 4), 15)
        return max(1, min(cap, raw))

    @classmethod
    def can_berserk(cls, actor) -> ActionResult:
        if not getattr(actor, "is_profession", None) or not actor.is_profession("barbarian") or cls._get_circle(actor) < 2:
            return ActionResult.fail(errors=["You do not have the facilities to properly channel your rage."]) 

        room = getattr(actor, "location", None)
        if hasattr(actor, "is_dead") and actor.is_dead():
            return ActionResult.fail(errors=["The haunting sounds of distant battle echo all around you, fading into a black silence as quickly as they came."])
        if cls._room_has_flag(room, "silenced"):
            return ActionResult.fail(errors=["You can't do that here."])
        if cls._room_has_flag(room, "safehaven"):
            return ActionResult.fail(errors=["A deep sense of quiet is infused throughout this place, your Berserk lost beneath an overwhelming desire for tranquility."])
        if bool(getattr(getattr(actor, "db", None), "invisible", False)) or bool(getattr(getattr(actor, "db", None), "nonexist", False)) or bool(getattr(actor, "get_state", lambda _key: None)("invisible")):
            return ActionResult.fail(errors=["The pervasive stench of magical corruption splinters your attempt to Berserk, your inner fire shaken by its deep-rooted presence."])
        if bool(getattr(getattr(actor, "db", None), "unconscious", False)):
            return ActionResult.fail(errors=["You're unconscious!"])
        if cls._has_effect_code(actor, cls.BLOODTHIRST_CODE):
            return ActionResult.fail(errors=["Your rage already burns beneath the fury of a true bloodthirst!"])
        if cls._has_effect_code(actor, cls.DANCE_CODE):
            return ActionResult.fail(errors=["You cannot muster the rage to Berserk while your mind and body are focused on a Dance."])
        if cls.get_active_berserk(actor) or cls._has_effect_code(actor, cls.BERSERK_CODE):
            return ActionResult.fail(errors=["You are already berserking.  Yes, all that frothing and seething - it's YOU!"])
        if cls._is_droughtmans_maze(room):
            return ActionResult.fail(errors=["Something prevents you from doing that."])
        target = cls._get_melee_critter_target(actor)
        if target is None and not bool(getattr(getattr(actor, "db", None), "gmmode", False)):
            return ActionResult.fail(errors=["Without a foe to savage, your battle rage lingers just beyond your grasp!"])

        saf_value = BarbarianSafService.get_inner_fire(actor)
        if saf_value < 0:
            BarbarianSafService.set_inner_fire(actor, 0)
            saf_value = 0
        if 76 <= saf_value <= 115:
            return ActionResult.fail(errors=[cls._get_tier_message(saf_value)], data={"saf": saf_value, "strength_percent": 0})
        return ActionResult.ok(data={"saf": saf_value, "strength_percent": cls._get_strength_percent(saf_value), "target": target})

    @classmethod
    def berserk(cls, actor, *, randomizer=None) -> ActionResult:
        preflight = cls.can_berserk(actor)
        if not preflight.success:
            return preflight

        rng = randomizer or random.randint
        saf_value = int(preflight.data.get("saf", 0) or 0)
        strength_percent = int(preflight.data.get("strength_percent", 0) or 0)
        target = preflight.data.get("target")
        stats = cls._get_stats(actor)
        broke_stun = False
        hidden_reveal = False
        messages = []

        if hasattr(actor, "is_stunned") and actor.is_stunned() and saf_value < 76:
            if (stats["discipline"] * 2) > (stats["strength"] + stats["charisma"]):
                BarbarianSafService.set_inner_fire(actor, max(0, saf_value - stats["strength"] + (stats["discipline"] * 2)))
                actor.db.stunned = False
                actor.db.stunned_until = 0.0
                broke_stun = True
                messages.append("You summon all of your strength to shake off the stun!")

        if hasattr(actor, "is_hidden") and actor.is_hidden():
            hidden_reveal = True
            messages.append(cls._get_hidden_message())
            if hasattr(actor, "break_stealth"):
                actor.break_stealth()

        berserk_message = cls._get_tier_message(saf_value)
        messages.append(berserk_message)

        of_bonus = cls._calculate_of_bonus(actor, strength_percent, roll=int(rng(80, 120)))
        hp_bonus = cls._calculate_hp_bonus(actor, strength_percent)
        mm_bonus = 0
        if not bool(getattr(getattr(actor, "db", None), "webbed", False)):
            mm_bonus = cls._calculate_mm_bonus(actor)
            actor.db.mm = int(getattr(getattr(actor, "db", None), "mm", 1) or 1) + mm_bonus
            if str(getattr(getattr(actor, "db", None), "position", "standing") or "standing").strip().lower() in {"prone", "sitting", "kneeling"}:
                actor.db.position = "standing"
                messages.append("You spring to your feet in a sudden burst of grace borne of vicious strength!")
        else:
            messages.append("You struggle against the webbing, becoming more enraged!")

        if hasattr(actor, "set_fatigue"):
            actor.set_fatigue(int(getattr(getattr(actor, "db", None), "max_fatigue", 100) or 100))
        else:
            actor.db.fatigue = int(getattr(getattr(actor, "db", None), "max_fatigue", 100) or 100)

        duration = cls._calculate_duration(actor, strength_percent, roll=int(rng(90, 110)))
        stat_bonus = cls._calculate_stat_bonus(actor, strength_percent, roll=int(rng(70, 130)))
        stat_bonuses = {"strength": min(stat_bonus, max(1, int(stats["strength"] / 2) or 1))}
        if cls._get_circle(actor) > 20:
            stat_bonuses["charisma"] = min(stat_bonus, max(1, int(stats["charisma"] / 2) or 1))
        if strength_percent > 75:
            stat_bonuses["reflex"] = min(stat_bonus, max(1, int(stats["reflex"] / 2) or 1))

        before_hp = int(getattr(getattr(actor, "db", None), "hp", 0) or 0)
        if hp_bonus > 0:
            actor.db.hp = before_hp + hp_bonus

        final_saf = BarbarianSafService.apply_berserk_cost(actor)
        expires_at = time.time() + duration
        payload = {
            "name": cls.DEFAULT_BERSERK,
            "started_at": time.time(),
            "expires_at": expires_at,
            "duration": duration,
            "strength_percent": strength_percent,
            "hp_bonus": hp_bonus,
            "mm_bonus": mm_bonus,
            "stat_bonuses": dict(stat_bonuses),
            "of_bonus": of_bonus,
            "target_id": getattr(target, "id", None),
            "target_key": getattr(target, "key", None),
            "broke_stun": broke_stun,
            "revealed_from_hidden": hidden_reveal,
            "post_berserk_saf": final_saf,
        }
        setter = getattr(actor, "set_state", None)
        if callable(setter):
            setter(cls.STATE_KEY, payload)
        cls._set_effect_code(actor, cls.BERSERK_CODE, {"duration": duration, "strength_percent": strength_percent, "of_bonus": of_bonus})
        if strength_percent > 75:
            cls._set_effect_code(actor, cls.FULL_STRENGTH_SKILL_CODE, {"duration": duration + 5, "strength_percent": strength_percent, "bonus": of_bonus})
        return ActionResult.ok(data=payload, messages=messages)