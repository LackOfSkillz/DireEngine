import time
from collections.abc import Mapping

from domain.abilities.dances.registry import DANCE_BY_BIT, get_dance_definition
from engine.services.result import ActionResult


class DanceService:
    STATE_KEY = "barbarian_active_dance"
    MAIN_EFFECT_CODE = 3387100
    CYCLIC_EFFECT_CODE = 3387001

    @classmethod
    def now(cls):
        return time.time()

    @classmethod
    def _is_barbarian(cls, actor) -> bool:
        checker = getattr(actor, "is_profession", None)
        return bool(callable(checker) and checker("barbarian"))

    @classmethod
    def _get_circle(cls, actor) -> int:
        getter = getattr(actor, "get_circle", None)
        if callable(getter):
            return max(1, int(getter() or 1))
        return max(1, int(getattr(getattr(actor, "db", None), "circle", 1) or 1))

    @classmethod
    def _get_spellbook2(cls, actor) -> int:
        getter = getattr(actor, "get_spellbook2", None)
        if callable(getter):
            return max(0, int(getter() or 0))
        return max(0, int(getattr(getattr(actor, "db", None), "spellbook2", 0) or 0))

    @classmethod
    def _set_spellbook2(cls, actor, value):
        setter = getattr(actor, "set_spellbook2", None)
        if callable(setter):
            return setter(value)
        actor.db.spellbook2 = max(0, int(value or 0))
        return actor.db.spellbook2

    @classmethod
    def has_known_dance_bit(cls, actor, bit_index: int) -> bool:
        return bool(cls._get_spellbook2(actor) & (1 << int(bit_index)))

    @classmethod
    def set_known_dance(cls, actor, bit_index: int):
        definition = DANCE_BY_BIT.get(int(bit_index))
        if definition is None:
            return ActionResult.fail(errors=["Unknown dance."])
        if not cls._is_barbarian(actor):
            return ActionResult.fail(errors=["Only Barbarians may learn dances."])
        if cls._get_circle(actor) < int(definition.required_level):
            return ActionResult.fail(errors=["You are not yet seasoned enough to learn that dance."])
        cls._set_spellbook2(actor, cls._get_spellbook2(actor) | (1 << int(bit_index)))
        return ActionResult.ok(data={"bit_index": int(bit_index), "spellbook2": cls._get_spellbook2(actor)})

    @classmethod
    def clear_known_dance(cls, actor, bit_index: int):
        cls._set_spellbook2(actor, cls._get_spellbook2(actor) & ~(1 << int(bit_index)))
        return ActionResult.ok(data={"bit_index": int(bit_index), "spellbook2": cls._get_spellbook2(actor)})

    @classmethod
    def get_known_dances(cls, actor):
        return [definition for bit_index, definition in sorted(DANCE_BY_BIT.items()) if cls.has_known_dance_bit(actor, bit_index)]

    @classmethod
    def get_known_dance_names(cls, actor):
        return [definition.name for definition in cls.get_known_dances(actor)]

    @classmethod
    def _set_state(cls, actor, key: str, payload: dict):
        setter = getattr(actor, "set_state", None)
        if callable(setter):
            setter(key, dict(payload or {}))

    @classmethod
    def _clear_state(cls, actor, key: str):
        clearer = getattr(actor, "clear_state", None)
        if callable(clearer):
            clearer(key)

    @classmethod
    def _get_state(cls, actor, key: str):
        getter = getattr(actor, "get_state", None)
        if callable(getter):
            return getter(key)
        return None

    @classmethod
    def _get_ccp(cls, actor) -> int:
        getter = getattr(actor, "get_barbarian_dance_ccp", None)
        if callable(getter):
            return max(1, int(getter() or 1))
        return max(1, int(getattr(getattr(actor, "db", None), "ccp", 100) or 100))

    @classmethod
    def _get_armor_penalty(cls, actor) -> int:
        getter = getattr(actor, "get_barbarian_dance_armor_penalty", None)
        if callable(getter):
            return max(0, min(100, int(getter() or 0)))
        return max(0, min(100, int(getattr(getattr(actor, "db", None), "armor_penalty", 0) or 0)))

    @classmethod
    def _get_encumbrance(cls, actor) -> int:
        getter = getattr(actor, "get_barbarian_dance_encumbrance", None)
        if callable(getter):
            return max(0, int(getter() or 0))
        db = getattr(actor, "db", None)
        return max(0, int(getattr(db, "encumberance", getattr(db, "encumbrance", 0)) or 0))

    @classmethod
    def compute_duration_seconds(cls, actor, definition, *, started_at=None) -> int:
        armor_factor = max(1, int(100 - (cls._get_armor_penalty(actor) / 2)))
        encumbrance = cls._get_encumbrance(actor)
        encumbrance_factor = 100
        if 0 < encumbrance < 100:
            encumbrance_factor = int((100 - encumbrance + 100) / 2)
        encumbrance_factor = max(1, min(100, int(encumbrance_factor)))
        minutes = int((cls._get_ccp(actor) / 4) * armor_factor * encumbrance_factor / (10000 * max(1, int(definition.bit_index))))
        minutes = int(minutes + 13 - int(definition.bit_index))
        minutes = max(1, min(25, minutes))
        remaining = minutes * 60
        if started_at is not None:
            remaining -= int(max(0.0, cls.now() - float(started_at or 0.0)))
        return max(0, int(remaining))

    @classmethod
    def get_active_dance(cls, actor):
        payload = cls._get_state(actor, cls.STATE_KEY)
        if not isinstance(payload, Mapping):
            return None
        started_at = float(payload.get("started_at", 0.0) or 0.0)
        definition = DANCE_BY_BIT.get(int(payload.get("bit_index", 0) or 0))
        if definition is None:
            cls.end_dance(actor, emit_message=False)
            return None
        remaining = cls.compute_duration_seconds(actor, definition, started_at=started_at)
        if remaining <= 0:
            cls.end_dance(actor, emit_message=False)
            return None
        refreshed = dict(payload)
        refreshed["expires_at"] = cls.now() + remaining
        cls._set_state(actor, cls.STATE_KEY, refreshed)
        cls._set_state(actor, f"effect_{cls.MAIN_EFFECT_CODE}", refreshed)
        cls._set_state(actor, f"effect_{cls.CYCLIC_EFFECT_CODE}", {"bit_index": refreshed["bit_index"], "dance_name": refreshed["name"], "expires_at": refreshed["expires_at"], "value2": refreshed["bit_index"]})
        return refreshed

    @classmethod
    def get_payload(cls, actor):
        active = cls.get_active_dance(actor)
        if not isinstance(active, Mapping):
            return {}
        return dict(active)

    @classmethod
    def can_dance(cls, actor, dance_name: str | None = None):
        if not cls._is_barbarian(actor):
            return ActionResult.fail(errors=["You are not following the Barbarian path."])
        if getattr(actor, "get_active_barbarian_berserk", None) and actor.get_active_barbarian_berserk():
            return ActionResult.fail(errors=["Your berserk rage leaves no room for the measured focus of a battle dance."])
        if not dance_name:
            names = [definition.canonical_display_name for definition in cls.get_known_dances(actor)]
            if not names:
                return ActionResult.ok(messages=["You have not yet learned any battle dances."], data={"known": []})
            return ActionResult.ok(messages=["Known dances: " + ", ".join(names)], data={"known": names})
        definition = get_dance_definition(dance_name)
        if definition is None:
            return ActionResult.fail(errors=["You do not know that battle dance."])
        if not cls.has_known_dance_bit(actor, definition.bit_index):
            return ActionResult.fail(errors=["You have not received the proper instruction in that dance."])
        return ActionResult.ok(data={"definition": definition})

    @classmethod
    def begin_dance(cls, actor, dance_name: str | None = None):
        check = cls.can_dance(actor, dance_name)
        if not check.success or not dance_name:
            return check
        definition = check.data["definition"]
        messages = []
        active = cls.get_active_dance(actor)
        if isinstance(active, Mapping) and str(active.get("name")) != definition.name:
            cls.end_dance(actor, emit_message=False)
            messages.append("You feel your inner fire cool, as the adrenaline pumping effect of your battle dance ends.")
        started_at = cls.now()
        duration = cls.compute_duration_seconds(actor, definition, started_at=started_at)
        payload = definition.build_payload(actor, cls)
        payload.update({
            "name": definition.name,
            "display_name": definition.canonical_display_name,
            "bit_index": int(definition.bit_index),
            "started_at": started_at,
            "expires_at": started_at + duration,
            "duration_seconds": duration,
        })
        cls._set_state(actor, cls.STATE_KEY, payload)
        cls._set_state(actor, f"effect_{cls.MAIN_EFFECT_CODE}", payload)
        cls._set_state(actor, f"effect_{cls.CYCLIC_EFFECT_CODE}", {"bit_index": definition.bit_index, "dance_name": definition.name, "expires_at": started_at + duration, "value2": definition.bit_index})
        messages.append(f"You settle into the Dance of the {definition.canonical_display_name}.")
        if callable(getattr(actor, "sync_client_state", None)):
            actor.sync_client_state()
        return ActionResult.ok(messages=messages, data={"dance": definition.name, "duration_seconds": duration})

    @classmethod
    def end_dance(cls, actor, *, emit_message: bool = True):
        active = cls._get_state(actor, cls.STATE_KEY)
        if not isinstance(active, Mapping):
            return ActionResult.ok(messages=[])
        cls._clear_state(actor, cls.STATE_KEY)
        cls._clear_state(actor, f"effect_{cls.MAIN_EFFECT_CODE}")
        cls._clear_state(actor, f"effect_{cls.CYCLIC_EFFECT_CODE}")
        if callable(getattr(actor, "sync_client_state", None)):
            actor.sync_client_state()
        messages = ["You feel your inner fire cool, as the adrenaline pumping effect of your battle dance ends."] if emit_message else []
        return ActionResult.ok(messages=messages, data={"dance": active.get("name")})

    @classmethod
    def tick_active_dance(cls, actor):
        active = cls.get_active_dance(actor)
        if not isinstance(active, Mapping):
            return ActionResult.ok(messages=[])
        return ActionResult.ok(data={"dance": active.get("name"), "expires_at": active.get("expires_at")})

    @classmethod
    def _get_map_value(cls, actor, key: str, name: str) -> int:
        payload = cls.get_payload(actor)
        source = dict(payload.get(key) or {})
        normalized = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
        return int(source.get(normalized, 0) or 0)

    @classmethod
    def get_stat_modifier(cls, actor, stat_name: str) -> int:
        return cls._get_map_value(actor, "stat_modifiers", stat_name)

    @classmethod
    def get_skill_modifier(cls, actor, skill_name: str) -> int:
        return cls._get_map_value(actor, "skill_modifiers", skill_name)

    @classmethod
    def get_offense_bonus(cls, actor, bonus_name: str) -> int:
        return cls._get_map_value(actor, "offense_bonuses", bonus_name)

    @classmethod
    def get_defense_bonus(cls, actor, defense_name: str) -> int:
        return cls._get_map_value(actor, "defense_bonuses", defense_name)

    @classmethod
    def get_balance_bonus(cls, actor) -> int:
        return max(0, int(cls.get_payload(actor).get("balance_bonus", 0) or 0))

    @classmethod
    def get_engagement_speed_bonus(cls, actor) -> int:
        return max(0, int(cls.get_payload(actor).get("engagement_speed_bonus", 0) or 0))

    @classmethod
    def get_roar_power_modifier(cls, actor, category: str) -> int:
        active = cls.get_active_dance(actor)
        if not isinstance(active, Mapping):
            return 100
        mapping = dict(active.get("roar_power_modifiers") or {})
        return int(mapping.get(str(category or "").strip().lower(), 100) or 100)