from .wearable_containers import WearableContainer


class Sheath(WearableContainer):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_sheath = True
        self.db.slot = None
        self.db.capacity = 1
        self.db.allowed_types = ["weapon"]
        self.db.sheath_type = "generic"
        self.db.allowed_weapon_types = []
        self.db.desc = "A practical sheath sized to carry a single weapon."

    def can_hold_item(self, weapon):
        can_hold, msg = super().can_hold_item(weapon)
        if not can_hold:
            return can_hold, msg

        allowed = self.db.allowed_weapon_types or []
        weapon_type = getattr(weapon.db, "weapon_type", None)
        if not allowed:
            return True, None
        if weapon_type not in allowed:
            return False, "That does not fit."
        return True, None

    def return_appearance(self, looker):
        return super().return_appearance(looker)


class BeltSheath(Sheath):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "belt sheath"
        self.db.slot = "waist"
        self.db.sheath_type = "belt"
        self.db.allowed_weapon_types = ["light_edge", "blunt"]
        self.db.desc = "A belt-worn sheath sized for lighter blades and clubs."


class BackScabbard(Sheath):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "back scabbard"
        self.db.slot = "back"
        self.db.sheath_type = "back"
        self.db.allowed_weapon_types = ["heavy_edge", "polearm"]
        self.db.desc = "A back-worn scabbard built for larger weapons."