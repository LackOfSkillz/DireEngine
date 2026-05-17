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

    def test_render_vitality_healing_messages(self):
        result = ActionResult.ok(data={"spell_id": "vitality_healing", "effect_payload": {"effect_family": "healing", "heal_amount": 12, "self_target": True, "target_key": "Empath", "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["Life floods back through you, restoring strength spent in service to others."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "Empath draws life back into themselves, looking visibly steadier.",
        )

    def test_render_heal_wounds_messages(self):
        result = ActionResult.ok(data={"spell_id": "heal_wounds", "effect_payload": {"effect_family": "healing", "heal_amount": 9, "self_target": True, "target_key": "Empath", "source_mana_type": "life", "healing_mode": "empath_wounds"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A steady wash of life knits your carried wounds back toward wholeness."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A patient wash of life settles over Empath, knitting their carried wounds toward wholeness.",
        )

    def test_render_heal_scars_messages(self):
        result = ActionResult.ok(data={"spell_id": "heal_scars", "effect_payload": {"effect_family": "healing", "heal_amount": 2, "self_target": True, "target_key": "Empath", "source_mana_type": "life", "healing_mode": "scars"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A slow warmth works through old scar tissue, easing what once seemed permanent."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A slow restorative warmth passes over Empath's old scars.",
        )

    def test_render_external_wound_healing_messages(self):
        result = ActionResult.ok(data={"spell_id": "external_wound_healing", "effect_payload": {"effect_family": "healing", "heal_amount": 4, "self_target": True, "target_key": "Empath", "source_mana_type": "life", "healing_mode": "external_wounds"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A focused warmth gathers across your skin, knitting fresh external injuries closed."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A focused warmth gathers across Empath's skin, sealing fresh external injuries.",
        )

    def test_render_internal_wound_healing_messages(self):
        result = ActionResult.ok(data={"spell_id": "internal_wound_healing", "effect_payload": {"effect_family": "healing", "heal_amount": 4, "self_target": True, "target_key": "Empath", "source_mana_type": "life", "healing_mode": "internal_wounds"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A focused warmth gathers deep beneath your skin, knitting fresh internal injuries closed."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A focused warmth sinks beneath Empath's skin, mending internal hurts.",
        )

    def test_render_heal_messages(self):
        result = ActionResult.ok(data={"spell_id": "heal", "effect_payload": {"effect_family": "healing", "heal_amount": 7, "self_target": True, "target_key": "Empath", "source_mana_type": "life", "healing_mode": "combined_heal"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A deep, encompassing warmth knits wounds and scars together at once, though the broad effort lacks the precision of a narrower working."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A broad restorative warmth settles over Empath, easing wounds and scars together.",
        )

    def test_render_flush_poisons_messages(self):
        result = ActionResult.ok(data={"spell_id": "flush_poisons", "effect_payload": {"effect_family": "utility", "utility_effect": "flush_poisons", "removed": True, "removed_amount": 15, "self_target": True, "target_key": "Empath", "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A purifying warmth courses through you, driving venom out of your blood."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A purifying warmth passes through Empath, flushing corruption from their body.",
        )

    def test_render_cure_disease_messages(self):
        result = ActionResult.ok(data={"spell_id": "cure_disease", "effect_payload": {"effect_family": "utility", "utility_effect": "cure_disease", "removed": True, "removed_amount": 12, "self_target": True, "target_key": "Empath", "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["Your body warms with renewed vitality as illness gives way before the spell's working."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A steady restorative warmth settles over Empath as illness loosens its hold.",
        )

    def test_render_refresh_messages(self):
        result = ActionResult.ok(data={"spell_id": "refresh", "effect_payload": {"effect_family": "utility", "utility_effect": "refresh", "fatigue_reduced": 9, "self_target": False, "target_key": "Patient", "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A bright wave of life passes through Patient, easing away their weariness."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["A bright wave of life washes through you, easing away some of your weariness."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "Empath calls a bright restorative pulse over Patient.",
        )

    def test_render_raise_power_messages(self):
        result = ActionResult.ok(data={"spell_id": "raise_power", "effect_payload": {"effect_family": "utility", "utility_effect": "raise_power", "self_target": True, "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You drive the Life mana around you into a higher pulse, leaving your whole group spent."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "Empath draws on Life mana so hard that the air itself seems to thrum, while the group sags with sudden weariness.",
        )

    def test_render_gift_of_life_messages(self):
        result = ActionResult.ok(data={"spell_id": "gift_of_life", "effect_payload": {"effect_family": "utility", "utility_effect": "gift_of_life", "self_target": True, "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You draw Gift of Life inward, strengthening your empathic poise and hardening your reserves."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "Empath draws Gift of Life inward, settling into a steadier empathic focus.",
        )

    def test_render_innocence_messages(self):
        result = ActionResult.ok(data={"spell_id": "innocence", "effect_payload": {"effect_family": "utility", "utility_effect": "innocence", "self_target": True, "undead_backfire_count": 0, "source_mana_type": "life"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A quiet stillness settles around you, signaling to nearby threats that you are no danger."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "Empath's presence softens with empathic calm, drawing the attention of nearby threats elsewhere.",
        )

    def test_render_zone_of_protection_messages(self):
        result = ActionResult.ok(data={"spell_id": "zone_of_protection", "effect_payload": {"effect_family": "warding", "group_target": True, "target_count": 2}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A large translucent sphere forms around you and your group, warding against hostile Life magic."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["A large translucent sphere forms around you, shimmering with protective Life resonance."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Empath"),
            "A large translucent sphere forms around Empath and companions, shimmering with protective Life resonance.",
        )

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

    def test_render_protection_from_evil_messages(self):
        result = ActionResult.ok(data={"spell_id": "protection_from_evil", "effect_payload": {"effect_family": "warding", "barrier_strength": 5, "duration": 20, "self_target": False, "target_key": "Pilgrim"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A soft white glow settles over Pilgrim, turning aside unholy menace."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["A soft white glow settles around you, warding off unholy force."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "A soft white glow gathers around Pilgrim at Cleric's invocation.",
        )

    def test_render_room_warding(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "warding", "barrier_strength": 5, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        line = SpellEffectPresenter.render_room(result, "Cleric")

        self.assertEqual(line, "Cleric draws a barrier tight around themselves.")

    def test_render_manifest_force_messages(self):
        result = ActionResult.ok(data={"spell_id": "manifest_force", "effect_payload": {"effect_family": "warding", "barrier_strength": 34, "duration": 781, "self_target": True, "target_key": "Mage"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You complete the cast. A faintly shimmering barrier of pure force coalesces around you, ready to absorb incoming blows."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Mage"),
            "Mage completes a spell. A faintly shimmering barrier of pure force coalesces around them.",
        )
        self.assertEqual(
            SpellEffectPresenter.render_expiration({"effect_family": "warding", "spell_id": "manifest_force"}),
            ["The shimmering barrier of force around you fades and dissipates as its spell ends."],
        )

    def test_render_group_warding(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "warding", "group_target": True, "target_count": 2}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You extend a protective field over 2 allies."])
        self.assertEqual(SpellEffectPresenter.render_target(result), ["A protective field settles over you."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Cleric"), "Cleric extends a protective field over the group.")

    def test_render_utility_light(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "utility", "utility_effect": "light", "self_target": True}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["A soft light forms around you."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Mage"), "A soft light gathers around Mage.")

    def test_render_bless_messages(self):
        result = ActionResult.ok(data={"spell_id": "bless", "effect_payload": {"effect_family": "utility", "utility_effect": "bless", "self_target": False, "target_key": "Guard"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A pure holy radiance settles over Guard, readying them against the unclean."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["Holy radiance settles over you, leaving you ready against the unclean."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Cleric lays a mantle of holy radiance over Guard.",
        )

    def test_render_holy_light_messages(self):
        result = ActionResult.ok(data={"spell_id": "holy_light", "effect_payload": {"effect_family": "utility", "utility_effect": "light", "self_target": True}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["Holy light blossoms around you, casting back the gloom."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Cleric"), "Holy light blossoms around Cleric, pushing back the gloom.")

    def test_render_utility_cleanse(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "utility", "utility_effect": "cleanse", "removed": True, "self_target": True}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You feel lingering effects wash away."])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Cleric"), "A cleansing wash passes over Cleric.")

    def test_render_spirit_beacon_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "spirit_beacon",
                "effect_payload": {
                    "effect_family": "utility",
                    "utility_effect": "spirit_beacon",
                    "self_target": True,
                    "recovery_point_key": "Sanctuary",
                },
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You anchor a spirit beacon here, fixing your departing soul toward Sanctuary."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Cleric fixes a pale spirit beacon around themselves.",
        )

    def test_render_uncurse_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "uncurse",
                "effect_payload": {
                    "effect_family": "utility",
                    "utility_effect": "uncurse",
                    "target_key": "Pilgrim",
                    "self_target": False,
                    "removed": True,
                    "death_sting_relieved": True,
                },
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You invoke Uncurse upon Pilgrim, easing Death's Sting and washing hostile magic away."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["A merciful cleansing eases Death's Sting and strips hostile magic away."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Cleric invokes Uncurse over Pilgrim, easing Death's Sting and hostile magic alike.",
        )

    def test_render_gauge_flow_messages(self):
        result = ActionResult.ok(data={"spell_id": "gauge_flow", "effect_payload": {"effect_family": "utility", "utility_effect": "gauge_flow", "self_target": True}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You complete the cast. Your senses extend outward, perceiving the flow of magical energies around you."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Jekar"),
            "Jekar completes a spell. Their gaze becomes distant, attuned to something beyond the visible.",
        )

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

    def test_render_strange_arrow_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "strange_arrow",
                "effect_payload": {"effect_family": "targeted_magic", "hit": True, "target_key": "Target", "final_damage": 11.0, "absorbed_by_ward": 0.0, "caster_key": "Jekar"},
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You complete the cast at Target. A jagged arrow of crackling energy lances out and strikes them for 11 damage!"],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["Jekar's spell completes at you. A jagged arrow of crackling energy lances into you, dealing 11 damage!"],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Jekar"),
            "Jekar's spell completes at Target. A jagged arrow of crackling energy strikes Target with a sharp crack of thunder.",
        )

    def test_render_aesrela_everild_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "aesrela_everild",
                "effect_payload": {
                    "effect_family": "targeted_magic",
                    "hit": True,
                    "target_key": "Target",
                    "final_damage": 9.0,
                    "absorbed_by_ward": 0.0,
                    "stunned": True,
                    "caster_key": "Jekar",
                },
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You invoke Aesrela Everild at Target. Bolts of silver flame hammer into them, leaving them stunned."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["Silver flame bolts hammer into you and leave you reeling, stunned."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Jekar"),
            "Jekar invokes Aesrela Everild. Bolts of silver flame crash into Target, leaving them visibly stunned.",
        )

    def test_render_revelation_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "revelation",
                "effect_payload": {"effect_family": "utility", "utility_effect": "revelation", "target_key": "HiddenTarget", "revealed": True, "self_target": False},
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You invoke Revelation upon HiddenTarget, wrenching them into plain sight."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["A divine flash strips away your concealment and leaves you exposed."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Cleric invokes Revelation upon HiddenTarget, forcing them into plain sight.",
        )

    def test_render_hand_of_tenemlor_messages(self):
        result = ActionResult.ok(
            data={
                "spell_id": "hand_of_tenemlor",
                "effect_payload": {"effect_family": "targeted_magic", "hit": True, "target_key": "Target", "final_damage": 8.0, "absorbed_by_ward": 0.0, "caster_key": "Jekar"},
            }
        )

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You invoke Hand of Tenemlor at Target. A cauterizing hand of holy fire sears their left hand for 8 damage!"],
        )
        self.assertEqual(
            SpellEffectPresenter.render_target(result),
            ["Jekar's spell sears your left hand with holy fire, dealing 8 damage!"],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Jekar"),
            "Jekar invokes Hand of Tenemlor. A blazing hand of holy fire sears Target's left hand.",
        )

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

    def test_render_burden_messages_and_expiration(self):
        result = ActionResult.ok(data={"spell_id": "burden", "effect_payload": {"effect_family": "debilitation", "effect_type": "burden", "hit": True, "target_key": "Target"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You complete the cast at Target. A weight settles onto them, dragging at them."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Jekar"),
            "Jekar's spell completes at Target. Target sags visibly, looking suddenly burdened.",
        )
        self.assertEqual(
            SpellEffectPresenter.render_expiration({"effect_family": "debilitation", "effect_type": "burden"}),
            ["The weight burdening you lifts. You feel your strength returning."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_expiration_room({"effect_family": "debilitation", "effect_type": "burden"}, "Target"),
            "Target straightens up, looking less burdened.",
        )

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

    def test_render_minor_physical_protection_expiration(self):
        self.assertEqual(
            SpellEffectPresenter.render_expiration({"effect_family": "warding", "spell_id": "minor_physical_protection"}),
            ["The silver ward around you thins and vanishes."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_expiration_room({"effect_family": "warding", "spell_id": "minor_physical_protection"}, "Cleric"),
            "The silver ward around Cleric thins and vanishes.",
        )

    def test_render_major_physical_protection_messages(self):
        result = ActionResult.ok(data={"spell_id": "major_physical_protection", "effect_payload": {"effect_family": "warding", "barrier_strength": 8, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A broad silver ward settles over you, hardening into a stronger bulwark against physical blows."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "A broad silver ward settles over Cleric.",
        )

    def test_render_halo_messages(self):
        result = ActionResult.ok(data={"spell_id": "halo", "effect_payload": {"effect_family": "warding", "barrier_strength": 8, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["Pinpoints of intense white light erupt around you, gathering into a dormant halo of force."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Pinpoints of intense white light whirl around Cleric, gathering into a dormant halo.",
        )

    def test_render_divine_radiance_messages_and_expiration(self):
        result = ActionResult.ok(data={"spell_id": "divine_radiance", "effect_payload": {"effect_family": "warding", "barrier_strength": 4, "duration": 20, "self_target": True, "target_key": "Cleric"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["A radiant holy aura surrounds you, spilling light and sheltering you from the unclean."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "A radiant holy aura blazes around Cleric.",
        )
        self.assertEqual(
            SpellEffectPresenter.render_expiration({"effect_family": "warding", "spell_id": "divine_radiance"}),
            ["The radiant holy aura around you dims, and the shadows begin to creep back in."],
        )

    def test_render_rejuvenation_messages(self):
        result = ActionResult.ok(data={"spell_id": "rejuvenation", "effect_payload": {"effect_family": "resurrection", "target_key": "Fallen", "corpse_key": "corpse of fallen"}})

        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["You cast Rejuvenation over Fallen, calling them back from death through a surge of holy will."],
        )
        self.assertEqual(
            SpellEffectPresenter.render_room(result, "Cleric"),
            "Cleric invokes Rejuvenation over corpse of fallen, and Fallen jolts back to life.",
        )

    def test_render_mass_rejuvenation_deferred_message(self):
        result = ActionResult.fail(errors=["Mass Rejuvenation's held-mana ritual is not yet implemented."], data={"spell_id": "mass_rejuvenation", "reason": "deferred_held_mana_ritual"})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["Mass Rejuvenation's held-mana ritual is not yet implemented."])

    def test_render_gauge_flow_expiration_room(self):
        self.assertEqual(
            SpellEffectPresenter.render_expiration_room({"effect_family": "utility", "effect_type": "gauge_flow"}, "Jekar"),
            "Jekar's distant gaze refocuses on the present.",
        )

    def test_render_aoe_start(self):
        result = ActionResult.ok(data={"effect_payload": {"effect_family": "aoe", "target_count": 3, "targets": []}})

        self.assertEqual(SpellEffectPresenter.render_self(result), ["You unleash a burst of energy!"])
        self.assertEqual(SpellEffectPresenter.render_room(result, "Mage"), "Mage unleashes a burst of energy!")


if __name__ == "__main__":
    unittest.main()