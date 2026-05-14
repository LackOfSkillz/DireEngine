import unittest
from types import SimpleNamespace

from engine.services.feat_service import FeatService


class DummyCharacter:
    def __init__(self, feats=None):
        self.db = SimpleNamespace(feats=feats)


class FeatServiceTests(unittest.TestCase):
    def test_identity_modifier_without_feats(self):
        character = DummyCharacter()

        self.assertEqual(FeatService.get_modifier(character, "attunement_regen_multiplier"), 1.0)
        self.assertEqual(FeatService.get_modifier(character, "prepared_expiry_bonus_seconds"), 0.0)
        self.assertFalse(FeatService.get_unlock(character, "raw_channeling"))

    def test_known_feats_include_learned_and_granted(self):
        character = DummyCharacter(feats={"learned": ["deep_attunement"], "granted": ["efficient_channeling"]})

        self.assertTrue(FeatService.has_feat(character, "deep_attunement"))
        self.assertTrue(FeatService.has_feat(character, "efficient_channeling"))
        self.assertEqual(FeatService.get_known_feats(character), ["deep_attunement", "efficient_channeling"])

    def test_modifier_resolves_active_feat_payload(self):
        character = DummyCharacter(feats={"learned": ["deep_attunement", "focused_preparation"], "granted": []})

        self.assertEqual(FeatService.get_modifier(character, "attunement_regen_multiplier"), 1.10)
        self.assertEqual(FeatService.get_modifier(character, "prepared_expiry_bonus_seconds"), 15.0)


if __name__ == "__main__":
    unittest.main()