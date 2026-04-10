from typeclasses.objects import Object


class WeighStation(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_weigh_station = True
        self.db.stealable = False
        self.db.desc = "A brass-faced weigh station with a marked tray and a little price slate beside it."
        self.aliases.add("station")
        self.aliases.add("scale")
