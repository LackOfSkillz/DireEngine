import unittest
from types import SimpleNamespace

from engine.services.feat_service import FeatService
from engine.services.feat_training_service import FeatTrainerService


class DummyCharacter:
    def __init__(self, profession="cleric", circle=10, coins=5000, skills=None, feats=None):
        self.db = SimpleNamespace(
            profession=profession,
            circle=circle,
            coins=coins,
            feats=feats,
            magic_slot_pool=None,
        )
        self.skills = dict(skills or {"attunement": 100, "arcana": 100, "primary_magic": 100})

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle

    def get_skill_rank(self, skill_name):
        return self.skills.get(skill_name, 0)


class FeatTrainingServiceTests(unittest.TestCase):
    def test_can_learn_feat_success(self):
        character = DummyCharacter()

        result = FeatTrainerService.can_learn_feat(character, "deep_attunement")

        self.assertTrue(result.success)
        self.assertEqual(result.needed_slots, 1)

    def test_can_learn_feat_detects_missing_skills(self):
        character = DummyCharacter(skills={"attunement": 90, "arcana": 100, "primary_magic": 100})

        result = FeatTrainerService.can_learn_feat(character, "deep_attunement")

        self.assertFalse(result.success)
        self.assertEqual(result.reason, "insufficient_skills")
        self.assertIn("attunement", result.missing_skills)

    def test_teach_feat_allocates_slot_and_persists(self):
        character = DummyCharacter()

        result = FeatTrainerService.teach_feat(character, "deep_attunement")

        self.assertTrue(result.success)
        self.assertIn("deep_attunement", character.db.feats["learned"])
        self.assertTrue(FeatService.has_feat(character, "deep_attunement"))

    def test_forget_feat_refunds_slot_and_charges_coins(self):
        character = DummyCharacter(feats={"learned": ["deep_attunement"], "granted": []})
        character.db.magic_slot_pool = {"max": 10, "allocations": {"spells": {}, "feats": {"deep_attunement": 1}}}

        result = FeatTrainerService.forget_feat(character, "deep_attunement")

        self.assertTrue(result.success)
        self.assertEqual(result.slots_refunded, 1)
        self.assertEqual(character.db.coins, 3750)
        self.assertNotIn("deep_attunement", character.db.feats["learned"])

    def test_granted_feat_cannot_be_forgotten(self):
        character = DummyCharacter(feats={"learned": [], "granted": ["efficient_channeling"]})

        result = FeatTrainerService.can_forget_feat(character, "efficient_channeling")

        self.assertFalse(result.success)
        self.assertEqual(result.reason, "granted_feat_cannot_be_forgotten")

    def test_circle_grant_converts_learned_feat_to_granted(self):
        character = DummyCharacter(
            profession="cleric",
            circle=1,
            feats={"learned": ["efficient_channeling"], "granted": []},
        )
        character.db.magic_slot_pool = {"max": 10, "allocations": {"spells": {}, "feats": {"efficient_channeling": 1}}}

        granted = FeatTrainerService.grant_circle_profession_feats(character, 2)

        self.assertEqual([feat.id for feat in granted], ["efficient_channeling"])
        self.assertNotIn("efficient_channeling", character.db.feats["learned"])
        self.assertIn("efficient_channeling", character.db.feats["granted"])
        self.assertEqual(character.db.magic_slot_pool["allocations"]["feats"], {})

    def test_bard_circle_two_receives_raw_channeling_grant(self):
        character = DummyCharacter(
            profession="bard",
            circle=1,
            feats={"learned": [], "granted": []},
        )

        granted = FeatTrainerService.grant_circle_profession_feats(character, 2)

        self.assertEqual([feat.id for feat in granted], ["raw_channeling"])
        self.assertIn("raw_channeling", character.db.feats["granted"])

    def test_granted_raw_channeling_cannot_be_forgotten(self):
        character = DummyCharacter(feats={"learned": [], "granted": ["raw_channeling"]})

        result = FeatTrainerService.can_forget_feat(character, "raw_channeling")

        self.assertFalse(result.success)
        self.assertEqual(result.reason, "granted_feat_cannot_be_forgotten")


if __name__ == "__main__":
    unittest.main()