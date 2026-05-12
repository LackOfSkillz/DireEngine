import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.bundles.exceptions import ManifestValidationError
from engine.bundles.manifest import parse_bundle_manifest


class ManifestParserTests(unittest.TestCase):
    def test_parse_valid_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "bundle.toml"
            manifest_path.write_text(
                textwrap.dedent(
                    """
                    [bundle]
                    id = "T1-PROF-RANGER"
                    display_name = "Ranger"
                    version = "1.0.0"
                    tier = 1

                    [requires]
                    engine = ">=1.0.0"
                    free_bundles = ["T0-SPELL-CIRCLES"]
                    optional_bundles = ["T1-ZONE-CROSSING"]

                    [provides]
                    professions = ["ranger"]

                    [entrypoint]
                    register_callable = "fakebundles.ranger.register"
                    """
                ),
                encoding="utf-8",
            )
            manifest = parse_bundle_manifest(manifest_path)
        self.assertEqual(manifest.bundle_id, "T1-PROF-RANGER")
        self.assertEqual(manifest.required_bundles, ("T0-SPELL-CIRCLES",))
        self.assertEqual(manifest.optional_bundles, ("T1-ZONE-CROSSING",))
        self.assertEqual(manifest.provides["professions"], ("ranger",))

    def test_invalid_manifest_raises(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "bundle.toml"
            manifest_path.write_text("[bundle]\nid='missing-entrypoint'\n", encoding="utf-8")
            with self.assertRaises(ManifestValidationError):
                parse_bundle_manifest(manifest_path)


if __name__ == "__main__":
    unittest.main()