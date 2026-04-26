import os
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from world.area_forge.cli import forge_area
from world.area_forge import run as area_forge_run


class AreaForgeCliTests(unittest.TestCase):
    @patch("world.area_forge.cli.forge_area.run_area_forge")
    def test_cli_passes_spawn_flags(self, mock_run_area_forge):
        exit_code = forge_area.main(
            [
                "--map",
                "maps/CrossingMap (1).png",
                "--area-id",
                "builder2",
                "--mode",
                "build",
                "--spawn",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_run_area_forge.assert_called_once_with(
            "maps/CrossingMap (1).png",
            "builder2",
            mode="build",
            manifest_path=None,
            use_ocr=True,
            profile="yaml_graph",
            spawn=True,
            dry_run_spawn=False,
        )


class AreaForgeRunTests(unittest.TestCase):
    def test_run_area_forge_rejects_spawn_for_extract_mode(self):
        with self.assertRaisesRegex(ValueError, "build or full mode"):
            area_forge_run.run_area_forge(
                "maps/CrossingMap (1).png",
                "builder2",
                mode="extract",
                manifest_path="manifest.json",
                spawn=True,
            )

    @patch("world.area_forge.run.save_snapshot")
    @patch("world.area_forge.run._spawn_zone")
    @patch("world.area_forge.run._build_evennia_area")
    @patch("world.area_forge.run.generate_normalization_report")
    @patch("world.area_forge.run.diff_area_specs")
    @patch("world.area_forge.run.load_snapshot")
    @patch("world.area_forge.run.save_review_report")
    @patch("world.area_forge.run.generate_review_flags")
    @patch("world.area_forge.run.load_review_graph")
    @patch("world.area_forge.run.load_area_spec")
    @patch("world.area_forge.run.artifact_paths")
    @patch("world.area_forge.run.load_manifest")
    def test_run_area_forge_build_mode_supports_dry_run_spawn(
        self,
        mock_load_manifest,
        mock_artifact_paths,
        mock_load_area_spec,
        mock_load_review_graph,
        mock_generate_review_flags,
        mock_save_review_report,
        mock_load_snapshot,
        mock_diff_area_specs,
        mock_generate_normalization_report,
        mock_build_evennia_area,
        mock_spawn_zone,
        mock_save_snapshot,
    ):
        del mock_save_review_report, mock_save_snapshot

        mock_load_manifest.return_value = {
            "map_file": "maps/CrossingMap (1).png",
            "area_id": "builder2",
            "profile": "yaml_graph",
            "style": {},
        }
        mock_artifact_paths.return_value = {
            "manifest": "artifacts/builder2/manifest.json",
            "areaspec": "artifacts/builder2/areaspec.json",
            "review": "artifacts/builder2/review.json",
            "review_graph": "artifacts/builder2/review_graph.json",
            "normalization_report": "artifacts/builder2/normalization_report.json",
            "marker_recovery_report": "artifacts/builder2/marker_recovery_report.json",
        }
        mock_load_area_spec.return_value = {"nodes": [{"id": "room_0001"}], "edges": []}
        mock_load_review_graph.return_value = {"nodes": [], "edges": []}
        mock_generate_review_flags.return_value = []
        mock_load_snapshot.return_value = None
        mock_diff_area_specs.return_value = []
        mock_generate_normalization_report.return_value = {"normalized_nodes": [], "isolated_room_count": 0, "overlap_count": 0}
        mock_build_evennia_area.return_value = {"zone_yaml": "worlddata/zones/builder2.yaml"}
        mock_spawn_zone.return_value = {
            "zone_id": "builder2",
            "dry_run": True,
            "rooms": 1,
            "exits": 0,
            "npcs": 0,
            "items": 0,
            "warnings": [],
        }

        result = area_forge_run.run_area_forge(
            "maps/CrossingMap (1).png",
            "builder2",
            mode="build",
            manifest_path="artifacts/builder2/manifest.json",
            profile="yaml_graph",
            dry_run_spawn=True,
        )

        mock_spawn_zone.assert_called_once_with("builder2", dry_run=True)
        self.assertTrue(result["spawn_result"]["dry_run"])


if __name__ == "__main__":
    unittest.main()