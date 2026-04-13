import unittest
from unittest.mock import patch

from domain.spells.spell_definitions import get_spell
from engine.presenters.spell_effect_presenter import SpellEffectPresenter
from engine.services.spell_contest_service import SpellContestService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.spellbook_service import SpellbookService
from engine.services.state_service import StateService
from tests.services.test_character_spell_runtime import RuntimeDummyCharacter, RuntimeDummyRoom


class SpellPvPInteractionTests(unittest.TestCase):
    def _learn(self, character, spell_id):
        spell = get_spell(spell_id)
        learned_via = "book" if "book" in (spell.acquisition_methods or []) else str((spell.acquisition_methods or ["npc"])[0])
        return SpellbookService.learn_spell(character, spell.id, learned_via)

    def _prepare_and_cast(self, caster, spell_id, room, *, target_name=None, mana=12):
        self.assertTrue(self._learn(caster, spell_id).success)
        self.assertTrue(caster.prepare_spell(f"{spell_id} {mana}"))
        self.assertTrue(caster.cast_spell(target_name=target_name))

    def test_player_vs_player_targeted_spell_uses_same_damage_path_once(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        defender.apply_warding_barrier(defender, "minor_barrier", strength=8, duration=20)
        room = RuntimeDummyRoom()
        room.add(attacker, defender)
        before_hp = defender.db.hp

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            self._prepare_and_cast(attacker, "flare", room, target_name="Defender")

        self.assertEqual(apply_damage_mock.call_count, 1)
        self.assertLess(defender.db.hp, before_hp)

    def test_player_vs_player_debilitation_updates_nested_state_and_modifier_reads(self):
        attacker = RuntimeDummyCharacter(profession="moon_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        room = RuntimeDummyRoom()
        room.add(attacker, defender)

        with patch.object(SpellContestService, "resolve_debilitation", wraps=SpellContestService.resolve_debilitation) as contest_mock:
            self._prepare_and_cast(attacker, "daze", room, target_name="Defender", mana=14)

        debilitation = dict((defender.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertTrue(contest_mock.called)
        self.assertIn("daze", debilitation)
        self.assertGreater(defender.get_effect_modifier("magic_defense"), 0)

    def test_player_vs_player_buff_debuff_stack_matches_pve_contest_rules(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        clean = RuntimeDummyCharacter(profession="cleric", key="Clean")
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        room = RuntimeDummyRoom()
        room.add(attacker, defender, clean, seer)

        self._prepare_and_cast(attacker, "bolster", room, mana=10)
        self._prepare_and_cast(seer, "daze", room, target_name="Defender", mana=14)
        flare = get_spell("flare")
        pvp_result = SpellEffectService.apply_spell(attacker, flare, 20.0, quality="normal", target=defender)
        clean_result = SpellEffectService.apply_spell(attacker, flare, 20.0, quality="normal", target=clean)

        self.assertGreater(
            float(pvp_result.data["effect_payload"]["contest_margin"]),
            float(clean_result.data["effect_payload"]["contest_margin"]),
        )

    def test_self_only_pvp_spell_does_not_target_other_player(self):
        caster = RuntimeDummyCharacter(profession="cleric", key="Caster")
        other = RuntimeDummyCharacter(profession="cleric", key="Other")
        room = RuntimeDummyRoom()
        room.add(caster, other)

        self._prepare_and_cast(caster, "minor_barrier", room, target_name="Other", mana=12)

        self.assertIsNotNone(caster.get_state("warding_barrier"))
        self.assertIsNone(other.get_state("warding_barrier"))

    def test_pvp_ward_vs_targeted_matches_pve_barrier_behavior(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        defender.apply_warding_barrier(defender, "minor_barrier", strength=200, duration=20)
        room = RuntimeDummyRoom()
        room.add(attacker, defender)
        before_hp = defender.db.hp

        self._prepare_and_cast(attacker, "flare", room, target_name="Defender")

        self.assertEqual(defender.db.hp, before_hp)
        self.assertTrue(any("absorbs it completely" in line.lower() for line in attacker.messages))

    def test_pvp_debuff_expiry_removes_modifier_once(self):
        attacker = RuntimeDummyCharacter(profession="moon_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        room = RuntimeDummyRoom()
        room.add(attacker, defender)

        self._prepare_and_cast(attacker, "daze", room, target_name="Defender", mana=14)
        before = defender.get_effect_modifier("magic_defense")
        duration = int(((defender.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}) or {}).get("duration", 0) or 0)
        for _ in range(duration):
            defender.process_magic_states()
        after = defender.get_effect_modifier("magic_defense")

        self.assertGreater(before, 0)
        self.assertEqual(after, 0)

    def test_pvp_no_double_damage_with_barrier_and_active_effects(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        room = RuntimeDummyRoom()
        room.add(attacker, defender, seer)
        defender.apply_warding_barrier(defender, "minor_barrier", strength=8, duration=20)
        self._prepare_and_cast(seer, "daze", room, target_name="Defender", mana=14)
        before_hp = defender.db.hp

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            self._prepare_and_cast(attacker, "flare", room, target_name="Defender")

        self.assertEqual(apply_damage_mock.call_count, 1)
        self.assertLess(defender.db.hp, before_hp)

    def test_player_vs_player_cyclic_damage_ticks_once(self):
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        room = RuntimeDummyRoom()
        room.add(seer, defender)

        self._prepare_and_cast(seer, "wither", room, target_name="Defender", mana=14)
        before_hp = defender.db.hp
        with patch("engine.services.state_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            seer.process_magic_states()

        self.assertEqual(apply_damage_mock.call_count, 1)
        self.assertLess(defender.db.hp, before_hp)

    def test_player_vs_player_aoe_hits_multiple_players_independently(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender_a = RuntimeDummyCharacter(profession="cleric", key="DefenderA")
        defender_b = RuntimeDummyCharacter(profession="cleric", key="DefenderB")
        defender_c = RuntimeDummyCharacter(profession="cleric", key="DefenderC")
        room = RuntimeDummyRoom()
        room.add(attacker, defender_a, defender_b, defender_c)
        before = {obj.key: obj.db.hp for obj in (defender_a, defender_b, defender_c)}

        with patch("engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            self._prepare_and_cast(attacker, "arc_burst", room, mana=16)

        self.assertEqual(apply_damage_mock.call_count, 3)
        self.assertLess(defender_a.db.hp, before["DefenderA"])
        self.assertLess(defender_b.db.hp, before["DefenderB"])
        self.assertLess(defender_c.db.hp, before["DefenderC"])

    def test_player_vs_player_room_cyclic_hits_players_once_per_tick(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender_a = RuntimeDummyCharacter(profession="cleric", key="DefenderA")
        defender_b = RuntimeDummyCharacter(profession="cleric", key="DefenderB")
        room = RuntimeDummyRoom()
        room.add(attacker, defender_a, defender_b)

        self._prepare_and_cast(attacker, "storm_field", room, mana=16)
        before = {obj.key: obj.db.hp for obj in (defender_a, defender_b)}
        with patch("engine.services.state_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            attacker.process_magic_states()

        self.assertEqual(apply_damage_mock.call_count, 2)
        self.assertLess(defender_a.db.hp, before["DefenderA"])
        self.assertLess(defender_b.db.hp, before["DefenderB"])

    def test_pvp_presenter_messages_stay_coherent_without_duplication(self):
        attacker = RuntimeDummyCharacter(profession="warrior_mage", key="Attacker")
        defender = RuntimeDummyCharacter(profession="cleric", key="Defender")
        room = RuntimeDummyRoom()
        room.add(attacker, defender)
        spell = get_spell("flare")
        result = SpellEffectService.apply_spell(attacker, spell, 20.0, quality="normal", target=defender)

        self.assertEqual(len(SpellEffectPresenter.render_self(result)), 1)
        self.assertEqual(len(SpellEffectPresenter.render_target(result)), 1)
        self.assertIsNotNone(SpellEffectPresenter.render_room(result, attacker.key))


if __name__ == "__main__":
    unittest.main()