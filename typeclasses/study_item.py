from evennia.objects.objects import DefaultObject


class StudyItem(DefaultObject):
    def at_object_creation(self):
        self.db.is_study_item = True
        self.db.skill = "scholarship"
        self.db.difficulty = 10
        self.db.study_uses = 0