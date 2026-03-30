from .objects import Object


class Wearable(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.wearable = True
        self.db.slot = None
        if self.db.weight is None:
            self.db.weight = 1.0
        self.db.worn_by = None

    def clear_wear_state(self):
        wearer = getattr(self.db, "worn_by", None)
        if wearer and hasattr(wearer, "clear_equipment_item"):
            wearer.clear_equipment_item(self)
        self.db.worn_by = None

    def at_get(self, getter, **kwargs):
        super().at_get(getter, **kwargs)
        self.clear_wear_state()

    def at_drop(self, dropper, **kwargs):
        self.clear_wear_state()
        super().at_drop(dropper, **kwargs)

    def at_give(self, giver, getter, **kwargs):
        self.clear_wear_state()
        super().at_give(giver, getter, **kwargs)