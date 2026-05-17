"""Generic magic slot pool service.

Spells are the first consumer of the pool. Additional consumers such as
magical feats can allocate from the same pool in later dispatches.
"""

from __future__ import annotations

from collections.abc import Mapping

from world.professions import get_profession_skillset_tier


MAGIC_USING_PROFESSIONS = frozenset(
    {
        "bard",
        "cleric",
        "empath",
        "moon_mage",
        "necromancer",
        "paladin",
        "ranger",
        "trader",
        "warrior_mage",
    }
)


class SlotService:
    """Owner of the shared magic-slot pool."""

    @staticmethod
    def _normalize_profession(value):
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _get_profession(character):
        if character is None:
            return ""
        getter = getattr(character, "get_profession", None)
        if callable(getter):
            return SlotService._normalize_profession(getter())
        db = getattr(character, "db", None)
        return SlotService._normalize_profession(
            getattr(db, "profession", getattr(character, "profession", ""))
        )

    @staticmethod
    def _get_circle(character):
        """Return the persisted circle without re-entering character bootstrap.

        Slot pool initialization runs inside Character.ensure_core_defaults(). Calling
        Character.get_circle() from here would re-enter that bootstrap path and can
        recurse when legacy magic users still have magic_slot_pool=None.
        """
        db = getattr(character, "db", None)
        raw_circle = getattr(db, "circle", getattr(character, "circle", None))
        if not isinstance(raw_circle, int) or raw_circle < 1:
            return 1
        return raw_circle

    @staticmethod
    def _get_magic_placement(character):
        profession = SlotService._get_profession(character)
        if profession not in MAGIC_USING_PROFESSIONS:
            return None
        return get_profession_skillset_tier(profession, "magic", default=None)

    @staticmethod
    def _compute_max_slots(placement, circle):
        normalized = str(placement or "").strip().lower()
        current_circle = max(0, int(circle or 0))
        if normalized not in {"primary", "secondary", "tertiary"} or current_circle <= 0:
            return 0
        if current_circle > 150:
            current_circle = 150

        if normalized == "primary":
            if current_circle <= 50:
                return current_circle
            if current_circle <= 100:
                return 50 + ((current_circle - 50) // 2)
            return 75 + max(0, (current_circle // 3) - 33)

        if normalized == "secondary":
            if current_circle <= 20:
                return current_circle
            if current_circle <= 100:
                return 20 + ((current_circle - 20) // 2)
            return 60 + max(0, (current_circle // 3) - 33)

        if current_circle == 1:
            return 1
        if current_circle <= 100:
            return 1 + (current_circle // 2)
        return 51 + max(0, (current_circle // 3) - 33)

    @staticmethod
    def get_pool(character):
        placement = SlotService._get_magic_placement(character)
        if placement is None:
            return None

        db = getattr(character, "db", None)
        if db is None:
            return None

        max_slots = SlotService._compute_max_slots(placement, SlotService._get_circle(character))
        raw_pool = getattr(db, "magic_slot_pool", None)
        if not isinstance(raw_pool, Mapping):
            raw_pool = {}

        normalized = {
            "max": max_slots,
            "allocations": {},
        }
        raw_allocations = raw_pool.get("allocations") if isinstance(raw_pool, Mapping) else None
        if isinstance(raw_allocations, Mapping):
            for category, entries in raw_allocations.items():
                normalized_category = str(category or "").strip().lower() or "misc"
                if isinstance(entries, Mapping):
                    normalized["allocations"][normalized_category] = {
                        str(item_id): max(0, int(cost or 0))
                        for item_id, cost in entries.items()
                    }
        normalized["allocations"].setdefault("spells", {})
        db.magic_slot_pool = normalized
        return normalized

    @staticmethod
    def get_used_slots(character):
        pool = SlotService.get_pool(character)
        if pool is None:
            return 0
        return sum(sum(category.values()) for category in pool["allocations"].values())

    @staticmethod
    def get_available_slots(character):
        pool = SlotService.get_pool(character)
        if pool is None:
            return 0
        return max(0, int(pool.get("max", 0) or 0) - SlotService.get_used_slots(character))

    @staticmethod
    def has_available_slots(character, count):
        return SlotService.get_available_slots(character) >= max(0, int(count or 0))

    @staticmethod
    def allocate(character, category, item_id, cost):
        requested = max(0, int(cost or 0))
        if requested == 0:
            return True

        pool = SlotService.get_pool(character)
        if pool is None or not SlotService.has_available_slots(character, requested):
            return False

        normalized_category = str(category or "").strip().lower() or "misc"
        normalized_item = str(item_id or "").strip().lower()
        if not normalized_item:
            return False

        allocations = pool["allocations"].setdefault(normalized_category, {})
        existing_cost = max(0, int(allocations.get(normalized_item, 0) or 0))
        delta = requested - existing_cost
        if delta > 0 and not SlotService.has_available_slots(character, delta):
            return False

        allocations[normalized_item] = requested
        getattr(character, "db").magic_slot_pool = pool
        return True

    @staticmethod
    def deallocate(character, category, item_id):
        pool = SlotService.get_pool(character)
        if pool is None:
            return 0

        normalized_category = str(category or "").strip().lower() or "misc"
        normalized_item = str(item_id or "").strip().lower()
        allocations = pool["allocations"].get(normalized_category)
        if not isinstance(allocations, Mapping):
            return 0

        freed = max(0, int(allocations.pop(normalized_item, 0) or 0))
        getattr(character, "db").magic_slot_pool = pool
        return freed

    @staticmethod
    def recompute_max(character):
        return SlotService.get_pool(character)