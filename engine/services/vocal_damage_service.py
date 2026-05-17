import random
import time
from collections.abc import Mapping


class VocalDamageService:
    INTIMIDATION_CODE = 3089001
    INSPIRATION_CODE = 3089002
    STATE_KEY = "barbarian_vocal_damage"

    TIER_MESSAGES = (
        (0, 0, "You feel ready to defeat an army!"),
        (1, 7, "You feel ready to defeat all challengers."),
        (8, 13, "You feel worn but still ready to meet a challenge."),
        (14, 17, "You feel depleted and less than inspired."),
        (18, 20, "You feel weary of proclaiming your lust for battle."),
        (21, 999, "Your voice was nearly stolen by the weakness of your will to press on."),
    )

    @classmethod
    def _state_for(cls, actor):
        getter = getattr(actor, "get_state", None)
        if callable(getter):
            data = getter(cls.STATE_KEY)
            if isinstance(data, Mapping):
                return {
                    str(code): {
                        str(bit): [float(entry or 0.0) for entry in list(entries or []) if float(entry or 0.0) > 0.0]
                        for bit, entries in dict(code_map or {}).items()
                    }
                    for code, code_map in dict(data or {}).items()
                }
        return {}

    @classmethod
    def _set_state(cls, actor, data):
        setter = getattr(actor, "set_state", None)
        clearer = getattr(actor, "clear_state", None)
        if data:
            if callable(setter):
                setter(cls.STATE_KEY, data)
        elif callable(clearer):
            clearer(cls.STATE_KEY)
        cls._sync_effect_states(actor, data)

    @classmethod
    def _sync_effect_states(cls, actor, data):
        setter = getattr(actor, "set_state", None)
        clearer = getattr(actor, "clear_state", None)
        if not callable(setter) or not callable(clearer):
            return
        for code in (cls.INTIMIDATION_CODE, cls.INSPIRATION_CODE):
            code_map = dict((data or {}).get(str(code), {}) or {})
            if not code_map:
                clearer(f"effect_{code}")
                continue
            total = 0
            expires_at = 0.0
            for entries in code_map.values():
                total += len(list(entries or []))
                for expiry in list(entries or []):
                    expires_at = max(expires_at, float(expiry or 0.0))
            setter(
                f"effect_{code}",
                {
                    "code": code,
                    "total": total,
                    "expires_at": expires_at,
                    "entries": code_map,
                },
            )

    @classmethod
    def _purge_expired(cls, actor):
        now = time.time()
        data = cls._state_for(actor)
        cleaned = {}
        for code, code_map in data.items():
            active_map = {}
            for bit_index, entries in code_map.items():
                active_entries = [float(entry) for entry in list(entries or []) if float(entry or 0.0) > now]
                if active_entries:
                    active_map[str(bit_index)] = active_entries
            if active_map:
                cleaned[str(code)] = active_map
        if cleaned != data:
            cls._set_state(actor, cleaned)
        return cleaned

    @classmethod
    def _get_stat(cls, actor, name):
        get_stat = getattr(actor, "get_stat", None)
        if callable(get_stat):
            return int(get_stat(name) or 0)
        stats = dict(getattr(getattr(actor, "db", None), "stats", {}) or {})
        return int(stats.get(str(name or "").strip().lower(), 0) or 0)

    @classmethod
    def _get_vocal_lore(cls, actor):
        getter = getattr(actor, "get_skill", None)
        if callable(getter):
            for skill_name in ("vocal_lore", "performing", "scholarship"):
                value = int(getter(skill_name) or 0)
                if value > 0:
                    return value
        return 0

    @classmethod
    def get_vocal_damage_duration(cls, actor, *, randomizer=None) -> int:
        rng = randomizer or random.randint
        charisma = cls._get_stat(actor, "charisma")
        discipline = cls._get_stat(actor, "discipline")
        vocal_lore = cls._get_vocal_lore(actor)
        duration = int(165 - charisma - (discipline / 2) - (vocal_lore / 15) + int(rng(-5, 5)))
        return max(90, duration)

    @classmethod
    def add_vocal_damage(cls, actor, code: int, bit_index: int, amount: int = 1, *, randomizer=None):
        if amount <= 0:
            return cls.get_total_vocal_damage(actor)
        data = cls._purge_expired(actor)
        code_key = str(int(code))
        bit_key = str(int(bit_index))
        code_map = dict(data.get(code_key, {}) or {})
        entries = [float(entry) for entry in list(code_map.get(bit_key, []) or [])]
        expires_at = time.time() + cls.get_vocal_damage_duration(actor, randomizer=randomizer)
        for _ in range(int(amount or 0)):
            entries.append(expires_at)
        code_map[bit_key] = entries
        data[code_key] = code_map
        cls._set_state(actor, data)
        return cls.get_total_vocal_damage(actor)

    @classmethod
    def clear_all_vocal_damage(cls, actor):
        cls._set_state(actor, {})
        return {"total": 0, "modifier": 100, "tier": 0, "message": cls.TIER_MESSAGES[0][2], "codes": {}}

    @classmethod
    def get_total_vocal_damage(cls, actor):
        data = cls._purge_expired(actor)
        total = 0
        code_totals = {}
        for code, code_map in data.items():
            amount = sum(len(list(entries or [])) for entries in dict(code_map or {}).values())
            code_totals[str(code)] = amount
            total += amount
        modifier = cls._modifier_from_total(total)
        tier, message = cls._tier_message(total)
        return {
            "total": total,
            "modifier": modifier,
            "tier": tier,
            "message": message,
            "codes": code_totals,
        }

    @classmethod
    def _modifier_from_total(cls, total: int) -> int:
        amount = int(total or 0)
        if amount <= 0:
            return 100
        if 1 <= amount <= 7:
            return int(100 - ((amount * 3) / 2))
        if 8 <= amount <= 13:
            return int(105 - ((amount * 5) / 2))
        if 14 <= amount <= 17:
            return int(100 - ((amount * amount * amount) / 80))
        if 18 <= amount <= 20:
            return int(110 - (amount * 5))
        return 0

    @classmethod
    def _tier_message(cls, total: int):
        amount = int(total or 0)
        for tier_index, (minimum, maximum, message) in enumerate(cls.TIER_MESSAGES):
            if minimum <= amount <= maximum:
                return tier_index, message
        return len(cls.TIER_MESSAGES) - 1, cls.TIER_MESSAGES[-1][2]

    @classmethod
    def get_exhaustion_tier(cls, actor):
        summary = cls.get_total_vocal_damage(actor)
        return {
            "tier": summary["tier"],
            "message": summary["message"],
            "total": summary["total"],
            "modifier": summary["modifier"],
        }