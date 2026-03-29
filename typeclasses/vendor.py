from typeclasses.npcs import NPC


class Vendor(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_vendor = True
        self.db.trade_difficulty = 20
        self.db.inventory = []
        self.db.desc = "A trader with an eye for useful goods and a sharper eye for prices."