import unittest

from domain.spells.spell_definitions import get_spell
from engine.services.mana_service import ManaService
from engine.services.spell_access_service import SpellAccessService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.spellbook_service import SpellbookService
from engine.services.state_service import StateService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, profession="cleric"):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.location = None
        self.pk = 1
        self.id = 1
        self.key = profession.title()
        self.profession = profession
        self.devotion = 100
        self.devotion_max = 100
        self.empath_shock = 0
        self.states = {}
        self.db.circle = 5
        self.db.hp = 100
        self.db.max_hp = 100
        self.db.stats = {"reflex": 10, "magic_resistance": 10}
        self.db.spellbook = {"known_spells": {}}

    def ensure_core_defaults(self):
        return None

    def is_profession(self, profession):
        return self.profession == str(profession or "").strip().lower()

    def get_profession(self):
        return self.profession

    def get_devotion(self):
        return self.devotion

    def get_devotion_max(self):
        return self.devotion_max

    def adjust_devotion(self, amount, sync=False):
        _sync = sync
        self.devotion = max(0, min(self.devotion_max, self.devotion + int(amount)))
        return self.devotion

    def get_empath_healing_modifier(self):
        return 1.0

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
            "primary_magic": 100,
        }
        return mapping.get(name, 100)

    def get_stat(self, name):
        if name in self.db.stats:
            return self.db.stats[name]
        mapping = {"intelligence": 30, "discipline": 30, "wisdom": 30, "reflex": 10}
        return mapping.get(name, 30)

    def set_hp(self, value):
        self.db.hp = max(0, min(int(value), int(self.db.max_hp or 0)))

    def award_skill_experience(self, *args, **kwargs):
        _args = args
        _kwargs = kwargs
        return None

    def set_state(self, key, value):
        self.states[key] = value

    def get_state(self, key):
        return self.states.get(key)

    def clear_state(self, key):
        self.states.pop(key, None)

    def adjust_empath_shock(self, amount):
        self.empath_shock += int(amount)
        return self.empath_shock

    def get_multi_skill_factor(self, primary, secondary):
        primary_skill = self.get_skill(primary)
        secondary_skill = self.get_skill(secondary)
        return min(primary_skill, secondary_skill) / max(1, max(primary_skill, secondary_skill))

    def resolve_hit_quality(self, offense, defense):
        ratio = float(offense) / max(1.0, float(defense))
        if ratio < 0.5:
            return "miss"
        if ratio < 0.8:
            return "graze"
        if ratio < 1.2:
            return "hit"
        return "strong"

    def apply_magic_resistance(self, incoming_power):
        resist = int(self.db.stats.get("magic_resistance", 10) or 10)
        return max(1.0, float(incoming_power) * (100.0 / (100.0 + resist)))

    def apply_ward_absorption(self, target, damage):
        ward = target.get_state("warding_barrier")
        if not ward:
            return damage
        absorbed = min(max(0, int(damage)), int(ward.get("strength", 0) or 0))
        remaining = max(0, int(damage) - absorbed)
        updated = dict(ward)
        updated["strength"] = max(0, int(updated.get("strength", 0) or 0) - absorbed)
        if updated["strength"] <= 0:
            target.clear_state("warding_barrier")
        else:
            target.set_state("warding_barrier", updated)
        return remaining

    def apply_warding_barrier(self, target, name, strength, duration):
        existing = target.get_state("warding_barrier")
        if existing and int(existing.get("strength", 0) or 0) > strength and existing.get("name") != name:
            refreshed = dict(existing)
            refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
            target.set_state("warding_barrier", refreshed)
            return True
        if existing and existing.get("name") == name:
            refreshed = dict(existing)
            refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), duration)
            refreshed["strength"] = max(int(refreshed.get("strength", 0) or 0), strength)
            target.set_state("warding_barrier", refreshed)
            return True
        target.set_state("warding_barrier", {"name": name, "strength": strength, "duration": duration})
        return True

    def get_effect_modifier(self, modifier_key, category="debilitation"):
        active_effects = dict((self.get_state("active_effects") or {}).get(category, {}) or {})
        total = 0.0
        for effect in active_effects.values():
            modifiers = dict(effect.get("modifiers") or {})
            total += float(effect.get("strength", 0) or 0) * float(modifiers.get(modifier_key, 0.0) or 0.0)
        return int(round(total))


class DummyRoom:
    def __init__(self, mana=None):
        self.db = DummyHolder()
        self.db.mana = dict(mana or {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0})


class StructuredSpellPipelineTests(unittest.TestCase):
    def test_cleric_minor_heal_prepare_cast_and_apply_changes_target_hp(self):
        cleric = DummyCharacter(profession="cleric")
        patient = DummyCharacter(profession="cleric")
        patient.db.hp = 70
        room = DummyRoom()
        spell = get_spell("cleric_minor_heal")

        learned = SpellbookService.learn_spell(cleric, spell.id, "book")
        access = SpellAccessService.can_use_spell(cleric, spell)
        ManaService._set_attunement_state(cleric, 100.0, 100.0)
        prepared = ManaService.prepare_spell(cleric, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(cleric, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(cleric, spell, cast.data["final_spell_power"], quality="strong", target=patient)

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        self.assertGreater(patient.db.hp, 70)
        self.assertEqual(effect.data["effect_payload"]["effect_family"], "healing")
        self.assertEqual(effect.data["spell_id"], "cleric_minor_heal")

    def test_bolster_prepare_cast_and_apply_sets_augmentation_state(self):
        mage = DummyCharacter(profession="warrior_mage")
        room = DummyRoom()
        spell = get_spell("bolster")

        learned = SpellbookService.learn_spell(mage, spell.id, "npc")
        access = SpellAccessService.can_use_spell(mage, spell)
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        prepared = ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="strong")

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        self.assertEqual(effect.data["effect_payload"]["effect_family"], "augmentation")
        self.assertIsNotNone(mage.get_state("augmentation_buff"))
        self.assertEqual(mage.get_state("augmentation_buff")["name"], "bolster")

    def test_minor_barrier_prepare_cast_and_apply_sets_barrier_state(self):
        cleric = DummyCharacter(profession="cleric")
        room = DummyRoom()
        spell = get_spell("minor_barrier")

        learned = SpellbookService.learn_spell(cleric, spell.id, "book")
        access = SpellAccessService.can_use_spell(cleric, spell)
        ManaService._set_attunement_state(cleric, 100.0, 100.0)
        prepared = ManaService.prepare_spell(cleric, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(cleric, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(cleric, spell, cast.data["final_spell_power"], quality="strong")

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        self.assertEqual(effect.data["effect_payload"]["effect_family"], "warding")
        self.assertIsNotNone(cleric.get_state("warding_barrier"))
        self.assertEqual(cleric.get_state("warding_barrier")["name"], "minor_barrier")

    def test_flare_prepare_cast_and_apply_hit_changes_target_hp(self):
        mage = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        room = DummyRoom()
        spell = get_spell("flare")

        learned = SpellbookService.learn_spell(mage, spell.id, "npc")
        access = SpellAccessService.can_use_spell(mage, spell)
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        prepared = ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        before_hp = target.db.hp
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        self.assertTrue(effect.data["effect_payload"]["hit"])
        self.assertLess(target.db.hp, before_hp)

    def test_flare_prepare_cast_and_apply_miss_does_not_change_hp(self):
        mage = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        target.db.stats["reflex"] = 1000
        room = DummyRoom()
        spell = get_spell("flare")

        SpellbookService.learn_spell(mage, spell.id, "npc")
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        before_hp = target.db.hp
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="normal", target=target)

        self.assertTrue(effect.success)
        self.assertFalse(effect.data["effect_payload"]["hit"])
        self.assertEqual(target.db.hp, before_hp)

    def test_flare_hits_warded_target_and_barrier_absorbs_part(self):
        mage = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        target.apply_warding_barrier(target, "minor_barrier", strength=8, duration=20)
        room = DummyRoom()
        spell = get_spell("flare")

        SpellbookService.learn_spell(mage, spell.id, "npc")
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        before_hp = target.db.hp
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(effect.success)
        self.assertTrue(effect.data["effect_payload"]["hit"])
        self.assertGreater(effect.data["effect_payload"]["absorbed_by_ward"], 0.0)
        self.assertLess(target.db.hp, before_hp)

    def test_flare_full_absorb_changes_hp_once_or_not_at_all(self):
        mage = DummyCharacter(profession="warrior_mage")
        target = DummyCharacter(profession="cleric")
        target.apply_warding_barrier(target, "minor_barrier", strength=200, duration=20)
        room = DummyRoom()
        spell = get_spell("flare")

        SpellbookService.learn_spell(mage, spell.id, "npc")
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        before_hp = target.db.hp
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(effect.success)
        self.assertTrue(effect.data["effect_payload"]["hit"])
        self.assertEqual(effect.data["effect_payload"]["final_damage"], 0.0)
        self.assertEqual(target.db.hp, before_hp)

    def test_daze_prepare_cast_apply_tick_and_expire(self):
        mage = DummyCharacter(profession="moon_mage")
        target = DummyCharacter(profession="cleric")
        room = DummyRoom()
        spell = get_spell("daze")

        learned = SpellbookService.learn_spell(mage, spell.id, "book")
        access = SpellAccessService.can_use_spell(mage, spell)
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        prepared = ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(mage, spell, cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        active_effects = target.get_state("active_effects") or {}
        self.assertIn("daze", active_effects.get("debilitation", {}))

        duration = int(effect.data["effect_payload"]["duration"] or 0)
        for _ in range(duration):
            StateService.tick_active_effects(target)

        self.assertNotIn("daze", dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {}))

    def test_slow_prepare_cast_apply_reuses_debilitation_handler(self):
        cleric = DummyCharacter(profession="cleric")
        target = DummyCharacter(profession="moon_mage")
        room = DummyRoom()
        spell = get_spell("slow")

        learned = SpellbookService.learn_spell(cleric, spell.id, "book")
        access = SpellAccessService.can_use_spell(cleric, spell)
        ManaService._set_attunement_state(cleric, 100.0, 100.0)
        prepared = ManaService.prepare_spell(cleric, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(cleric, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(cleric, spell, cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(learned.success)
        self.assertTrue(access.success)
        self.assertTrue(prepared.success)
        self.assertTrue(cast.success)
        self.assertTrue(effect.success)
        self.assertEqual(effect.data["effect_payload"]["effect_family"], "debilitation")
        self.assertEqual(effect.data["effect_payload"]["effect_type"], "slow")
        self.assertIn("slow", (target.get_state("active_effects") or {}).get("debilitation", {}))

    def test_daze_and_slow_coexist_without_overwriting_each_other(self):
        moon_mage = DummyCharacter(profession="moon_mage")
        cleric = DummyCharacter(profession="cleric")
        target = DummyCharacter(profession="warrior_mage")
        room = DummyRoom()
        daze = get_spell("daze")
        slow = get_spell("slow")

        SpellbookService.learn_spell(moon_mage, daze.id, "book")
        SpellbookService.learn_spell(cleric, slow.id, "book")
        ManaService._set_attunement_state(moon_mage, 100.0, 100.0)
        ManaService._set_attunement_state(cleric, 100.0, 100.0)
        ManaService.prepare_spell(moon_mage, room, daze.mana_type, daze.base_difficulty, daze.safe_mana, 30)
        ManaService.prepare_spell(cleric, room, slow.mana_type, slow.base_difficulty, slow.safe_mana, 30)
        daze_cast = ManaService.cast_spell(moon_mage, daze.mana_type, daze.base_difficulty)
        slow_cast = ManaService.cast_spell(cleric, slow.mana_type, slow.base_difficulty)
        daze_effect = SpellEffectService.apply_spell(moon_mage, daze, daze_cast.data["final_spell_power"], quality="strong", target=target)
        slow_effect = SpellEffectService.apply_spell(cleric, slow, slow_cast.data["final_spell_power"], quality="strong", target=target)

        self.assertTrue(daze_effect.success)
        self.assertTrue(slow_effect.success)
        debilitation_effects = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertIn("daze", debilitation_effects)
        self.assertIn("slow", debilitation_effects)

    def test_daze_miss_does_not_mutate_state(self):
        mage = DummyCharacter(profession="moon_mage")
        target = DummyCharacter(profession="cleric")
        target.get_skill = lambda name: 1000 if name == "warding" else 100
        room = DummyRoom()
        spell = get_spell("daze")

        SpellbookService.learn_spell(mage, spell.id, "book")
        ManaService._set_attunement_state(mage, 100.0, 100.0)
        ManaService.prepare_spell(mage, room, spell.mana_type, spell.base_difficulty, spell.safe_mana, 30)
        cast = ManaService.cast_spell(mage, spell.mana_type, spell.base_difficulty)
        effect = SpellEffectService.apply_spell(mage, spell, 1.0, quality="weak", target=target)

        self.assertTrue(effect.success)
        self.assertFalse(effect.data["effect_payload"]["hit"])
        self.assertIsNone(target.get_state("active_effects"))


if __name__ == "__main__":
    unittest.main()