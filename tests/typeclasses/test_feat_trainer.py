import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from typeclasses.feat_trainer import FeatTrainerNPC
from world.areas.the_landing.feat_trainers import ensure_the_landing_feat_trainers


class FeatTrainerTypeclassTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key):
        obj = create_object(typeclass, key=key, nohome=True)
        self.created.append(obj)
        return obj

    def test_feat_trainer_initializes_required_attributes(self):
        trainer = self._create(FeatTrainerNPC, "Feat Trainer Test")

        self.assertTrue(trainer.db.is_trainer)
        self.assertEqual(trainer.db.trainer_kind, "feat")
        self.assertTrue(str(trainer.db.greeting or "").strip())

    def test_handle_inquiry_returns_generic_help(self):
        trainer = self._create(FeatTrainerNPC, "Feat Trainer Help")

        response = trainer.handle_inquiry(SimpleNamespace(), "feat")

        self.assertIn("Magical feats", response)

    def test_handle_inquiry_returns_feat_description(self):
        trainer = self._create(FeatTrainerNPC, "Feat Trainer Query")

        response = trainer.handle_inquiry(SimpleNamespace(), "deep attunement")

        self.assertIn("Deep Attunement", response)
        self.assertIn("Slot cost", response)

    def test_landing_feat_trainer_bootstrap_creates_room_and_trainer(self):
        room = ensure_the_landing_feat_trainers()

        self.assertIsNotNone(room)
        self.assertEqual(room.db.region_name, "The Landing")
        trainers = [obj for obj in room.contents if isinstance(obj, FeatTrainerNPC)]
        self.assertEqual(len(trainers), 1)


if __name__ == "__main__":
    unittest.main()