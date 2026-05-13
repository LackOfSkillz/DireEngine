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
        self.db.punc_res = 210
        self.db.slic_res = 210
        self.db.impa_res = 210
        self.db.fire_res = 0
        self.db.cold_res = 0
        self.db.elec_res = 0
        self.db.damage = 0
        self.db.strength = 100
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
        flat = max(0, int(self.db.protection or 0))
        pct = max(0, int(round(float(self.db.absorption or 0.0) * 100)))
        encoded = (flat * 100) + pct
        # TODO(world-data-migration): re-seed armor from canon_items with explicit *_res fields.
        self.db.punc_res = getattr(self.db, "punc_res", encoded) or encoded
        self.db.slic_res = getattr(self.db, "slic_res", encoded) or encoded
        self.db.impa_res = getattr(self.db, "impa_res", encoded) or encoded

    def get_armor_profile(self):
        return {
            "type": self.db.armor_type,
            "protection": self.db.protection,
            "hindrance": self.db.hindrance,
            "coverage": list(self.db.coverage or self.db.covers or []),
            "punc_res": int(getattr(self.db, "punc_res", 0) or 0),
            "slic_res": int(getattr(self.db, "slic_res", 0) or 0),
            "impa_res": int(getattr(self.db, "impa_res", 0) or 0),
            "fire_res": int(getattr(self.db, "fire_res", 0) or 0),
            "cold_res": int(getattr(self.db, "cold_res", 0) or 0),
            "elec_res": int(getattr(self.db, "elec_res", 0) or 0),
            "damage": int(getattr(self.db, "damage", 0) or 0),
            "strength": int(getattr(self.db, "strength", 100) or 100),
        }