from typeclasses.npcs import NPC


class Vendor(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_vendor = True
        self.db.vendor_type = "general"
        self.db.accepted_item_types = []
        self.db.trade_difficulty = 20
        self.db.inventory = []
        self.db.shop_heat = 0
        self.db.shop_heat_updated_at = 0
        self.db.theft_attempt_log = {}
        self.db.desc = "A trader with an eye for useful goods and a sharper eye for prices."