from .wearables import Wearable


ARMOR_PRESETS = {
    "light_armor": {"protection": 2, "hindrance": 1, "weight": 5.0},
    "chain_armor": {"protection": 4, "hindrance": 3, "weight": 10.0},
    "brigandine": {"protection": 6, "hindrance": 4, "weight": 12.0},
    "plate_armor": {"protection": 8, "hindrance": 6, "weight": 15.0},
}


class Armor(Wearable):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.item_type = "armor"
        self.db.armor_type = "light_armor"
        self.db.protection = 2
        self.db.hindrance = 1
        self.db.absorption = 0.1
        self.db.maneuver_hindrance = 5
        self.db.stealth_hindrance = 5
        self.db.coverage = ["torso"]
        self.db.covers = []
        self.db.skill_scaling = {}
        self.db.unlocks = {
            20: {"protection_bonus": 1},
            40: {"hindrance_reduction": 1},
        }
        self.db.condition = 100
        self.apply_armor_preset()

    def apply_armor_preset(self):
        preset = ARMOR_PRESETS.get(self.db.armor_type, {})
        self.db.protection = preset.get("protection", self.db.protection or 2)
        self.db.hindrance = preset.get("hindrance", self.db.hindrance or 1)
        self.db.weight = preset.get("weight", self.db.weight or 5.0)
        self.db.maneuver_hindrance = self.db.hindrance
        self.db.stealth_hindrance = self.db.hindrance

    def get_armor_profile(self):
        return {
            "type": self.db.armor_type,
            "protection": self.db.protection,
            "hindrance": self.db.hindrance,
            "coverage": list(self.db.coverage or self.db.covers or []),
        }