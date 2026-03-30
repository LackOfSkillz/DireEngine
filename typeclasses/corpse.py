from collections.abc import Mapping

from evennia import search_object
from evennia.objects.objects import DefaultObject

from .objects import ObjectParent


class Corpse(ObjectParent, DefaultObject):
    """Minimal corpse object used by death, depart, and resurrection flows."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_corpse = True
        self.db.owner_id = None
        self.db.owner_name = self.key
        self.db.death_timestamp = 0.0
        self.db.decay_time = 0.0
        self.db.favor_snapshot = None
        self.locks.add("get:false()")

    def is_owner(self, player):
        return int(getattr(player, "id", 0) or 0) == int(getattr(self.db, "owner_id", 0) or 0)

    def get_owner(self):
        owner_id = int(getattr(self.db, "owner_id", 0) or 0)
        if owner_id <= 0:
            return None
        result = search_object(f"#{owner_id}")
        return result[0] if result else None

    def get_favor_snapshot(self):
        snapshot = getattr(self.db, "favor_snapshot", None)
        return dict(snapshot) if isinstance(snapshot, Mapping) else None
