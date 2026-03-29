from typeclasses.objects import Object


GRADE_VALUES = {
    "rough": 0.6,
    "standard": 1.0,
    "fine": 1.3,
    "master": 1.6,
}


class Lockpick(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_lockpick = True
        if not self.db.grade:
            self.db.grade = "standard"
        self.db.quality = self.get_quality()
        self.db.durability = 10

    def get_quality(self):
        return GRADE_VALUES.get(self.db.grade, 1.0)

    def get_display_name(self, looker=None, **kwargs):
        return f"{self.db.grade} lockpick"