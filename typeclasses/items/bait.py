from typeclasses.objects import Object


class Bait(Object):
    """Base bait item for the fishing system."""

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_bait = True
        self.db.bait_type = "worm_cutbait"
        self.db.bait_family = "worm_cutbait"
        self.db.quality = 14
        self.db.bait_quality = 14
        self.db.bait_match_tags = ["worm", "cutbait", "freshwater"]
        self.db.weight = 0.1
        self.db.desc = "A simple bundle of universal fishing bait."