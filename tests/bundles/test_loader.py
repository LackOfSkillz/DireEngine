import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from engine.bundles.boot import RegistryHub
from engine.bundles.content_registry import ContentRegistry
from engine.bundles.loader import BundleLoader
from engine.bundles.profession_registry import ProfessionRegistry
from engine.bundles.race_registry import RaceRegistry
from engine.bundles.skill_registry import SkillRegistry
from engine.bundles.spell_circle_registry import SpellCircleRegistry
from engine.bundles.stat_registry import StatRegistry
from engine.bundles.trade_registry import TradeRegistry
from engine.bundles.zone_registry import ZoneRegistry


def _build_hub():
    return RegistryHub(
        profession_registry=ProfessionRegistry("profession_registry"),
        race_registry=RaceRegistry("race_registry"),
        zone_registry=ZoneRegistry("zone_registry"),
        trade_registry=TradeRegistry("trade_registry"),
        content_registry=ContentRegistry("content_registry"),
        skill_registry=SkillRegistry("skill_registry"),
        stat_registry=StatRegistry("stat_registry"),
        spell_circle_registry=SpellCircleRegistry("spell_circle_registry"),
    )


class LoaderTests(unittest.TestCase):
    def _write_bundle(self, root: Path, package_root: Path, folder: str, manifest_text: str, module_text: str):
        bundle_dir = root / folder
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "bundle.toml").write_text(textwrap.dedent(manifest_text), encoding="utf-8")
        package_root.mkdir(parents=True, exist_ok=True)
        (package_root / "__init__.py").write_text("", encoding="utf-8")
        (package_root / f"{folder}.py").write_text(textwrap.dedent(module_text), encoding="utf-8")

    def test_discovery_order_and_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundles"
            package_root = Path(temp_dir) / "fakebundles"
            self._write_bundle(
                root,
                package_root,
                "alpha",
                """
                [bundle]
                id = "alpha"
                display_name = "Alpha"
                version = "1.0.0"
                tier = 0

                [provides]
                professions = ["alpha_prof"]

                [entrypoint]
                register_callable = "fakebundles.alpha.register"
                """,
                """
                def register(context):
                    context.registries.profession_registry.register(
                        'alpha_prof',
                        {'id': 'alpha_prof', 'display_name': 'Alpha Prof', 'bundle_id': 'alpha', 'tier': 0},
                        source_bundle=context.manifest.bundle_id,
                    )
                """,
            )
            self._write_bundle(
                root,
                package_root,
                "beta",
                """
                [bundle]
                id = "beta"
                display_name = "Beta"
                version = "1.0.0"
                tier = 1

                [requires]
                free_bundles = ["alpha"]

                [provides]
                races = ["beta_race"]

                [entrypoint]
                register_callable = "fakebundles.beta.register"
                """,
                """
                def register(context):
                    context.registries.race_registry.register(
                        'beta_race',
                        {'id': 'beta_race', 'display_name': 'Beta Race', 'bundle_id': 'beta', 'tier': 1},
                        source_bundle=context.manifest.bundle_id,
                    )
                """,
            )
            sys.path.insert(0, temp_dir)
            try:
                loader = BundleLoader(registries=_build_hub(), search_paths=[str(root)])
                manifests = loader.discover()
                self.assertEqual([manifest.bundle_id for manifest in manifests], ["alpha", "beta"])
                report = loader.load_all(manifests)
                self.assertEqual(report.loaded, ["alpha", "beta"])
                self.assertIsNotNone(loader.registries.profession_registry.get("alpha_prof"))
                self.assertIsNotNone(loader.registries.race_registry.get("beta_race"))
            finally:
                sys.path.remove(temp_dir)

    def test_cycle_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundles"
            package_root = Path(temp_dir) / "cyclebundles"
            self._write_bundle(
                root,
                package_root,
                "alpha",
                """
                [bundle]
                id = "alpha"
                display_name = "Alpha"
                version = "1.0.0"
                tier = 0

                [requires]
                free_bundles = ["beta"]

                [entrypoint]
                register_callable = "cyclebundles.alpha.register"
                """,
                "def register(context):\n    return None\n",
            )
            self._write_bundle(
                root,
                package_root,
                "beta",
                """
                [bundle]
                id = "beta"
                display_name = "Beta"
                version = "1.0.0"
                tier = 0

                [requires]
                free_bundles = ["alpha"]

                [entrypoint]
                register_callable = "cyclebundles.beta.register"
                """,
                "def register(context):\n    return None\n",
            )
            sys.path.insert(0, temp_dir)
            try:
                loader = BundleLoader(registries=_build_hub(), search_paths=[str(root)])
                validation = loader.validate_dependencies(loader.discover())
                self.assertFalse(validation.is_valid)
                self.assertTrue(any("cycle" in message.lower() for message in validation.errors))
            finally:
                sys.path.remove(temp_dir)

    def test_missing_required_dependency_skips_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundles"
            package_root = Path(temp_dir) / "skipbundles"
            self._write_bundle(
                root,
                package_root,
                "beta",
                """
                [bundle]
                id = "beta"
                display_name = "Beta"
                version = "1.0.0"
                tier = 0

                [requires]
                free_bundles = ["missing"]

                [entrypoint]
                register_callable = "skipbundles.beta.register"
                """,
                "def register(context):\n    raise AssertionError('should not load')\n",
            )
            sys.path.insert(0, temp_dir)
            try:
                loader = BundleLoader(registries=_build_hub(), search_paths=[str(root)])
                report = loader.load_all(loader.discover())
                self.assertEqual(report.loaded, [])
                self.assertIn("beta", report.skipped)
            finally:
                sys.path.remove(temp_dir)

    def test_missing_optional_dependency_does_not_block_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "bundles"
            package_root = Path(temp_dir) / "optionbundles"
            self._write_bundle(
                root,
                package_root,
                "gamma",
                """
                [bundle]
                id = "gamma"
                display_name = "Gamma"
                version = "1.0.0"
                tier = 0

                [requires]
                optional_bundles = ["missing"]

                [provides]
                trade_systems = ["gamma_trade"]

                [entrypoint]
                register_callable = "optionbundles.gamma.register"
                """,
                """
                def register(context):
                    context.registries.trade_registry.register(
                        'gamma_trade',
                        {'id': 'gamma_trade', 'display_name': 'Gamma Trade', 'bundle_id': 'gamma', 'tier': 0},
                        source_bundle=context.manifest.bundle_id,
                    )
                """,
            )
            sys.path.insert(0, temp_dir)
            try:
                loader = BundleLoader(registries=_build_hub(), search_paths=[str(root)])
                report = loader.load_all(loader.discover())
                self.assertEqual(report.loaded, ["gamma"])
                self.assertIsNotNone(loader.registries.trade_registry.get("gamma_trade"))
            finally:
                sys.path.remove(temp_dir)

    def test_zero_bundles_is_graceful(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = BundleLoader(registries=_build_hub(), search_paths=[temp_dir])
            report = loader.load_all(loader.discover())
            self.assertEqual(report.loaded, [])
            self.assertIsNone(loader.registries.profession_registry.get("moon_mage"))


if __name__ == "__main__":
    unittest.main()