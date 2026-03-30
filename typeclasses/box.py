from typeclasses.objects import Object


class Box(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_box = True
        self.db.strict_loot_box = False

        self.db.locked = True
        self.db.is_locked = True
        self.db.opened = False
        self.db.is_open = False
        self.db.lock_difficulty = 20
        self.db.contents = []
        self.db.weight = 5.0
        self.db.item_value = 25
        self.db.value = 25

        self.db.trap_present = False
        self.db.trap_difficulty = 0
        self.db.trap_type = None
        self.db.disarmed = False

        self.db.last_disarmed_trap = None

    def is_locked(self):
        return bool(getattr(self.db, "is_locked", getattr(self.db, "locked", True)))

    def is_open(self):
        return bool(getattr(self.db, "is_open", getattr(self.db, "opened", False)))

    def has_active_trap(self):
        return bool(self.db.trap_present and not self.db.disarmed)

    def can_be_opened(self):
        return (not self.is_locked()) and (not self.has_active_trap())