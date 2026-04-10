from typeclasses.objects import Object
from world.systems import fishing_economy


class Junk(Object):
    """Waterlogged salvage pulled from a fishing table."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.item_type = "junk"
        self.db.is_junk = True
        self.db.junk_tier = "common"
        self.db.junk_group = "River 1"
        self.db.value = 1
        self.db.item_value = 1
        self.db.desc = "A sodden bit of salvage dragged out of the water."

    def return_appearance(self, looker, **kwargs):
        return fishing_economy.format_junk_inspection(self)