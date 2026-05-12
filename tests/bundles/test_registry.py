import unittest

from engine.bundles.exceptions import BundleConflictError, BundleNotLoadedError, BundleOwnershipError, ManifestValidationError
from engine.bundles.profession_registry import ProfessionRegistry


class RegistryContractTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProfessionRegistry("profession_registry")
        self.definition = {
            "id": "ranger",
            "display_name": "Ranger",
            "bundle_id": "T1-PROF-RANGER",
            "tier": 1,
        }

    def test_register_and_get(self):
        self.registry.register("ranger", self.definition, source_bundle="bundle.ranger")
        payload = self.registry.get("ranger")
        self.assertEqual(payload["display_name"], "Ranger")
        self.assertEqual(payload["source_bundle"], "bundle.ranger")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.registry.get("moon_mage"))

    def test_require_missing_raises(self):
        with self.assertRaises(BundleNotLoadedError):
            self.registry.require("moon_mage")

    def test_conflict_raises(self):
        self.registry.register("ranger", self.definition, source_bundle="bundle.ranger")
        with self.assertRaises(BundleConflictError):
            self.registry.register("ranger", self.definition, source_bundle="bundle.other")

    def test_same_owner_can_reregister(self):
        self.registry.register("ranger", self.definition, source_bundle="bundle.ranger")
        updated = dict(self.definition)
        updated["display_name"] = "Ranger Prime"
        self.registry.register("ranger", updated, source_bundle="bundle.ranger")
        self.assertEqual(self.registry.get("ranger")["display_name"], "Ranger Prime")

    def test_list_methods(self):
        self.registry.register("ranger", self.definition, source_bundle="bundle.ranger")
        self.assertEqual(self.registry.list_keys(), ["ranger"])
        self.assertEqual(self.registry.list_by_bundle("bundle.ranger"), ["ranger"])
        self.assertTrue(self.registry.is_registered("ranger"))

    def test_unregister_requires_owner(self):
        self.registry.register("ranger", self.definition, source_bundle="bundle.ranger")
        with self.assertRaises(BundleOwnershipError):
            self.registry.unregister("ranger", source_bundle="bundle.other")
        self.registry.unregister("ranger", source_bundle="bundle.ranger")
        self.assertFalse(self.registry.is_registered("ranger"))

    def test_invalid_definition_raises(self):
        with self.assertRaises(ManifestValidationError):
            self.registry.register("ranger", {"id": "ranger"}, source_bundle="bundle.ranger")


if __name__ == "__main__":
    unittest.main()