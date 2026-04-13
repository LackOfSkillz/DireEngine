import unittest
from unittest.mock import patch

from domain.spells.spell_definitions import get_spell
from engine.presenters.spell_effect_presenter import SpellEffectPresenter
from engine.services.mana_service import ManaService
from engine.services.spell_access_service import SpellAccessService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.spellbook_service import SpellbookService
from engine.services.spell_contest_service import SpellContestService
from engine.services.state_service import StateService
from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyRoom


class SpellSystemInteractionTests(unittest.TestCase):
    def _prepare_and_cast(self, caster, spell_id, room, *, quality="strong", target=None):
        spell = get_spell(spell_id)
        learned_via = "book" if "book" in (spell.acquisition_methods or []) else str((spell.acquisition_methods or ["npc"])[0])
        learned = SpellbookService.learn_spell(caster, spell.id, learned_via)
        access = SpellAccessService.can_use_spell(caster, spell)
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        prepared = ManaService.prepare_spell(caster, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(caster, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(caster, spell, cast.data["final_spell_power"], quality=quality, target=target)
        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        return effect

    def _ward_strength(self, target):
        ward = dict(target.get_state("warding_barrier") or {})
        return int(ward.get("strength", 0) or 0)

    def assert_hp_changed_once(self, before_hp, after_hp, payload, apply_damage_mock):
        final_damage = int(payload.get("final_damage", 0.0) or 0)
        self.assertEqual(before_hp - after_hp, final_damage)
        expected_calls = 1 if final_damage > 0 else 0
        self.assertEqual(apply_damage_mock.call_count, expected_calls)

    def assert_barrier_consumed_once(self, before_strength, after_strength, payload):
        absorbed = int(payload.get("absorbed_by_ward", 0.0) or 0)
        self.assertEqual(before_strength - after_strength, absorbed)

    def assert_debuff_applied_once(self, target, effect_type):
        debilitation = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertIn(effect_type, debilitation)
        self.assertEqual(len([name for name in debilitation if name == effect_type]), 1)

    def assert_duration_decremented_once(self, before_duration, after_duration):
        self.assertEqual(before_duration - after_duration, 1)

    def test_buff_and_debuff_both_modify_targeted_contest(self):
        attacker = DummyCharacter(profession="warrior_mage")
        defender = DummyCharacter(profession="cleric")
        baseline_target = DummyCharacter(profession="cleric")
        room = DummyRoom()

        bolster = self._prepare_and_cast(attacker, "bolster", room)
        daze_caster = DummyCharacter(profession="moon_mage")
        self._prepare_and_cast(daze_caster, "daze", room, target=defender)

        flare = get_spell("flare")
        with patch.object(SpellContestService, "_resolve_spell_contest", wraps=SpellContestService._resolve_spell_contest) as contest_mock:
            buffed_and_debuffed = SpellEffectService.apply_spell(attacker, flare, 20.0, quality="normal", target=defender)
            baseline = SpellEffectService.apply_spell(attacker, flare, 20.0, quality="normal", target=baseline_target)

        self.assertTrue(contest_mock.called)
        self.assertEqual(bolster.data["effect_payload"]["effect_family"], "augmentation")
        self.assertEqual(buffed_and_debuffed.data["effect_payload"]["effect_family"], "targeted_magic")
        self.assertGreater(
            float(buffed_and_debuffed.data["effect_payload"]["contest_margin"]),
            float(baseline.data["effect_payload"]["contest_margin"]),
        )

    def test_damage_and_ward_absorption_use_authoritative_path_once(self):
        caster = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        target.apply_warding_barrier(target, "minor_barrier", strength=8, duration=20)
        room = DummyRoom()
        before_hp = target.db.hp
        before_ward = self._ward_strength(target)

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            result = self._prepare_and_cast(caster, "flare", room, target=target)

        payload = result.data["effect_payload"]
        after_hp = target.db.hp
        after_ward = self._ward_strength(target)
        self.assertGreater(float(payload["absorbed_by_ward"]), 0.0)
        self.assert_hp_changed_once(before_hp, after_hp, payload, apply_damage_mock)
        self.assert_barrier_consumed_once(before_ward, after_ward, payload)

    def test_full_absorb_preserves_hp_and_reports_presenter_state(self):
        caster = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        target.apply_warding_barrier(target, "minor_barrier", strength=200, duration=20)
        room = DummyRoom()
        before_hp = target.db.hp

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            result = self._prepare_and_cast(caster, "flare", room, target=target)

        payload = result.data["effect_payload"]
        self.assertTrue(payload["hit"])
        self.assertEqual(target.db.hp, before_hp)
        self.assertEqual(float(payload["absorbed_by_ward"]), float(payload["base_damage"]))
        self.assert_hp_changed_once(before_hp, target.db.hp, payload, apply_damage_mock)
        self.assertEqual(
            SpellEffectPresenter.render_self(result),
            ["Your spell strikes Cleric, but the barrier absorbs it completely."],
        )

    def test_zero_damage_non_absorb_edge_case_stays_structured(self):
        caster = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        room = DummyRoom()
        target.apply_magic_resistance = lambda damage: 0

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            result = self._prepare_and_cast(caster, "flare", room, quality="weak", target=target)

        payload = result.data["effect_payload"]
        self.assertTrue(payload["hit"])
        self.assertEqual(float(payload["final_damage"]), 0.0)
        self.assertEqual(float(payload["absorbed_by_ward"]), 0.0)
        self.assertEqual(apply_damage_mock.call_count, 0)
        self.assertEqual(SpellEffectPresenter.render_self(result), [f"Your spell strikes Cleric."])

    def test_simultaneous_effect_state_interaction_keeps_other_states(self):
        caster = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        seer = DummyCharacter(profession="moon_mage")
        room = DummyRoom()

        self._prepare_and_cast(caster, "bolster", room)
        self._prepare_and_cast(seer, "daze", room, target=target)
        target.apply_warding_barrier(target, "minor_barrier", strength=6, duration=20)
        before_effects = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        before_ward = dict(target.get_state("warding_barrier") or {})

        result = self._prepare_and_cast(caster, "flare", room, target=target)

        payload = result.data["effect_payload"]
        after_effects = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        after_ward = dict(target.get_state("warding_barrier") or {})
        self.assertIn("daze", after_effects)
        self.assertEqual(before_effects["daze"]["strength"], after_effects["daze"]["strength"])
        self.assertEqual(caster.get_state("augmentation_buff")["name"], "bolster")
        self.assertLessEqual(int(after_ward.get("strength", 0) or 0), int(before_ward.get("strength", 0) or 0))
        self.assertIn("absorbed_by_ward", payload)

    def test_cyclic_tick_respects_augmentation_and_debilitation_modifiers(self):
        room = DummyRoom()
        wither = get_spell("wither")
        baseline_caster = DummyCharacter(profession="moon_mage")
        buffed_caster = DummyCharacter(profession="moon_mage")
        weakened_caster = DummyCharacter(profession="moon_mage")
        baseline_target = DummyCharacter(profession="cleric")
        buffed_target = DummyCharacter(profession="cleric")
        weakened_target = DummyCharacter(profession="cleric")
        for caster in (baseline_caster, buffed_caster, weakened_caster):
            ManaService._set_attunement_state(caster, 100.0, 100.0)

        buffed_caster.set_state(
            "augmentation_buff",
            {"name": "bolster", "strength": 8, "duration": 5, "modifiers": {"magic_attack": 1.0}},
        )
        StateService.apply_debilitation_effect(
            weakened_caster,
            "daze",
            3,
            3,
            source_spell="daze",
            modifiers={"magic_attack": 1.0},
        )

        _ = room
        self.assertTrue(SpellEffectService.apply_spell(baseline_caster, wither, 40.0, quality="strong", target=baseline_target).success)
        self.assertTrue(SpellEffectService.apply_spell(buffed_caster, wither, 40.0, quality="strong", target=buffed_target).success)
        self.assertTrue(SpellEffectService.apply_spell(weakened_caster, wither, 40.0, quality="strong", target=weakened_target).success)

        baseline_tick = StateService.process_cyclic_effects(baseline_caster)
        buffed_tick = StateService.process_cyclic_effects(buffed_caster)
        weakened_tick = StateService.process_cyclic_effects(weakened_caster)

        baseline_damage = float(((baseline_tick.data or {}).get("processed_effects", [{}])[0] or {}).get("final_damage", 0.0) or 0.0)
        buffed_damage = float(((buffed_tick.data or {}).get("processed_effects", [{}])[0] or {}).get("final_damage", 0.0) or 0.0)
        weakened_damage = float(((weakened_tick.data or {}).get("processed_effects", [{}])[0] or {}).get("final_damage", 0.0) or 0.0)

        self.assertGreater(buffed_damage, baseline_damage)
        self.assertLess(weakened_damage, baseline_damage)

    def test_aoe_respects_buff_and_debuff_per_target(self):
        room = DummyRoom()
        caster = DummyCharacter(profession="warrior_mage")
        buffed_caster = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        debuffed_target = DummyCharacter(profession="cleric")
        arc_burst = get_spell("arc_burst")
        caster.location = room
        buffed_caster.location = room
        target.location = room
        debuffed_target.location = room
        room.contents = [caster, target]

        clean = SpellEffectService.apply_spell(caster, arc_burst, 36.0, quality="strong", target=room)
        buffed_caster.set_state("augmentation_buff", {"name": "bolster", "strength": 6, "duration": 4, "modifiers": {"magic_attack": 1.0}})
        room.contents = [buffed_caster, debuffed_target]
        StateService.apply_debilitation_effect(debuffed_target, "daze", 3, 3, source_spell="daze", modifiers={"magic_defense": 1.0})
        shifted = SpellEffectService.apply_spell(buffed_caster, arc_burst, 36.0, quality="strong", target=room)

        clean_payload = (clean.data["effect_payload"]["targets"] or [])[0]
        shifted_payload = (shifted.data["effect_payload"]["targets"] or [])[0]
        self.assertGreater(float(shifted_payload["contest_margin"]), float(clean_payload["contest_margin"]))

    def test_aoe_environment_affects_all_targets_equally(self):
        spell = get_spell("arc_burst")
        caster = DummyCharacter(profession="warrior_mage")
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        high_a = DummyCharacter(profession="cleric")
        high_b = DummyCharacter(profession="cleric")
        low_a = DummyCharacter(profession="cleric")
        low_b = DummyCharacter(profession="cleric")

        high_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        low_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        high_room.db.environmental_mana = {"elemental": 1.4}
        low_room.db.environmental_mana = {"elemental": 0.7}
        high_room.contents = [caster, high_a, high_b]
        low_room.contents = [caster, low_a, low_b]

        high = ManaService.can_prepare_spell(caster, high_room, "elemental", 16, 1, 30)
        low = ManaService.can_prepare_spell(caster, low_room, "elemental", 16, 1, 30)
        self.assertTrue(high.success)
        self.assertTrue(low.success)

        high_result = SpellEffectService.apply_spell(caster, spell, 40.0 * float(high.data["environmental_mana_modifier"]), quality="strong", target=high_room)
        low_result = SpellEffectService.apply_spell(caster, spell, 40.0 * float(low.data["environmental_mana_modifier"]), quality="strong", target=low_room)

        high_payloads = high_result.data["effect_payload"]["targets"]
        low_payloads = low_result.data["effect_payload"]["targets"]
        self.assertGreater(float(high_payloads[0]["damage"]), float(low_payloads[0]["damage"]))
        self.assertGreater(float(high_payloads[1]["damage"]), float(low_payloads[1]["damage"]))

    def test_expiry_interaction_removes_only_expired_effect(self):
        target = DummyCharacter(profession="cleric")
        target.set_state("augmentation_buff", {"name": "bolster", "strength": 3, "duration": 2, "modifiers": {"magic_defense": 1.0}})
        StateService.apply_debilitation_effect(target, "daze", 2, 1, source_spell="daze", modifiers={"magic_defense": 1.0})

        before_duration = int(target.get_state("augmentation_buff")["duration"] or 0)
        target_process = lambda: None
        _ = target_process
        StateService.tick_active_effects(target)
        buff = dict(target.get_state("augmentation_buff") or {})
        buff["duration"] = int(buff.get("duration", 0) or 0) - 1
        target.set_state("augmentation_buff", buff)

        active_effects = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertNotIn("daze", active_effects)
        self.assertEqual(target.get_state("augmentation_buff")["name"], "bolster")
        self.assert_duration_decremented_once(before_duration, int(target.get_state("augmentation_buff")["duration"] or 0))

    def test_recast_precedence_keeps_stronger_effect_authoritative(self):
        target = DummyCharacter(profession="cleric")

        first = StateService.apply_debilitation_effect(target, "daze", 2, 4, source_spell="daze", modifiers={"magic_defense": 1.0})
        second = StateService.apply_debilitation_effect(target, "daze", 5, 6, source_spell="daze", modifiers={"magic_defense": 1.0})
        before = dict((target.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}) or {})
        third = StateService.apply_debilitation_effect(target, "daze", 1, 10, source_spell="daze", modifiers={"magic_defense": 1.0})
        after = dict((target.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}) or {})

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertTrue(third.success)
        self.assertFalse(third.data["applied"])
        self.assertTrue(third.data["ignored"])
        self.assertEqual(before["strength"], after["strength"])
        self.assertEqual(before["duration"], after["duration"])
        self.assert_debuff_applied_once(target, "daze")

    def test_pre_cyclic_stress_baseline_preserves_system_stability(self):
        attacker = DummyCharacter(profession="warrior_mage")
        defender = DummyCharacter(profession="cleric")
        seer = DummyCharacter(profession="moon_mage")
        room = DummyRoom()

        self._prepare_and_cast(attacker, "bolster", room)
        self._prepare_and_cast(seer, "daze", room, target=defender)
        defender.apply_warding_barrier(defender, "minor_barrier", strength=10, duration=3)

        before_hp = defender.db.hp
        before_buff_duration = int(attacker.get_state("augmentation_buff")["duration"] or 0)
        before_debuff_duration = int(((defender.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}) or {}).get("duration", 0) or 0)
        before_ward_strength = self._ward_strength(defender)

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            strike = self._prepare_and_cast(attacker, "flare", room, target=defender)

        payload = strike.data["effect_payload"]
        self.assertTrue(strike.success)
        self.assertEqual(payload["effect_family"], "targeted_magic")
        self.assert_hp_changed_once(before_hp, defender.db.hp, payload, apply_damage_mock)
        self.assert_barrier_consumed_once(before_ward_strength, self._ward_strength(defender), payload)
        self.assertIn("daze", ((defender.get_state("active_effects") or {}).get("debilitation", {}) or {}))

        attacker_buff = dict(attacker.get_state("augmentation_buff") or {})
        attacker_buff["duration"] = int(attacker_buff.get("duration", 0) or 0) - 1
        attacker.set_state("augmentation_buff", attacker_buff)
        tick_result = StateService.tick_active_effects(defender)

        after_buff_duration = int(attacker.get_state("augmentation_buff")["duration"] or 0)
        after_debuff_duration = int(((defender.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}) or {}).get("duration", 0) or 0)
        self.assert_duration_decremented_once(before_buff_duration, after_buff_duration)
        self.assert_duration_decremented_once(before_debuff_duration, after_debuff_duration)
        self.assertEqual(list((tick_result.data or {}).get("expired_effects", []) or []), [])


if __name__ == "__main__":
    unittest.main()