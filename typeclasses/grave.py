import time

from evennia.objects.objects import DefaultObject
from evennia.utils.search import search_object

from .objects import ObjectParent


class Grave(ObjectParent, DefaultObject):
    """Owner-visible grave holding items left behind after corpse decay."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_grave = True
        self.db.owner_id = None
        self.db.owner_name = self.key
        self.db.creation_time = 0.0
        self.db.stored_items = []
        self.db.stored_coins = 0
        self.db.recovery_allowed = []
        self.db.grave_damage_max = 66
        self.db.last_grave_damage_tick = 0.0
        self.db.expiry_time = 0.0
        self.db.expiry_warned = False
        self.locks.add("get:false()")

    def get_owner(self):
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id <= 0:
            return None
        result = search_object(f"#{owner_id}")
        return result[0] if result else None

    def is_orphaned(self):
        return self.get_owner() is None

    def get_expiry_remaining(self):
        return max(0.0, float(getattr(self.db, "expiry_time", 0.0) or 0.0) - time.time())

    def is_owner(self, player):
        return int(getattr(player, "id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0)

    def get_recovery_allowed_ids(self):
        raw = getattr(self.db, "recovery_allowed", None) or []
        allowed = set()
        for entry in raw:
            try:
                value = int(entry)
            except (TypeError, ValueError):
                continue
            if value > 0:
                allowed.add(value)
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id > 0:
            allowed.add(owner_id)
        return allowed

    def is_recovery_allowed(self, player):
        player_id = int(getattr(player, "id", 0) or 0)
        return player_id > 0 and player_id in self.get_recovery_allowed_ids()

    def grant_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0:
            allowed.add(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def revoke_recovery_access(self, player):
        allowed = self.get_recovery_allowed_ids()
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        player_id = int(getattr(player, "id", 0) or 0)
        if player_id > 0 and player_id != owner_id:
            allowed.discard(player_id)
        self.db.recovery_allowed = sorted(allowed)
        return self.db.recovery_allowed

    def get_grave_damage(self, item):
        return max(0, min(int(getattr(self.db, "grave_damage_max", 66) or 66), int(getattr(getattr(item, "db", None), "grave_damage", 0) or 0)))

    def increment_grave_damage(self, amount=1):
        maximum = max(0, int(getattr(self.db, "grave_damage_max", 66) or 66))
        scale = 1.0
        if self.location and hasattr(self.location, "get_death_zone_profile"):
            scale = float(self.location.get_death_zone_profile().get("grave_damage_scale", 1.0) or 1.0)
        applied_amount = max(1, int(round(max(0.0, float(amount or 0.0)) * scale)))
        updated = {}
        for item in list(self.contents):
            current = int(getattr(getattr(item, "db", None), "grave_damage", 0) or 0)
            new_value = max(0, min(maximum, current + applied_amount))
            item.db.grave_damage = new_value
            updated[item.id] = new_value
        self.db.stored_items = sorted(updated)
        self.db.last_grave_damage_tick = getattr(self.db, "last_grave_damage_tick", 0.0) or 0.0
        return updated

    def _has_admin_access(self, accessing_obj):
        account = getattr(accessing_obj, "account", None)
        if not account:
            return False
        return account.check_permstring("Admin") or account.check_permstring("Developer")

    def access(self, accessing_obj, access_type="read", default=False, **kwargs):
        if access_type in {"view", "read", "search", "get"}:
            if self.is_recovery_allowed(accessing_obj) or self._has_admin_access(accessing_obj):
                return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)
            return False
        return super().access(accessing_obj, access_type=access_type, default=default, **kwargs)