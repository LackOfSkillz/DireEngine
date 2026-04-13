import unittest
from unittest.mock import patch

from domain.spells.spell_definitions import get_spell
from engine.presenters.mana_presenter import ManaPresenter
from engine.services.mana_service import ManaService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.state_service import StateService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="commoner"):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.location = None
        self.pk = 1
        self.id = 1
        self.key = "Dummy"
        self.profession = profession
        self.devotion = 0
        self.devotion_max = 0
        self.empath_shock = 0
        self.healing_modifier_override = None
        self.hp = 100
        self.db.hp = 100
        self.db.max_hp = 100
        self.states = {}

    def ensure_core_defaults(self):
        return None

    def is_profession(self, profession):
        return self.profession == str(profession or "").strip().lower()

    def get_devotion(self):
        return self.devotion

    def get_devotion_max(self):
        return self.devotion_max

    def adjust_devotion(self, amount, sync=False):
        _sync = sync
        self.devotion += int(amount)
        if self.devotion > self.devotion_max:
            self.devotion = self.devotion_max
        if self.devotion < 0:
            self.devotion = 0
        return self.devotion

    def get_empath_healing_modifier(self):
        if self.healing_modifier_override is not None:
            return self.healing_modifier_override
        return 1.0 - ((self.empath_shock / 100.0) * 0.80)

    def get_empath_shock(self):
        return self.empath_shock

    def get_skill(self, name):
        mapping = {
            "attunement": 100,
            "arcana": 100,
            "targeted_magic": 100,
            "utility": 100,
            "warding": 100,
            "augmentation": 100,
        }
        return mapping.get(name, 100)

    def get_stat(self, name):
        mapping = {"intelligence": 30, "discipline": 30, "wisdom": 30}
        return mapping.get(name, 30)

    def get_profession(self):
        return self.profession

    def set_hp(self, value):
        self.hp = int(value)
        self.db.hp = self.hp

    def set_state(self, key, value):
        self.states[key] = value

    def get_state(self, key):
        return self.states.get(key)

    def clear_state(self, key):
        self.states.pop(key, None)

    def adjust_empath_shock(self, amount):
        self.empath_shock += int(amount)
        return self.empath_shock

    def get_effect_modifier(self, modifier_key, category="debilitation"):
        active_effects = dict((self.get_state("active_effects") or {}).get(category, {}) or {})
        total = 0.0
        for effect in active_effects.values():
            modifiers = dict(effect.get("modifiers") or {})
            total += float(effect.get("strength", 0) or 0) * float(modifiers.get(modifier_key, 0.0) or 0.0)
        return int(round(total))

    def apply_magic_resistance(self, incoming_power):
        return float(incoming_power)

    def apply_ward_absorption(self, target, damage):
        _target = target
        return damage


class DummyRoom:
    def __init__(self, mana=None):
        self.db = DummyHolder()
        if mana is not None:
            self.db.mana = dict(mana)


class ManaServiceTests(unittest.TestCase):
    def test_low_environment_produces_higher_prep_cost_than_rich_environment(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 100.0, 100.0)
        poor_room = DummyRoom({"holy": 0.5, "life": 0.5, "elemental": 0.5, "lunar": 0.5})
        rich_room = DummyRoom({"holy": 1.5, "life": 1.5, "elemental": 1.5, "lunar": 1.5})

        poor = ManaService.can_prepare_spell(character, poor_room, "holy", 20, 10, 30)
        rich = ManaService.can_prepare_spell(character, rich_room, "holy", 20, 10, 30)

        self.assertTrue(poor.success)
        self.assertTrue(rich.success)
        self.assertGreater(int(poor.data["prep_cost"]), int(rich.data["prep_cost"]))

    def test_zero_attunement_blocks_preparation(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 0.0, 100.0)
        room = DummyRoom()

        result = ManaService.can_prepare_spell(character, room, "holy", 20, 10, 30)

        self.assertFalse(result.success)
        self.assertIn("Not enough attunement.", result.errors)

    def test_prepare_spell_stores_prepared_state(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 100.0, 100.0)
        room = DummyRoom()

        result = ManaService.prepare_spell(character, room, "holy", 20, 10, 30)

        self.assertTrue(result.success)
        prepared = ManaService._get_prepared_mana_state(character)
        self.assertIsNotNone(prepared)
        self.assertEqual(prepared["realm"], "holy")
        self.assertEqual(prepared["mana_input"], 20)
        self.assertEqual(prepared["held_mana"], 0)
        self.assertTrue(ManaPresenter.render_prepare(result))

    def test_harness_increases_held_mana_and_reduces_attunement(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 100.0, 100.0)
        room = DummyRoom()
        ManaService.prepare_spell(character, room, "holy", 20, 10, 30)
        attunement_before = ManaService._get_attunement_state(character)["current"]

        result = ManaService.harness_mana(character, 10, 100, 50)

        self.assertTrue(result.success)
        prepared = ManaService._get_prepared_mana_state(character)
        attunement_after = ManaService._get_attunement_state(character)["current"]
        self.assertEqual(prepared["held_mana"], 10)
        self.assertLess(attunement_after, attunement_before)
        self.assertTrue(ManaPresenter.render_harness(result))

    def test_cast_spell_clears_prepared_state(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 100.0, 100.0)
        room = DummyRoom()
        character.location = room
        ManaService.prepare_spell(character, room, "holy", 20, 10, 30)

        result = ManaService.cast_spell(character, "holy", 100)

        self.assertTrue(result.success)
        self.assertIsNone(ManaService._get_prepared_mana_state(character))
        self.assertIn("final_spell_power", result.data)
        self.assertIn("backlash_chance", result.data)
        self.assertTrue(ManaPresenter.render_cast(result))

    def test_cleric_devotion_increases_effective_holy_access(self):
        cleric = DummyCharacter(profession="cleric")
        cleric.devotion = 100
        cleric.devotion_max = 100
        room = DummyRoom()

        modifier = ManaService._get_profession_env_modifier(cleric, "holy")
        effective = ManaService._get_effective_env_mana(cleric, room, "holy")

        self.assertEqual(modifier, 1.25)
        self.assertEqual(effective, 1.25)

    def test_empath_shock_reduces_healing_modifier(self):
        empath = DummyCharacter(profession="empath")
        empath.empath_shock = 50

        modifier = ManaService._get_empath_healing_modifier(empath)

        self.assertLess(modifier, 1.0)
        self.assertEqual(modifier, 0.6)

    def test_zero_values_are_preserved_in_state(self):
        character = DummyCharacter()
        room = DummyRoom({"holy": 0.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0})
        ManaService._set_attunement_state(character, 0.0, 100.0)
        ManaService._set_prepared_mana_state(character, {"realm": "holy", "mana_input": 5, "prep_cost": 2, "held_mana": 0, "min_prep": 5, "max_prep": 10})

        self.assertEqual(ManaService._get_room_mana(room, "holy"), 0.0)
        self.assertEqual(ManaService._get_attunement_state(character)["current"], 0.0)
        self.assertEqual(ManaService._get_prepared_mana_state(character)["held_mana"], 0)

    def test_legacy_scalar_attunement_storage_is_supported(self):
        character = DummyCharacter()
        character.db.attunement = 12.0
        character.db.max_attunement = 30.0

        state = ManaService._get_attunement_state(character)
        ManaService.restore_attunement(character, 5)

        self.assertEqual(state["current"], 12.0)
        self.assertEqual(state["max"], 30.0)
        self.assertEqual(character.db.attunement, 17.0)
        self.assertEqual(character.db.max_attunement, 30.0)

    def test_moon_mage_effective_mana_ignores_room_value(self):
        character = DummyCharacter(profession="moon mage")
        character.db.lunar_global_state = 1.4
        character.db.celestial_alignment_modifier = 1.0
        character.db.weather_modifier = 1.0
        room = DummyRoom({"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 0.0})

        effective = ManaService._get_effective_env_mana(character, room, "lunar")

        self.assertEqual(effective, 1.4)

    def test_warrior_mage_bonus_increases_elemental_mana(self):
        character = DummyCharacter(profession="warrior mage")
        character.db.elemental_alignment_bonus = 0.2
        room = DummyRoom({"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0})

        effective = ManaService._get_effective_env_mana(character, room, "elemental")

        self.assertEqual(effective, 1.2)

    def test_cast_spell_can_resolve_excellent_band(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 100.0, 100.0)
        room = DummyRoom()
        character.location = room
        ManaService.prepare_spell(character, room, "holy", 20, 10, 30)

        with patch("engine.services.mana_service.random.uniform", return_value=10.0), patch("engine.services.mana_service.random.random", return_value=1.0):
            result = ManaService.cast_spell(character, "holy", 220)

        self.assertEqual(result.data["success_band"], "excellent")
        self.assertGreater(result.data["final_spell_power"], 0.0)
        self.assertIn("exceptional control", ManaPresenter.render_cast(result)[0])

    def test_cast_spell_can_resolve_partial_band(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 80.0, 100.0)
        room = DummyRoom({"holy": 0.5, "life": 0.5, "elemental": 0.5, "lunar": 0.5})
        character.location = room
        ManaService._set_prepared_mana_state(character, {"realm": "holy", "mana_input": 20, "prep_cost": 5, "held_mana": 0, "min_prep": 10, "max_prep": 30, "safe_mana": 12, "tier": 4, "base_difficulty": 50.0})

        with patch("engine.services.mana_service.random.uniform", return_value=2.0), patch("engine.services.mana_service.random.random", return_value=1.0):
            result = ManaService.cast_spell(character, "holy", 60)

        self.assertEqual(result.data["success_band"], "partial")
        self.assertGreater(result.data["final_spell_power"], 0.0)
        self.assertIn("weakly", ManaPresenter.render_cast(result)[0])

    def test_cast_spell_can_resolve_failure_without_backlash(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 80.0, 100.0)
        room = DummyRoom({"holy": 0.6, "life": 0.6, "elemental": 0.6, "lunar": 0.6})
        character.location = room
        ManaService._set_prepared_mana_state(character, {"realm": "holy", "mana_input": 20, "prep_cost": 5, "held_mana": 0, "min_prep": 10, "max_prep": 30, "safe_mana": 5, "tier": 5, "base_difficulty": 58.0})

        with patch("engine.services.mana_service.random.uniform", return_value=-9.0), patch("engine.services.mana_service.random.random", return_value=0.99):
            result = ManaService.cast_spell(character, "holy", 100)

        self.assertEqual(result.data["success_band"], "failure")
        self.assertNotIn("backlash_payload", result.data)
        self.assertIn("fizzles", ManaPresenter.render_cast(result)[0])

    def test_cast_spell_can_trigger_backlash_payload(self):
        character = DummyCharacter(profession="warrior mage")
        ManaService._set_attunement_state(character, 10.0, 100.0)
        room = DummyRoom({"elemental": 0.4, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        character.location = room
        ManaService._set_prepared_mana_state(character, {"realm": "elemental", "mana_input": 20, "prep_cost": 5, "held_mana": 0, "min_prep": 10, "max_prep": 30, "safe_mana": 5, "tier": 6, "base_difficulty": 80.0})

        with patch("engine.services.mana_service.random.uniform", return_value=-10.0), patch("engine.services.mana_service.random.random", return_value=0.0):
            result = ManaService.cast_spell(character, "elemental", 10)

        self.assertEqual(result.data["success_band"], "backlash")
        self.assertIn("backlash_payload", result.data)
        self.assertGreater(result.data["warrior_mage_self_hit"], 0)
        self.assertLess(character.hp, 100)
        self.assertIn("violent backlash", ManaPresenter.render_cast(result)[0])

    def test_profession_specific_backlash_payloads_are_reported(self):
        empath = DummyCharacter(profession="empath")
        cleric = DummyCharacter(profession="cleric")
        cleric.devotion = 100
        cleric.devotion_max = 100

        empath_payload = ManaService._apply_backlash_payload(empath, {"severity": 2, "shock_gain": 16, "attunement_burn_ratio": 0.0})
        cleric_payload = ManaService._apply_backlash_payload(cleric, {"severity": 2, "devotion_loss_ratio": 0.08, "attunement_burn_ratio": 0.0})

        self.assertEqual(empath_payload["shock_gain"], 16)
        self.assertEqual(empath.empath_shock, 16)
        self.assertGreater(cleric_payload["devotion_loss"], 0)
        self.assertLess(cleric.devotion, 100)

    def test_calculate_cyclic_tick_cost_scales_from_safe_mana_and_power(self):
        low = ManaService.calculate_cyclic_tick_cost(10, 10.0, {"mana_per_tick_scale": 0.1})
        high = ManaService.calculate_cyclic_tick_cost(20, 40.0, {"mana_per_tick_scale": 0.2})

        self.assertEqual(low, 1)
        self.assertEqual(high, 4)

    def test_consume_mana_fails_when_attunement_is_insufficient(self):
        character = DummyCharacter()
        ManaService._set_attunement_state(character, 1.0, 100.0)

        result = ManaService.consume_mana(character, 3)

        self.assertFalse(result.success)
        self.assertEqual(float(result.data["remaining_mana"]), 1.0)

    def test_environmental_modifier_defaults_to_neutral(self):
        room = DummyRoom()

        self.assertEqual(ManaService.get_environmental_modifier(room, "life"), 1.0)

    def test_environmental_modifier_changes_effective_environment(self):
        character = DummyCharacter(profession="warrior_mage")
        ManaService._set_attunement_state(character, 100.0, 100.0)
        high_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        low_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        high_room.db.environmental_mana = {"elemental": 1.5}
        low_room.db.environmental_mana = {"elemental": 0.8}

        high = ManaService.can_prepare_spell(character, high_room, "elemental", 12, 1, 30)
        low = ManaService.can_prepare_spell(character, low_room, "elemental", 12, 1, 30)

        self.assertTrue(high.success)
        self.assertTrue(low.success)
        self.assertGreater(float(high.data["effective_env_mana"]), float(low.data["effective_env_mana"]))

    def test_environmental_modifier_increases_cast_power(self):
        character = DummyCharacter(profession="warrior_mage")
        high_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        low_room = DummyRoom({"elemental": 1.0, "holy": 1.0, "life": 1.0, "lunar": 1.0})
        high_room.db.environmental_mana = {"elemental": 1.4}
        low_room.db.environmental_mana = {"elemental": 0.7}
        high_room.contents = [character]
        low_room.contents = [character]

        ManaService._set_attunement_state(character, 100.0, 100.0)
        character.location = high_room
        ManaService.prepare_spell(character, high_room, "elemental", 16, 1, 30)
        high_result = ManaService.cast_spell(character, "elemental", 100)

        ManaService._set_attunement_state(character, 100.0, 100.0)
        character.location = low_room
        ManaService.prepare_spell(character, low_room, "elemental", 16, 1, 30)
        low_result = ManaService.cast_spell(character, "elemental", 100)

        self.assertGreater(float(high_result.data["final_spell_power"]), float(low_result.data["final_spell_power"]))
        self.assertGreater(float(high_result.data["environmental_mana_modifier"]), float(low_result.data["environmental_mana_modifier"]))

    def test_structured_cyclic_upkeep_drains_attunement_until_collapse(self):
        caster = DummyCharacter(profession="empath")
        spell = get_spell("regenerate")
        ManaService._set_attunement_state(caster, 2.0, 100.0)

        started = SpellEffectService.apply_spell(caster, spell, 20.0, quality="strong", target=caster)
        self.assertTrue(started.success)

        first_tick = StateService.process_cyclic_effects(caster)
        second_tick = StateService.process_cyclic_effects(caster)

        self.assertEqual(len(list((first_tick.data or {}).get("processed_effects", []) or [])), 1)
        self.assertEqual(len(list((second_tick.data or {}).get("collapsed_effects", []) or [])), 1)
        self.assertEqual(((second_tick.data or {}).get("collapsed_effects", [{}])[0] or {}).get("collapse_reason"), "insufficient_mana")


if __name__ == "__main__":
    unittest.main()