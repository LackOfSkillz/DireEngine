from evennia.objects.objects import DefaultObject


class Luminar(DefaultObject):
    def at_object_creation(self):
        self.db.is_luminar = True
        self.db.capacity = 50
        self.db.charge = 0
        self.db.stability = 1.0
        self.db.desc = "A crystalline focus made to hold a measured Radiance charge."