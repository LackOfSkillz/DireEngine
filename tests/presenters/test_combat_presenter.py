import unittest
from types import SimpleNamespace

from engine.presenters.combat_presenter import CombatPresenter
from engine.services.result import ActionResult


class DummyActor:
    def __init__(self, key="Jekar", room=None):
        self.key = key
        self.location = room
        self.messages = []

    def msg(self, text):
        self.messages.append(text)


class DummyRoom:
    def __init__(self):
        self.messages = []

    def msg_contents(self, message, exclude=None):
        self.messages.append({"message": message, "exclude": exclude})


class CombatPresenterTests(unittest.TestCase):
    def test_render_attack_parry_miss_uses_distinct_messaging(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "miss",
                "verb": "thrust",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "details": {"combat_outcome": "parried_full"},
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertIn("rings off their guard", payload["attacker"][0])
        self.assertIn("catch Jekar's thrust", payload["target"][0])
        self.assertIn("turns aside Jekar's attack", payload["room"][0])

    def test_render_attack_evaded_miss_uses_distinct_messaging(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "miss",
                "verb": "slice",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "details": {"combat_outcome": "evaded"},
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertIn("cuts through empty air", payload["attacker"][0])
        self.assertIn("twist aside", payload["target"][0])
        self.assertIn("evading Jekar's attack", payload["room"][0])

    def test_render_attack_generic_miss_still_uses_generic_text(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "miss",
                "verb": "slice",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertIn("but miss", payload["attacker"][0])
        self.assertIn("but misses", payload["target"][0])

    def test_render_attack_adds_armor_messages_for_all_audiences(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "hit",
                "verb": "thrust",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "location_name": "arm",
                "quality": "good",
                "armor_absorbed": True,
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertTrue(any("armor turns part of the blow" in line for line in payload["attacker"]))
        self.assertTrue(any("armor absorbs part of the blow" in line for line in payload["target"]))
        self.assertTrue(any("armor blunts part of the impact" in line for line in payload["room"]))

    def test_render_attack_adds_force_of_impact_lines_for_solid_hits(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "hit",
                "verb": "thrust",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "location_name": "arm",
                "quality": "solid",
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertTrue(any("satisfying force" in line for line in payload["attacker"]))
        self.assertTrue(any("solid force" in line for line in payload["target"]))
        self.assertTrue(any("solid force" in line for line in payload["room"]))

    def test_render_attack_adds_barrier_weakened_messages(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "hit",
                "verb": "thrust",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "location_name": "arm",
                "quality": "good",
                "barrier_event": {"type": "weakened", "absorbed": 6},
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertTrue(any("visibly weakens" in line for line in payload["attacker"]))
        self.assertTrue(any("absorbs 6 points" in line for line in payload["target"]))
        self.assertTrue(any("dims visibly" in line for line in payload["room"]))

    def test_render_attack_adds_barrier_depleted_messages(self):
        payload = CombatPresenter.render_attack(
            ActionResult.ok(data={
                "outcome": "hit",
                "verb": "thrust",
                "weapon_name": "training sword",
                "target_name": "goblin",
                "attacker_name": "Jekar",
                "location_name": "arm",
                "quality": "good",
                "barrier_event": {"type": "depleted", "absorbed": 9},
            }),
            DummyActor(),
            DummyActor("goblin"),
        )

        self.assertTrue(any("shattering apart" in line for line in payload["attacker"]))
        self.assertTrue(any("leaving you exposed" in line for line in payload["target"]))
        self.assertTrue(any("brilliant flash" in line for line in payload["room"]))

    def test_present_attack_uses_helper_for_primary_triplet(self):
        room = DummyRoom()
        attacker = DummyActor(room=room)
        target = DummyActor("goblin", room=room)
        result = ActionResult.ok(data={
            "outcome": "miss",
            "verb": "slice",
            "weapon_name": "training sword",
            "target_name": "goblin",
            "attacker_name": "Jekar",
        })

        CombatPresenter.present_attack(result, attacker, target)

        self.assertEqual(attacker.messages[0], "You slice at goblin with your training sword but miss.")
        self.assertEqual(target.messages[0], "Jekar slices at you with training sword but misses.")
        self.assertEqual(room.messages[0]["message"], "Jekar slices at goblin with training sword but misses.")


if __name__ == "__main__":
    unittest.main()