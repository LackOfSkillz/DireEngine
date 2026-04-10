from evennia.objects.objects import DefaultObject


class FishingPole(DefaultObject):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_fishing_pole = True
        self.db.pole_rating = 10
        self.db.line_attached = True
        self.db.hook_attached = True
        self.db.line_tangled = False
        self.db.line_rating = 10
        self.db.hook_rating = 10
        self.db.weight = 2.0
        self.db.item_type = "fishing_gear"
        self.db.desc = "A plain starter fishing pole with a serviceable line and hook already rigged."
        self.aliases.add("pole")
        self.aliases.add("rod")