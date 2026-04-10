from typeclasses.objects import Object
from world.systems import fishing_economy


class Fish(Object):
    """Caught fish item stamped with fishing metadata."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.weight = 1
        self.db.value = 1
        self.db.item_type = "fish"
        self.db.fish_type = "fresh fish"
        self.db.is_trophy = False
        self.db.trophy_multiplier = 1.0
        self.db.fish_group = "river 1"
        self.db.fish_difficulty = 20
        self.db.fight_profile = "steady"
        self.db.desc = "A freshly caught fish with wet scales and a cold sheen."

    def return_appearance(self, looker, **kwargs):
        return fishing_economy.format_fish_inspection(self)