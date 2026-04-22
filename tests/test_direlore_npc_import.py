import unittest
from unittest.mock import patch

from server.systems import direlore_npc_import


class DireloreNpcImportTests(unittest.TestCase):
    def test_build_npc_payload_maps_spawn_ready_fields(self):
        payload = direlore_npc_import.interpret_npc(
            {"id": 171, "name": "Cavern bear", "level": 10, "npc_type": "creature"},
            messaging=[
                {"message_type": "ambient", "message_text": "Spawn: A cavern bear lumbers in."},
                {"message_type": "ambient", "message_text": "Entrance: A cavern bear saunters in."},
                {"message_type": "attack", "message_text": "The cavern bear mauls wildly."},
            ],
        )

        self.assertEqual(payload["id"], "cavern_bear")
        self.assertEqual(payload["type"], "hostile")
        self.assertEqual(payload["stats"], {"level": 10, "health": 100, "attack": 6, "defense": 5})
        self.assertTrue(payload["behavior"]["aggressive"])
        self.assertEqual(payload["description"]["short"], "a cavern bear")
        self.assertEqual(payload["description"]["long"], "Cavern bear is here.")
        self.assertEqual(payload["meta"]["source"], "direlore")
        self.assertEqual(
            payload["dialogue"]["idle"],
            ["A cavern bear lumbers in.", "A cavern bear saunters in."],
        )

    def test_classify_npc_type_is_conservative_for_non_creatures(self):
        self.assertEqual(direlore_npc_import.classify_npc_type({"npc_type": "passive"}), "neutral")
        self.assertEqual(direlore_npc_import.classify_npc_type({"npc_type": "humanoid"}), "neutral")

    def test_normalize_loot_candidate_id_strips_count_suffix(self):
        self.assertEqual(direlore_npc_import.normalize_loot_candidate_id("Dagger (2)"), "dagger")

    def test_import_summary_reports_missing_fields(self):
        rows = [
            {"id": 1, "name": "Cavern bear", "level": 10, "npc_type": "creature", "located": "Mine"},
            {"id": 2, "name": "Oddity", "level": 3, "npc_type": "unknown_type", "located": ""},
        ]

        with patch("server.systems.direlore_npc_import.fetch_canon_npcs", return_value=rows), patch(
            "server.systems.direlore_npc_import.fetch_npc_messages", return_value={}
        ), patch(
            "server.systems.direlore_npc_import.fetch_npc_loot_candidates", return_value={1: ["dagger"], 2: []}
        ):
            summary = direlore_npc_import.import_direlore_npcs(limit=2, dry_run=True)

        self.assertEqual(summary["imported"], 2)
        self.assertEqual(summary["missing"]["descriptions"], 1)
        self.assertEqual(summary["missing"]["aggression_flags"], 1)
        self.assertEqual(summary["missing"]["loot"], 1)
        self.assertEqual(summary["missing_percent"]["loot"], 50.0)


if __name__ == "__main__":
    unittest.main()