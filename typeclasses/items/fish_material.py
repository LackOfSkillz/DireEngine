from typeclasses.objects import Object
from world.systems import fishing_economy


class FishMaterial(Object):
    """Processed fish goods produced by cleaning a caught fish."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.item_type = "fish_meat"
        self.db.quantity = 1
        self.db.value = 2
        self.db.item_value = 2
        self.db.processed_from = "fresh catch"
        self.db.desc = "Prepared fish goods ready for sale."

    def return_appearance(self, looker, **kwargs):
        return fishing_economy.format_processed_fish_inspection(self)