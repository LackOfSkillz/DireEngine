import unittest

from engine.presenters.spell_effect_presenter import SpellEffectPresenter
from engine.services.result import ActionResult


class SpellEffectPresenterTests(unittest.TestCase):
    def test_render_self_heal_success(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "healing", "heal_amount": 5, "self_target": True, "target_key": "Empath", "source_mana_type": "life"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["A gentle surge of life closes some of your wounds."])

    def test_render_self_heal_noop(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "healing", "heal_amount": 0, "self_target": True, "target_key": "Empath", "source_mana_type": "life"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["Your spell settles over you, but there is nothing for it to mend."])

    def test_render_self_holy_heal_success(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "healing", "heal_amount": 5, "self_target": True, "target_key": "Cleric", "source_mana_type": "holy"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["A warm pulse of holy radiance closes some of your wounds."])

    def test_render_room_heal_targeted(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "healing", "heal_amount": 4, "self_target": False, "target_key": "Patient", "source_mana_type": "life"}})

        line = SpellEffectPresenter.render_room(result, "Empath")

        self.assertEqual(line, "Empath lays a gentle wash of life over Patient.")

    def test_render_room_holy_heal_targeted(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "healing", "heal_amount": 4, "self_target": False, "target_key": "Patient", "source_mana_type": "holy"}})

        line = SpellEffectPresenter.render_room(result, "Cleric")

        self.assertEqual(line, "Cleric lays a warm pulse of holy radiance over Patient.")

    def test_render_self_augmentation(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "augmentation", "buff_name": "bolster", "strength": 4, "self_target": True, "target_key": "Mage"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["You feel bolster settle into place around you at strength 4."])

    def test_render_room_augmentation(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "augmentation", "buff_name": "bolster", "strength": 4, "self_target": True, "target_key": "Mage"}})

        line = SpellEffectPresenter.render_room(result, "Mage")

        self.assertEqual(line, "Mage gathers bolster inward.")

    def test_render_self_warding(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "warding", "barrier_strength": 5, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["A faint barrier surrounds you with strength 5."])

    def test_render_room_warding(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "warding", "barrier_strength": 5, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        line = SpellEffectPresenter.render_room(result, "Cleric")

        self.assertEqual(line, "Cleric draws a barrier tight around themselves.")

    def test_render_group_warding(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "warding", "group_target": True, "target_count": 2}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You extend a protective field over 2 allies."])
        self.assertEqual(SpellEffectPresenter.render_target(result), ["A protective field settles over you."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Cleric"), "Cleric extends a protective field over the group.")

    def test_render_utility_light(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "utility", "utility_effect": "light", "self_target": True}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["A soft light forms around you."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Mage"), "A soft light gathers around Mage.")

    def test_render_utility_cleanse(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "utility", "utility_effect": "cleanse", "removed": True, "self_target": True}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You feel lingering effects wash away."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Cleric"), "A cleansing wash passes over Cleric.")

    def test_render_targeted_magic_miss(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "targeted_magic", "hit": False, "target_key": "Target", "final_damage": 0.0, "absorbed_by_ward": 0.0}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["Your spell misses Target."])

    def test_render_targeted_magic_full_absorb(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "targeted_magic", "hit": True, "hit_quality": "hit", "target_key": "Target", "final_damage": 0.0, "absorbed_by_ward": 8.0}})

        lines = SpellEffectPresenter.render_self(result)
        target_lines = SpellEffectPresenter.render_target(result)

        self.assertEqual(lines, ["Your spell strikes Target, but the barrier absorbs it completely."])
        self.assertEqual(target_lines, ["Your barrier catches the spell completely."])

    def test_render_targeted_magic_partial_absorb_room(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "targeted_magic", "hit": True, "hit_quality": "strong", "target_key": "Target", "final_damage": 6.0, "absorbed_by_ward": 3.0}})

        line = SpellEffectPresenter.render_room(result, "Mage")

        self.assertEqual(line, "Mage's spell strikes Target, but a barrier catches part of it.")

    def test_render_debilitation_hit(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "debilitation", "effect_type": "daze", "hit": True, "ignored": False, "target_key": "Target"}})

        lines = SpellEffectPresenter.render_self(result)
        target_lines = SpellEffectPresenter.render_target(result)
        room_line = SpellEffectPresenter.render_room(result, "Mage")

        self.assertEqual(lines, ["Your spell leaves Target reeling in a haze."])
        self.assertEqual(target_lines, ["You feel your thoughts blur."])
        self.assertEqual(room_line, "Mage's spell leaves Target looking dazed.")

    def test_render_debilitation_fail_to_take_hold(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "debilitation", "effect_type": "daze", "hit": False, "ignored": False, "target_key": "Target"}})

        lines = SpellEffectPresenter.render_self(result)

        self.assertEqual(lines, ["The spell fails to take hold."])

    def test_render_debilitation_expiration(self):
        lines = SpellEffectPresenter.render_expiration({"effect_family": "debilitation", "effect_type": "daze"})

        self.assertEqual(lines, ["You shake off the daze."])

    def test_render_cyclic_start(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "cyclic", "target_key": "Empath", "cyclic_state": {"started": True}}})

        lines = SpellEffectPresenter.render_self(result)
        room_line = SpellEffectPresenter.render_room(result, "Empath")

        self.assertEqual(lines, ["You begin sustaining the spell."])
        self.assertEqual(room_line, "Empath begins sustaining a spell.")

    def test_render_cyclic_collapse(self):
        lines = SpellEffectPresenter.render_expiration({"effect_family": "cyclic", "collapse_reason": "insufficient_mana"})

        self.assertEqual(lines, ["You lose control of the spell."])

    def test_render_utility_expiration(self):
        lines = SpellEffectPresenter.render_expiration({"effect_family": "utility", "effect_type": "light"})

        self.assertEqual(lines, ["The soft light around you fades."])

    def test_render_aoe_start(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "aoe", "target_count": 3, "targets": []}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You unleash a burst of energy!"])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Mage"), "Mage unleashes a burst of energy!")


if __name__ == "__main__":
    unittest.main()