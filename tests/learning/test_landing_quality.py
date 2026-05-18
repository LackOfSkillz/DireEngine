import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from world.area_forge.paths import area_namespace
from world.areas.the_landing.streetlife import STREETLIFE_NPCS, ensure_the_landing_streetlife
from world.the_landing import apply_curated_landing_overrides


class LandingQualityTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create_room(self, key, node_id):
        room = create_object("typeclasses.rooms.Room", key=key, nohome=True)
        namespace = area_namespace("new_landing")
        room.tags.add(node_id, category=namespace["node_category"])
        self.created.append(room)
        return room

    def test_curated_overrides_replace_bad_ocr_labels_and_apply_handwritten_landmarks(self):
        nodes = [
            {
                "id": "new_landing_666_432",
                "generated_name": "Central Crossing [666,432]",
                "final_label": "Central Crossing [666,432]",
            },
            {
                "id": "new_landing_66_734",
                "generated_name": "Guilder's Lane 2, Midway",
                "final_label": "3) Way",
            },
        ]

        updated = apply_curated_landing_overrides(nodes)

        self.assertEqual(updated[0]["final_label"], "Bellfound Steps")
        self.assertIn("Broad civic steps", updated[0]["desc_final"])
        self.assertEqual(updated[1]["final_label"], "Guilder's Lane 2, Midway")

    def test_streetlife_builder_creates_named_npcs_for_tagged_landing_nodes(self):
        for index, spec in enumerate(STREETLIFE_NPCS.values(), start=1):
            self._create_room(f"Landing Room {index}", spec["node_id"])

        placed = ensure_the_landing_streetlife()
        placed_again = ensure_the_landing_streetlife()

        self.assertEqual(set(placed), set(STREETLIFE_NPCS))
        self.assertEqual(set(placed_again), set(STREETLIFE_NPCS))
        self.assertEqual(
            {name: npc.id for name, npc in placed.items()},
            {name: npc.id for name, npc in placed_again.items()},
        )
        for name, npc in placed.items():
            self.created.append(npc)
            self.assertTrue(npc.db.is_npc)
            self.assertTrue(str(npc.db.default_inquiry_response or "").strip())
            self.assertTrue(bool(getattr(npc.db, "landing_streetlife", False)))


if __name__ == "__main__":
    unittest.main()