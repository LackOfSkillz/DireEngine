import unittest
from types import SimpleNamespace

from commands.cmd_feats import CmdFeats
from commands.cmd_forget_feat import CmdForgetFeat
from commands.cmd_learn_feat import CmdLearnFeat


class DummyRoom:
    def __init__(self, *contents):
        self.contents = list(contents)
        self.messages = []

    def msg_contents(self, message, exclude=None):
        _exclude = exclude
        self.messages.append(str(message))


class DummyTrainer:
    def __init__(self):
        self.key = "Instructor Sariel"
        self.db = SimpleNamespace(trainer_kind="feat")

    def resolve_feat(self, query):
        from engine.services.feat_training_service import FeatTrainerService

        return FeatTrainerService.resolve_feat_query(query)

    def describe_learning_path(self, actor, feat):
        _actor = actor
        return f"You are not ready for {feat.name}."

    def describe_forgetting_path(self, actor, feat):
        _actor = actor
        return f"You cannot forget {feat.name}."


class DummyCaller:
    def __init__(self, profession="cleric", feats=None, skills=None, coins=5000):
        self.db = SimpleNamespace(
            profession=profession,
            circle=10,
            feats=feats,
            magic_slot_pool=None,
            coins=coins,
        )
        self.location = DummyRoom()
        self.messages = []
        self.skills = dict(skills or {"attunement": 100, "arcana": 100, "primary_magic": 100})
        self.key = "Caller"

    def ensure_core_defaults(self):
        return None

    def get_profession(self):
        return self.db.profession

    def get_circle(self):
        return self.db.circle

    def get_skill_rank(self, skill_name):
        return self.skills.get(skill_name, 0)

    def msg(self, text):
        self.messages.append(str(text))


class FeatCommandTests(unittest.TestCase):
    def test_feats_command_lists_available_feat(self):
        caller = DummyCaller(feats={"learned": [], "granted": []})
        command = SimpleNamespace(caller=caller)

        CmdFeats.func(command)

        output = caller.messages[-1]
        self.assertIn("Magical Feats", output)
        self.assertIn("Deep Attunement", output)

    def test_learn_feat_requires_trainer(self):
        caller = DummyCaller(feats={"learned": [], "granted": []})
        command = SimpleNamespace(caller=caller, args="feat deep attunement")

        CmdLearnFeat.func(command)

        self.assertEqual(caller.messages[-1], "There is no feat trainer here.")

    def test_learn_feat_succeeds_and_emits_room_message(self):
        caller = DummyCaller(feats={"learned": [], "granted": []})
        trainer = DummyTrainer()
        caller.location = DummyRoom(caller, trainer)
        command = SimpleNamespace(caller=caller, args="feat deep attunement")

        CmdLearnFeat.func(command)

        self.assertIn("Deep Attunement", caller.messages[-1])
        self.assertIn("magical instruction", caller.location.messages[-1])

    def test_forget_feat_succeeds(self):
        caller = DummyCaller(feats={"learned": ["deep_attunement"], "granted": []})
        caller.db.magic_slot_pool = {"max": 10, "allocations": {"spells": {}, "feats": {"deep_attunement": 1}}}
        trainer = DummyTrainer()
        caller.location = DummyRoom(caller, trainer)
        command = SimpleNamespace(caller=caller, args="feat deep attunement")

        CmdForgetFeat.func(command)

        self.assertIn("slot refunded", caller.messages[-1])
        self.assertEqual(caller.db.coins, 3750)


if __name__ == "__main__":
    unittest.main()