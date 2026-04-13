import unittest
from unittest.mock import patch

from domain.spells.spell_definitions import get_spell
from engine.services.state_service import StateService
from engine.services.spell_contest_service import SpellContestService
from engine.services.spell_effect_service import SpellEffectService


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, hp=50, max_hp=100, key="Dummy", profession="empath", healing_modifier=1.0):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.db.hp = hp
        self.db.max_hp = max_hp
        self.db.stats = {"reflex": 10, "magic_resistance": 10}
        self.ndb.spell_debug = False
        self.ndb.spell_debug_trace = []
        self.key = key
        self.profession = profession
        self.healing_modifier = healing_modifier
        self.id = 7
        self.states = {}

    def set_hp(self, value):
        self.db.hp = max(0, min(int(value), int(self.db.max_hp or 0)))

    def is_profession(self, profession):
        return self.profession == str(profession or "").strip().lower()

    def get_profession(self):
        return self.profession

    def get_skill(self, name):
        mapping = {
            "attunement": 100,
            "arcana": 100,
            "targeted_magic": 100,
            "utility": 100,
            "warding": 100,
            "augmentation": 100,
            "primary_magic": 100,
            "evasion": 100,
        }
        return mapping.get(name, 100)

    def get_stat(self, name):
        if name in self.db.stats:
            return self.db.stats[name]
        mapping = {"intelligence": 30, "discipline": 30, "wisdom": 30, "reflex": 10}
        return mapping.get(name, 30)

    def get_empath_healing_modifier(self):
        return self.healing_modifier

    def set_state(self, key, value):
        self.states[key] = value

    def get_state(self, key):
        return self.states.get(key)

    def clear_state(self, key):
        self.states.pop(key, None)

    def get_effect_modifier(self, modifier_key, category="debilitation"):
        active_effects = dict((self.get_state("active_effects") or {}).get(category, {}) or {})
        total = 0.0
        for effect in active_effects.values():
            modifiers = dict(effect.get("modifiers") or {})
            total += float(effect.get("strength", 0) or 0) * float(modifiers.get(modifier_key, 0.0) or 0.0)
        return int(round(total))

    def award_skill_experience(self, *args, **kwargs):
        _args = args
        _kwargs = kwargs
        return None

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


class DummyRoom:
    def __init__(self, *contents):
        self.contents = []
        for obj in contents:
            if obj is not None:
                obj.location = self
                self.contents.append(obj)


class SpellEffectServiceTests(unittest.TestCase):
    def test_empath_heal_uses_final_spell_power(self):
        caster = DummyCharacter(hp=40, max_hp=100, key="Empath", profession="empath")
        spell = get_spell("empath_heal")

        low = SpellEffectService.apply_spell(caster, spell, 8.0, quality="normal")
        low_hp = caster.db.hp
        caster.db.hp = 40
        high = SpellEffectService.apply_spell(caster, spell, 40.0, quality="normal")
        high_hp = caster.db.hp

        self.assertTrue(low.success)
        self.assertTrue(high.success)
        self.assertGreater(high.data["effect_payload"]["heal_amount"], low.data["effect_payload"]["heal_amount"])
        self.assertGreater(high_hp, low_hp)

    def test_empath_heal_caps_at_missing_hp(self):
        caster = DummyCharacter(hp=98, max_hp=100, key="Empath", profession="empath")
        spell = get_spell("empath_heal")

        result = SpellEffectService.apply_spell(caster, spell, 50.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["heal_amount"], 2)
        self.assertEqual(caster.db.hp, 100)

    def test_empath_heal_can_target_another_character(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        target = DummyCharacter(hp=30, max_hp=100, key="Patient", profession="empath")
        spell = get_spell("empath_heal")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertFalse(result.data["effect_payload"]["self_target"])
        self.assertEqual(result.data["effect_payload"]["target_key"], "Patient")
        self.assertGreater(target.db.hp, 30)

    def test_cleric_minor_heal_routes_through_shared_healing_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=60, max_hp=100, key="Patient", profession="cleric")
        spell = get_spell("cleric_minor_heal")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "healing")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "healing")
        self.assertEqual(result.data["effect_payload"]["source_mana_type"], "holy")
        self.assertGreater(target.db.hp, 60)

    def test_empath_heal_respects_empath_healing_modifier(self):
        low_modifier = DummyCharacter(hp=40, max_hp=100, key="Empath", profession="empath", healing_modifier=0.5)
        full_modifier = DummyCharacter(hp=40, max_hp=100, key="Empath", profession="empath", healing_modifier=1.0)
        spell = get_spell("empath_heal")

        reduced = SpellEffectService.apply_spell(low_modifier, spell, 24.0, quality="strong")
        normal = SpellEffectService.apply_spell(full_modifier, spell, 24.0, quality="strong")

        self.assertTrue(reduced.success)
        self.assertTrue(normal.success)
        self.assertLess(reduced.data["effect_payload"]["heal_amount"], normal.data["effect_payload"]["heal_amount"])

    def test_unknown_family_returns_structured_failure(self):
        class UnknownSpell:
            id = "test_unknown"
            name = "Unknown"
            spell_type = "mystery"
            mana_type = "life"

        caster = DummyCharacter()

        result = SpellEffectService.apply_spell(caster, UnknownSpell(), 10.0)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "unknown_effect_family")

    def test_bolster_routes_through_augmentation_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("bolster")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "augmentation")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "augmentation")
        self.assertEqual(result.data["effect_payload"]["buff_name"], "bolster")
        self.assertEqual(caster.get_state("augmentation_buff")["name"], "bolster")

    def test_bolster_uses_final_spell_power_for_strength(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("bolster")

        low = SpellEffectService.apply_spell(caster, spell, 8.0, quality="normal")
        low_strength = low.data["effect_payload"]["strength"]
        high = SpellEffectService.apply_spell(caster, spell, 40.0, quality="normal")
        high_strength = high.data["effect_payload"]["strength"]

        self.assertGreater(high_strength, low_strength)

    def test_minor_barrier_routes_through_warding_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("minor_barrier")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "warding")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "warding")
        self.assertEqual(result.data["effect_payload"]["source_spell"], "minor_barrier")
        self.assertIsNotNone(caster.get_state("warding_barrier"))

    def test_minor_barrier_recast_refreshes_existing_barrier(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("minor_barrier")

        first = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal")
        first_barrier = dict(caster.get_state("warding_barrier") or {})
        second = SpellEffectService.apply_spell(caster, spell, 10.0, quality="normal")
        second_barrier = dict(caster.get_state("warding_barrier") or {})

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(second_barrier["strength"], first_barrier["strength"])
        self.assertGreaterEqual(second_barrier["duration"], first_barrier["duration"])

    def test_shared_guard_routes_through_group_warding_without_character_mutation(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        ally = DummyCharacter(hp=100, max_hp=100, key="Ally", profession="cleric")
        ally.account = object()
        room = DummyRoom(caster, ally)
        spell = get_spell("shared_guard")

        with patch("engine.services.spell_effect_service.StateService.apply_warding_effect", wraps=StateService.apply_warding_effect) as ward_mock:
            result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=room)

        self.assertTrue(result.success)
        self.assertEqual(ward_mock.call_count, 2)
        self.assertTrue(result.data["effect_payload"]["group_target"])
        self.assertEqual(result.data["effect_payload"]["target_count"], 2)
        self.assertIsNotNone(caster.get_state("warding_barrier"))
        self.assertIsNotNone(ally.get_state("warding_barrier"))

    def test_glimmer_routes_through_structured_utility_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("glimmer")

        with patch("engine.services.spell_effect_service.StateService.apply_utility_effect", wraps=StateService.apply_utility_effect) as utility_mock:
            result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(utility_mock.call_count, 1)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "light")
        self.assertIsNotNone(caster.get_state("utility_light"))

    def test_cleanse_routes_mutation_through_state_service(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        caster.set_state("exposed_magic", {"duration": 3})
        caster.set_state("active_effects", {"debilitation": {"hinder": {"duration": 3, "strength": 2}}})
        spell = get_spell("cleanse")

        with patch("engine.services.spell_effect_service.StateService.apply_cleanse", wraps=StateService.apply_cleanse) as cleanse_mock:
            result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(cleanse_mock.call_count, 1)
        self.assertTrue(result.data["effect_payload"]["removed"])
        self.assertIsNone(caster.get_state("exposed_magic"))
        self.assertEqual(dict((caster.get_state("active_effects") or {}).get("debilitation", {}) or {}), {})

    def test_flare_routes_through_targeted_magic_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "targeted_magic")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "targeted_magic")

    def test_arc_burst_routes_each_room_target_independently(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target_a = DummyCharacter(hp=100, max_hp=100, key="TargetA", profession="cleric")
        target_b = DummyCharacter(hp=100, max_hp=100, key="TargetB", profession="cleric")
        target_c = DummyCharacter(hp=100, max_hp=100, key="TargetC", profession="cleric")
        room = DummyRoom(caster, target_a, target_b, target_c)
        spell = get_spell("arc_burst")

        with patch("engine.services.spell_effect_service.SpellContestService.resolve_targeted_magic", wraps=SpellContestService.resolve_targeted_magic) as contest_mock:
            result = SpellEffectService.apply_spell(caster, spell, 36.0, quality="strong", target=room)

        self.assertTrue(result.success)
        self.assertEqual(contest_mock.call_count, 3)
        self.assertEqual(result.data["spell_type"], "aoe")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "aoe")
        self.assertEqual(len(result.data["effect_payload"]["targets"]), 3)
        self.assertEqual({entry["target_key"] for entry in result.data["effect_payload"]["targets"]}, {"TargetA", "TargetB", "TargetC"})

    def test_arc_burst_keeps_target_mutation_isolated(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        shielded = DummyCharacter(hp=100, max_hp=100, key="Shielded", profession="cleric")
        open_target = DummyCharacter(hp=100, max_hp=100, key="Open", profession="cleric")
        bystander = DummyCharacter(hp=100, max_hp=100, key="Bystander", profession="cleric")
        shielded.apply_warding_barrier(shielded, "minor_barrier", strength=200, duration=20)
        room = DummyRoom(caster, shielded, open_target, bystander)
        spell = get_spell("arc_burst")

        result = SpellEffectService.apply_spell(caster, spell, 36.0, quality="strong", target=room)

        self.assertTrue(result.success)
        payloads = {entry["target_key"]: entry for entry in result.data["effect_payload"]["targets"]}
        self.assertGreater(float(payloads["Shielded"]["absorbed"]), 0.0)
        self.assertEqual(float(payloads["Shielded"]["damage"]), 0.0)
        self.assertGreater(float(payloads["Open"]["damage"]), 0.0)
        self.assertGreater(float(payloads["Bystander"]["damage"]), 0.0)
        self.assertIsNone(open_target.get_state("warding_barrier"))
        self.assertTrue(all("contest_margin" in entry for entry in result.data["effect_payload"]["targets"]))

    def test_arc_burst_scales_down_as_target_count_rises(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        solo_target = DummyCharacter(hp=100, max_hp=100, key="Solo", profession="cleric")
        group_a = DummyCharacter(hp=100, max_hp=100, key="GroupA", profession="cleric")
        group_b = DummyCharacter(hp=100, max_hp=100, key="GroupB", profession="cleric")
        group_c = DummyCharacter(hp=100, max_hp=100, key="GroupC", profession="cleric")
        solo_room = DummyRoom(caster, solo_target)
        group_room = DummyRoom(caster, group_a, group_b, group_c)
        spell = get_spell("arc_burst")

        solo = SpellEffectService.apply_spell(caster, spell, 36.0, quality="strong", target=solo_room)
        group = SpellEffectService.apply_spell(caster, spell, 36.0, quality="strong", target=group_room)

        self.assertTrue(solo.success)
        self.assertTrue(group.success)
        self.assertGreater(float(solo.data["effect_payload"]["scaled_power"]), float(group.data["effect_payload"]["scaled_power"]))
        self.assertGreater(float(solo.data["effect_payload"]["targets"][0]["damage"]), float(group.data["effect_payload"]["targets"][0]["damage"]))

    def test_arc_burst_can_mix_hit_and_miss_per_target(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        hit_target = DummyCharacter(hp=100, max_hp=100, key="Hit", profession="cleric")
        miss_target = DummyCharacter(hp=100, max_hp=100, key="Miss", profession="cleric")
        miss_target.db.stats["reflex"] = 1000
        room = DummyRoom(caster, hit_target, miss_target)
        spell = get_spell("arc_burst")

        result = SpellEffectService.apply_spell(caster, spell, 36.0, quality="strong", target=room)

        self.assertTrue(result.success)
        payloads = {entry["target_key"]: entry for entry in result.data["effect_payload"]["targets"]}
        self.assertTrue(payloads["Hit"]["hit"])
        self.assertFalse(payloads["Miss"]["hit"])
        self.assertGreater(float(payloads["Hit"]["damage"]), 0.0)
        self.assertEqual(float(payloads["Miss"]["damage"]), 0.0)

    def test_flare_miss_returns_zero_damage_payload(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        target.db.stats["reflex"] = 1000
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 10.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertFalse(result.data["effect_payload"]["hit"])
        self.assertEqual(result.data["effect_payload"]["final_damage"], 0.0)

    def test_flare_invalid_target_fails_closed(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=None)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "invalid_target")

    def test_targeted_magic_handler_uses_contest_service_contract(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("flare")
        contest_payload = {
            "effect_family": "targeted_magic",
            "hit": True,
            "attack_score": 40.0,
            "defense_score": 20.0,
            "contest_margin": 20.0,
            "base_damage": 12.0,
            "final_damage": 8.0,
            "absorbed_by_ward": 4.0,
            "target_id": target.id,
            "target_key": target.key,
        }

        with patch("engine.services.spell_effect_service.SpellContestService.resolve_targeted_magic") as mocked:
            mocked.return_value = type("ContestResult", (), {"success": True, "data": contest_payload})()
            result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["contest_margin"], 20.0)
        self.assertEqual(result.data["effect_payload"]["absorbed_by_ward"], 4.0)

    def test_targeted_magic_trace_is_opt_in_and_structured(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        caster.ndb.spell_debug = True
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        trace = result.data["effect_payload"].get("debug_trace")
        self.assertIsInstance(trace, dict)
        self.assertEqual(trace["spell_id"], spell.id)
        self.assertIn("hit", trace)
        self.assertIn("contest_margin", trace)
        self.assertIn("base_damage", trace)
        self.assertIn("absorbed", trace)
        self.assertIn("final_damage", trace)
        self.assertEqual(caster.ndb.spell_debug_trace[-1]["spell_id"], spell.id)

    def test_targeted_magic_trace_is_omitted_when_debug_disabled(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertIsNone(result.data["effect_payload"].get("debug_trace"))
        self.assertEqual(caster.ndb.spell_debug_trace, [])

    def test_daze_routes_through_debilitation_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("daze")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "debilitation")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "debilitation")
        self.assertEqual(result.data["effect_payload"]["effect_type"], "daze")
        active_effects = target.get_state("active_effects") or {}
        self.assertIn("debilitation", active_effects)
        self.assertIn("daze", active_effects["debilitation"])

    def test_daze_miss_does_not_mutate_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        target.get_skill = lambda name: 1000 if name == "warding" else 100
        spell = get_spell("daze")

        result = SpellEffectService.apply_spell(caster, spell, 5.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertFalse(result.data["effect_payload"]["hit"])
        self.assertIsNone(target.get_state("active_effects"))

    def test_debilitation_stronger_recast_replaces_weaker(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("daze")

        first = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal", target=target)
        second = SpellEffectService.apply_spell(caster, spell, 40.0, quality="strong", target=target)

        first_effect = dict((target.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}))
        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertTrue(second.data["effect_payload"]["replaced"])
        self.assertGreaterEqual(int(second.data["effect_payload"]["strength"] or 0), int(first_effect.get("strength", 0) or 0))
        self.assertEqual(len((target.get_state("active_effects") or {}).get("debilitation", {})), 1)

    def test_debilitation_weaker_recast_is_ignored(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("daze")

        strong = SpellEffectService.apply_spell(caster, spell, 40.0, quality="strong", target=target)
        before = dict((target.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}))
        weak = SpellEffectService.apply_spell(caster, spell, 10.0, quality="weak", target=target)
        after = dict((target.get_state("active_effects") or {}).get("debilitation", {}).get("daze", {}))

        self.assertTrue(strong.success)
        self.assertTrue(weak.success)
        self.assertTrue(weak.data["effect_payload"]["ignored"])
        self.assertEqual(after["strength"], before["strength"])

    def test_debilitation_trace_is_opt_in_and_structured(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        caster.ndb.spell_debug = True
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("daze")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        trace = result.data["effect_payload"].get("debug_trace")
        self.assertIsInstance(trace, dict)
        self.assertEqual(trace["spell_id"], spell.id)
        self.assertEqual(trace["effect_type"], "daze")
        self.assertIn("contest_margin", trace)
        self.assertIn("strength", trace)
        self.assertIn("duration", trace)

    def test_daze_reduces_targeted_magic_defense_on_followup_cast(self):
        seer = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        mage = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        clean_target = DummyCharacter(hp=100, max_hp=100, key="Clean", profession="cleric")
        dazed_target = DummyCharacter(hp=100, max_hp=100, key="Dazed", profession="cleric")

        daze = get_spell("daze")
        flare = get_spell("flare")
        daze_result = SpellEffectService.apply_spell(seer, daze, 30.0, quality="strong", target=dazed_target)
        clean_result = SpellEffectService.apply_spell(mage, flare, 20.0, quality="normal", target=clean_target)
        dazed_result = SpellEffectService.apply_spell(mage, flare, 20.0, quality="normal", target=dazed_target)

        self.assertTrue(daze_result.success)
        self.assertTrue(clean_result.success)
        self.assertTrue(dazed_result.success)
        self.assertGreater(
            float(dazed_result.data["effect_payload"]["contest_margin"]),
            float(clean_result.data["effect_payload"]["contest_margin"]),
        )


if __name__ == "__main__":
    unittest.main()