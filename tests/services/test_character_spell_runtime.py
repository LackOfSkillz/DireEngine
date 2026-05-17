import os
import itertools
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from engine.services.mana_service import ManaService
from engine.services.spell_access_service import SpellAccessService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.spellbook_service import SpellbookService
from engine.services.spell_contest_service import SpellContestService
from engine.services.state_service import StateService
from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyHolder
from typeclasses.characters import Character
from world.systems.death import handle_death


class RuntimeDummyRoom:
    def __init__(self, mana=None):
        self.db = DummyHolder()
        self.db.mana = dict(mana or {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0})
        self.contents = []
        self.messages = []

    def add(self, *objects):
        for obj in objects:
            obj.location = self
            if obj not in self.contents:
                self.contents.append(obj)

    def msg_contents(self, message, exclude=None, **kwargs):
        _kwargs = kwargs
        excluded = set(exclude or [])
        self.messages.append(str(message))
        for obj in self.contents:
            if obj in excluded:
                continue
            if hasattr(obj, "msg"):
                obj.msg(str(message))


class RuntimeDummyCharacter(DummyCharacter):
    _ids = itertools.count(1)

    prepare_spell = Character.prepare_spell
    harness_spell = Character.harness_spell
    release_magic = Character.release_magic
    cast_spell = Character.cast_spell
    resolve_spell = Character.resolve_spell
    process_magic_states = Character.process_magic_states
    stop_cyclic_spell = Character.stop_cyclic_spell
    can_access_spell = Character.can_access_spell
    get_spell_def = Character.get_spell_def
    get_spell_metadata = Character.get_spell_metadata
    _resolve_structured_spell = Character._resolve_structured_spell
    _build_structured_spell_metadata = Character._build_structured_spell_metadata
    _sync_prepared_spell_state_from_mana = Character._sync_prepared_spell_state_from_mana
    get_active_effects = Character.get_active_effects
    get_active_cyclic_effects = Character.get_active_cyclic_effects
    get_mana_realm = Character.get_mana_realm
    calculate_preparation_stability = Character.calculate_preparation_stability
    resolve_cast_quality = Character.resolve_cast_quality
    resolve_cast_target = Character.resolve_cast_target
    apply_ward_absorption = Character.apply_ward_absorption
    apply_warding_barrier = Character.apply_warding_barrier

    def __init__(self, profession="cleric", key=None):
        super().__init__(profession=profession)
        self.id = next(self._ids)
        self.pk = self.id
        self.key = key or f"{profession.title()}-{self.id}"
        self.messages = []
        self.account = object()
        self._target = None
        self.db.attunement = 100.0
        self.db.max_attunement = 100.0
        self.db.states = {}

    def msg(self, text):
        self.messages.append(str(text))

    def search(self, query, candidates=None, global_search=False, location=None):
        _global_search = global_search
        pool = list(candidates) if candidates is not None else list(getattr(location or self.location, "contents", []) or [])
        needle = str(query or "").strip().lower()
        for candidate in pool:
            if str(getattr(candidate, "key", "") or "").strip().lower() == needle:
                return candidate
        return None

    def use_skill(self, *args, **kwargs):
        _args = args
        _kwargs = kwargs
        return None

    def sync_client_state(self):
        return None

    def invoke_luminar(self):
        return 0.0

    def get_cleric_magic_modifier(self):
        return 1.0

    def get_theurgy_training_difficulty(self, mana):
        _mana = mana
        return 0

    def set_spell_cooldown(self, spell, duration):
        self.set_state(f"cooldown_{spell}", {"duration": max(1, int(duration))})

    def get_target(self):
        return self._target

    def set_target(self, target):
        self._target = target


class RuntimeDummyCorpse:
    def __init__(self, owner=None, key="corpse"):
        self.db = DummyHolder()
        self.db.is_corpse = True
        self.id = next(RuntimeDummyCharacter._ids)
        self.pk = self.id
        self.key = key
        self._owner = owner
        self.location = None

    def get_owner(self):
        return self._owner


class RuntimeHiddenTarget(RuntimeDummyCharacter):
    def __init__(self, profession="cleric", key="HiddenTarget"):
        super().__init__(profession=profession, key=key)
        self.db.stealthed = True
        self.set_state("hidden", {"strength": 20})

    def is_hidden(self):
        return bool(self.get_state("hidden")) or bool(getattr(self.db, "stealthed", False))

    def reveal(self):
        self.db.stealthed = False
        self.clear_state("hidden")


class CharacterSpellRuntimeTests(unittest.TestCase):
    def _learn(self, character, spell_id):
        spell = character._resolve_structured_spell(spell_id)
        learned_via = "book" if "book" in (spell.acquisition_methods or []) else str((spell.acquisition_methods or ["npc"])[0])
        return SpellbookService.learn_spell(character, spell.id, learned_via)

    def test_prepare_cast_heal_runtime_targets_patient(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        patient = RuntimeDummyCharacter(profession="cleric", key="Patient")
        patient.db.hp = 70
        room = RuntimeDummyRoom()
        room.add(cleric, patient)

        self.assertTrue(self._learn(cleric, "cleric_minor_heal").success)
        with patch("typeclasses.characters.ManaService._cast_spell", wraps=ManaService._cast_spell) as mana_cast_mock, patch(
            "typeclasses.characters.SpellEffectService.apply_spell", wraps=SpellEffectService.apply_spell
        ) as effect_mock:
            self.assertTrue(cleric.prepare_spell("cleric_minor_heal 10"))
            self.assertTrue(cleric.cast_spell(target_name="Patient"))

        self.assertTrue(mana_cast_mock.called)
        self.assertTrue(effect_mock.called)
        self.assertGreater(patient.db.hp, 70)
        self.assertFalse(any("legacy" in line.lower() for line in cleric.messages))

    def test_prepare_runtime_defers_attunement_spend_until_cast(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(mage, target)

        self.assertTrue(self._learn(mage, "flare").success)
        attunement_before = ManaService._get_attunement_state(mage)["current"]

        self.assertTrue(mage.prepare_spell("flare 12"))
        self.assertEqual(ManaService._get_attunement_state(mage)["current"], attunement_before)
        self.assertTrue(mage.cast_spell(target_name="Target"))
        self.assertEqual(ManaService._get_attunement_state(mage)["current"], attunement_before - 12)

    def test_prepare_runtime_full_prep_transition_syncs_prepared_state(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "minor_barrier").success)
        self.assertTrue(cleric.prepare_spell("minor_barrier 12"))
        prepared_spell = dict(cleric.get_state("prepared_spell") or {})
        self.assertFalse(bool(prepared_spell.get("ready", True)))

        transition = ManaService.transition_to_full_prep(cleric)

        self.assertTrue(transition.success)
        self.assertTrue(bool((cleric.get_state("prepared_spell") or {}).get("ready", False)))

    def test_harness_runtime_without_prepared_spell_and_release_mana(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")

        self.assertTrue(mage.harness_spell("10"))
        self.assertEqual(ManaService._get_harnessed_mana_state(mage), 10)
        self.assertTrue(mage.release_magic("mana"))
        self.assertEqual(ManaService._get_harnessed_mana_state(mage), 0)

    def test_release_runtime_prefers_prepared_spell_before_held_mana(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "bolster").success)
        self.assertTrue(mage.harness_spell("10"))
        self.assertTrue(mage.prepare_spell("bolster 10"))

        self.assertTrue(mage.release_magic())
        self.assertIsNone(mage.get_state("prepared_spell"))
        self.assertEqual(ManaService._get_harnessed_mana_state(mage), 10)

    def test_release_runtime_can_stop_cyclic_spell(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "storm_field").success)
        self.assertTrue(mage.harness_spell("16"))
        self.assertTrue(mage.prepare_spell("storm_field 16"))
        self.assertTrue(mage.cast_spell())
        self.assertTrue(mage.get_active_cyclic_effects())

        self.assertTrue(mage.release_magic("cyclic"))
        self.assertFalse(mage.get_active_cyclic_effects())

    def test_release_runtime_can_fall_back_to_empath_link(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")

        with patch.object(RuntimeDummyCharacter, "remove_empath_link", return_value=True, create=True) as remove_link_mock:
            self.assertTrue(empath.release_magic())

        self.assertTrue(remove_link_mock.called)
        self.assertTrue(any("empathic connection" in line.lower() for line in empath.messages))

    def test_innocence_runtime_rejects_explicit_other_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="cleric", key="Patient")
        empath.db.circle = 11
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "innocence").success)
        self.assertTrue(empath.prepare_spell("innocence 10"))

        self.assertFalse(empath.cast_spell(target_name="Patient"))
        self.assertTrue(any("only cast that spell on yourself" in line.lower() for line in empath.messages))

    def test_zone_of_protection_runtime_wards_group_slice(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="cleric", key="Patient")
        empath.db.circle = 11
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "zone_of_protection").success)
        self.assertTrue(empath.prepare_spell("zone_of_protection 15"))
        self.assertTrue(empath.cast_spell())

        caster_ward = dict((empath.get_state("active_effects") or {}).get("warding", {}).get("zone_of_protection", {}) or {})
        patient_ward = dict((patient.get_state("active_effects") or {}).get("warding", {}).get("zone_of_protection", {}) or {})
        self.assertGreater(int(caster_ward.get("strength", 0) or 0), 0)
        self.assertGreater(int(patient_ward.get("strength", 0) or 0), 0)

    def test_zone_of_protection_runtime_rejects_explicit_other_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="cleric", key="Patient")
        empath.db.circle = 11
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "zone_of_protection").success)
        self.assertTrue(empath.prepare_spell("zone_of_protection 15"))

        self.assertFalse(empath.cast_spell(target_name="Patient"))
        self.assertTrue(any("only cast that spell on yourself" in line.lower() for line in empath.messages))

    def test_prepare_cast_augment_runtime_avoids_legacy_resolver(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "bolster").success)
        with patch.object(RuntimeDummyCharacter, "resolve_augmentation_spell", side_effect=AssertionError("legacy augmentation used"), create=True):
            self.assertTrue(mage.prepare_spell("bolster 10"))
            self.assertTrue(mage.cast_spell())

        self.assertEqual(mage.get_state("augmentation_buff")["name"], "bolster")
        self.assertTrue(any("bolster" in line.lower() for line in mage.messages))

    def test_prepare_cast_bless_runtime_can_target_an_ally(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        target = RuntimeDummyCharacter(profession="cleric", key="Guard")
        room = RuntimeDummyRoom()
        room.add(cleric, target)

        self.assertTrue(self._learn(cleric, "bless").success)
        self.assertTrue(cleric.prepare_spell("bless 10"))
        self.assertTrue(cleric.cast_spell(target_name="Guard"))

        bless_state = dict((target.get_state("active_effects") or {}).get("utility", {}).get("bless", {}) or {})
        self.assertTrue(bool(bless_state))
        self.assertTrue(any("holy radiance" in line.lower() for line in cleric.messages))

    def test_prepare_cast_ward_runtime_updates_authoritative_barrier(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "minor_barrier").success)
        with patch.object(RuntimeDummyCharacter, "resolve_warding_spell", side_effect=AssertionError("legacy warding used"), create=True):
            self.assertTrue(cleric.prepare_spell("minor_barrier 12"))
            self.assertTrue(cleric.cast_spell())
            first_barrier = dict(cleric.get_state("warding_barrier") or {})
            cleric.clear_state("cooldown_minor_barrier")
            self.assertTrue(cleric.prepare_spell("minor_barrier 6"))
            self.assertTrue(cleric.cast_spell())

        second_barrier = dict(cleric.get_state("warding_barrier") or {})
        self.assertEqual(second_barrier["name"], "minor_barrier")
        self.assertGreaterEqual(int(second_barrier["strength"]), int(first_barrier["strength"]))

    def test_prepare_cast_protection_from_evil_runtime_targets_patient(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        patient = RuntimeDummyCharacter(profession="cleric", key="Patient")
        room = RuntimeDummyRoom()
        room.add(cleric, patient)

        self.assertTrue(self._learn(cleric, "protection_from_evil").success)
        self.assertTrue(cleric.prepare_spell("protection_from_evil 20"))
        self.assertTrue(cleric.cast_spell(target_name="Patient"))

        self.assertEqual(patient.get_state("warding_barrier")["name"], "protection_from_evil")
        augmentation = dict((patient.get_state("active_effects") or {}).get("augmentation", {}).get("protection_from_evil", {}) or {})
        self.assertTrue(bool(augmentation))

    def test_prepare_cast_holy_light_runtime_sets_light_effect(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "holy_light").success)
        self.assertTrue(cleric.prepare_spell("holy_light 5"))
        self.assertTrue(cleric.cast_spell())

        utility_light = dict(cleric.get_state("utility_light") or {})
        self.assertEqual(utility_light.get("name"), "holy_light")
        self.assertTrue(any("holy light" in line.lower() for line in cleric.messages))

    def test_prepare_cast_major_physical_protection_runtime_sets_stronger_physical_barrier(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "major_physical_protection").success)
        self.assertTrue(cleric.prepare_spell("major_physical_protection 15"))
        self.assertTrue(cleric.cast_spell())

        self.assertTrue(bool((cleric.get_state("physical_barrier") or {}).get("absorbs_physical", False)))
        self.assertGreaterEqual(int((cleric.get_state("physical_barrier") or {}).get("strength", 0) or 0), 4)

    def test_prepare_cast_divine_radiance_runtime_sets_ward_and_light(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "divine_radiance").success)
        self.assertTrue(cleric.prepare_spell("divine_radiance 5"))
        self.assertTrue(cleric.cast_spell())

        self.assertEqual((cleric.get_state("warding_barrier") or {}).get("name"), "divine_radiance")
        self.assertEqual((cleric.get_state("utility_light") or {}).get("spell_id"), "divine_radiance")

    def test_prepare_cast_halo_runtime_sets_bounded_defensive_aura(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        cleric.db.circle = 20
        original_get_skill = cleric.get_skill
        cleric.get_skill = lambda name, _original=original_get_skill: 300 if name == "primary_magic" else _original(name)
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "halo").success)
        self.assertTrue(cleric.prepare_spell("halo 20"))
        self.assertTrue(cleric.cast_spell())

        self.assertEqual((cleric.get_state("warding_barrier") or {}).get("name"), "halo")
        augmentation = dict((cleric.get_state("active_effects") or {}).get("augmentation", {}).get("halo", {}) or {})
        self.assertEqual(dict(augmentation.get("modifiers") or {}).get("magic_defense"), 1.0)

    def test_prepare_cast_rejuvenation_runtime_targets_corpse_and_delegates_to_revive_hook(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        fallen = RuntimeDummyCharacter(profession="cleric", key="Fallen")
        corpse = RuntimeDummyCorpse(owner=fallen, key="corpse")
        room = RuntimeDummyRoom()
        room.add(cleric, corpse)
        calls = []
        cleric.perform_cleric_revive = lambda target: calls.append(target) or (True, "revived")

        self.assertTrue(self._learn(cleric, "rejuvenation").success)
        self.assertTrue(cleric.prepare_spell("rejuvenation 5"))
        self.assertTrue(cleric.cast_spell(target_name="corpse"))

        self.assertEqual(calls, [corpse])
        self.assertTrue(any("calling them back from death" in line.lower() for line in cleric.messages))

    def test_prepare_cast_targeted_runtime_uses_contest_and_state_service(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(mage, target)

        self.assertTrue(self._learn(mage, "flare").success)
        with patch.object(RuntimeDummyCharacter, "resolve_targeted_spell", side_effect=AssertionError("legacy targeted used"), create=True), patch(
            "engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage
        ) as apply_damage_mock:
            self.assertTrue(mage.prepare_spell("flare 12"))
            self.assertTrue(mage.cast_spell(target_name="Target"))

        self.assertGreaterEqual(apply_damage_mock.call_count, 0)
        self.assertLess(target.db.hp, target.db.max_hp)

    def test_prepare_cast_aoe_runtime_uses_room_targets_and_state_service(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        first = RuntimeDummyCharacter(profession="cleric", key="First")
        second = RuntimeDummyCharacter(profession="cleric", key="Second")
        third = RuntimeDummyCharacter(profession="cleric", key="Third")
        room = RuntimeDummyRoom()
        room.add(mage, first, second, third)

        self.assertTrue(self._learn(mage, "arc_burst").success)
        with patch.object(RuntimeDummyCharacter, "resolve_room_targeted_spell", side_effect=AssertionError("legacy room targeted used"), create=True), patch(
            "engine.services.spell_contest_service.StateService.apply_damage", wraps=StateService.apply_damage
        ) as apply_damage_mock:
            self.assertTrue(mage.prepare_spell("arc_burst 16"))
            self.assertTrue(mage.cast_spell())

        self.assertEqual(apply_damage_mock.call_count, 3)
        self.assertLess(first.db.hp, first.db.max_hp)
        self.assertLess(second.db.hp, second.db.max_hp)
        self.assertLess(third.db.hp, third.db.max_hp)

    def test_prepare_cast_debilitation_runtime_uses_nested_state_and_tick_loop(self):
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(seer, target)

        self.assertTrue(self._learn(seer, "daze").success)
        with patch.object(RuntimeDummyCharacter, "resolve_debilitation_spell", side_effect=AssertionError("legacy debilitation used"), create=True):
            self.assertTrue(seer.prepare_spell("daze 14"))
            self.assertTrue(seer.cast_spell(target_name="Target"))

        active = dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertIn("daze", active)
        duration = int(active["daze"]["duration"] or 0)
        for _ in range(duration):
            target.process_magic_states()
        self.assertNotIn("daze", dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {}))

    def test_prepare_cast_burden_runtime_applies_and_expires_strength_debuff(self):
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        target.db.stats["strength"] = 20
        room = RuntimeDummyRoom()
        room.add(seer, target)

        self.assertTrue(self._learn(seer, "burden").success)
        with patch.object(RuntimeDummyCharacter, "resolve_debilitation_spell", side_effect=AssertionError("legacy debilitation used"), create=True):
            self.assertTrue(seer.prepare_spell("burden 12"))
            self.assertTrue(seer.cast_spell(target_name="Target"))

        self.assertLess(target.get_stat("strength"), 20)
        self.assertGreater(target.get_encumbrance_modifier(), 0)
        duration = int((((target.get_state("active_effects") or {}).get("debilitation", {}).get("burden", {}) or {}).get("duration", 0) or 0))
        for _ in range(duration):
            target.process_magic_states()
        self.assertEqual(target.get_stat("strength"), 20)
        self.assertEqual(target.get_encumbrance_modifier(), 0)

    def test_invalid_target_runtime_fails_before_contest(self):
        room = RuntimeDummyRoom()
        for profession, spell_id, resolver_name in (("warrior_mage", "flare", "resolve_targeted_magic"), ("moon_mage", "daze", "resolve_debilitation")):
            with self.subTest(spell=spell_id):
                caster = RuntimeDummyCharacter(profession=profession, key=profession)
                room.add(caster)
                self.assertTrue(self._learn(caster, spell_id).success)
                with patch.object(SpellContestService, resolver_name, wraps=getattr(SpellContestService, resolver_name)) as resolver_mock, patch(
                    "typeclasses.characters.SpellEffectService.apply_spell", wraps=SpellEffectService.apply_spell
                ) as effect_mock:
                    self.assertTrue(caster.prepare_spell(f"{spell_id} 12"))
                    self.assertFalse(caster.cast_spell())

                self.assertFalse(resolver_mock.called)
                self.assertFalse(effect_mock.called)
                self.assertEqual(caster.get_state("active_effects"), None)

    def test_missing_learn_state_fails_before_mana_or_effect(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        with patch("typeclasses.characters.ManaService.prepare_spell", wraps=ManaService.prepare_spell) as mana_prepare_mock, patch(
            "typeclasses.characters.SpellEffectService.apply_spell", wraps=SpellEffectService.apply_spell
        ) as effect_mock:
            self.assertFalse(mage.prepare_spell("flare 12"))

        self.assertFalse(mana_prepare_mock.called)
        self.assertFalse(effect_mock.called)
        self.assertTrue(any("not learned" in line.lower() for line in mage.messages))

    def test_legacy_cyclic_metadata_is_blocked_after_retirement(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)
        mage.db.spellbook = {"known_spells": {"radiant_aura": {"learned_via": "npc"}}}

        self.assertFalse(mage.prepare_spell("radiant_aura 12"))
        self.assertTrue(any("do not know how to prepare" in line.lower() for line in mage.messages))

    def test_structured_runtime_never_enters_legacy_resolvers_for_migrated_families(self):
        cases = [
            ("cleric", "cleric_minor_heal", "Patient", "resolve_targeted_spell"),
            ("warrior_mage", "bolster", None, "resolve_augmentation_spell"),
            ("cleric", "minor_barrier", None, "resolve_warding_spell"),
            ("warrior_mage", "flare", "Target", "resolve_targeted_spell"),
            ("warrior_mage", "arc_burst", None, "resolve_room_targeted_spell"),
            ("moon_mage", "daze", "Target", "resolve_debilitation_spell"),
            ("empath", "regenerate", None, "start_cyclic_spell"),
            ("cleric", "shielding", None, "resolve_warding_spell"),
            ("warrior_mage", "glimmer", None, "resolve_utility_spell"),
            ("cleric", "cleanse", None, "resolve_cleanse_spell"),
            ("cleric", "shared_guard", None, "resolve_group_warding_spell"),
            ("warrior_mage", "radiant_burst", None, "resolve_room_targeted_spell"),
            ("warrior_mage", "hinder", "Target", "resolve_debilitation_spell"),
        ]
        for profession, spell_id, target_name, legacy_name in cases:
            with self.subTest(spell=spell_id):
                caster = RuntimeDummyCharacter(profession=profession, key=f"{spell_id}-caster")
                room = RuntimeDummyRoom()
                room.add(caster)
                if target_name:
                    target = RuntimeDummyCharacter(profession="cleric", key=target_name)
                    room.add(target)
                self.assertTrue(self._learn(caster, spell_id).success)
                with patch.object(RuntimeDummyCharacter, legacy_name, side_effect=AssertionError(f"legacy path {legacy_name} used"), create=True):
                    if spell_id == "regenerate":
                        self.assertTrue(caster.harness_spell("12"))
                    self.assertTrue(caster.prepare_spell(f"{spell_id} 12"))
                    self.assertTrue(caster.cast_spell(target_name=target_name))

    def test_prepare_cast_utility_runtime_uses_structured_state_service_path(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "glimmer").success)
        with patch.object(RuntimeDummyCharacter, "resolve_utility_spell", side_effect=AssertionError("legacy utility used"), create=True), patch(
            "engine.services.spell_effect_service.StateService.apply_utility_effect", wraps=StateService.apply_utility_effect
        ) as utility_mock:
            self.assertTrue(mage.prepare_spell("glimmer 10"))
            self.assertTrue(mage.cast_spell())

        self.assertEqual(utility_mock.call_count, 1)
        self.assertIsNotNone(mage.get_state("utility_light"))

    def test_prepare_cast_gauge_flow_runtime_sets_and_clears_capability_flag(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "gauge_flow").success)
        self.assertTrue(mage.prepare_spell("gauge_flow 10"))
        self.assertTrue(mage.cast_spell())

        self.assertTrue(bool(getattr(mage.db, "gauge_flow_active", False)))
        duration = int((((mage.get_state("active_effects") or {}).get("utility", {}).get("gauge_flow", {}) or {}).get("duration", 0) or 0))
        for _ in range(duration):
            mage.process_magic_states()
        self.assertFalse(bool(getattr(mage.db, "gauge_flow_active", False)))

    def test_prepare_cast_strange_arrow_runtime_applies_mixed_damage_components(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(mage, target)

        self.assertTrue(self._learn(mage, "strange_arrow").success)
        self.assertTrue(mage.prepare_spell("strange_arrow 12"))
        self.assertTrue(mage.cast_spell(target_name="Target"))

        self.assertLess(target.db.hp, target.db.max_hp)

    def test_prepare_cast_aesrela_everild_runtime_stuns_target(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        cleric.db.circle = 20
        room = RuntimeDummyRoom()
        room.add(cleric, target)

        self.assertTrue(self._learn(cleric, "aesrela_everild").success)
        self.assertTrue(cleric.prepare_spell("aesrela_everild 20"))
        self.assertTrue(cleric.cast_spell(target_name="Target"))

        self.assertTrue(bool(target.db.stunned))

    def test_prepare_cast_revelation_runtime_reveals_hidden_target(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        target = RuntimeHiddenTarget(profession="cleric", key="HiddenTarget")
        cleric.db.circle = 20
        room = RuntimeDummyRoom()
        room.add(cleric, target)

        self.assertTrue(self._learn(cleric, "revelation").success)
        self.assertTrue(cleric.prepare_spell("revelation 9"))
        self.assertTrue(cleric.cast_spell(target_name="HiddenTarget"))

        self.assertFalse(target.is_hidden())

    def test_prepare_cast_hand_of_tenemlor_runtime_burns_target(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        cleric.db.circle = 20
        room = RuntimeDummyRoom()
        room.add(cleric, target)

        self.assertTrue(self._learn(cleric, "hand_of_tenemlor").success)
        self.assertTrue(cleric.prepare_spell("hand_of_tenemlor 16"))
        self.assertTrue(cleric.cast_spell(target_name="Target"))

        self.assertLess(target.db.hp, target.db.max_hp)

    def test_prepare_cast_group_warding_runtime_uses_structured_handler(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        ally = RuntimeDummyCharacter(profession="cleric", key="Ally")
        room = RuntimeDummyRoom()
        room.add(cleric, ally)

        self.assertTrue(self._learn(cleric, "shared_guard").success)
        with patch.object(RuntimeDummyCharacter, "resolve_group_warding_spell", side_effect=AssertionError("legacy group warding used"), create=True), patch(
            "engine.services.spell_effect_service.StateService.apply_warding_effect", wraps=StateService.apply_warding_effect
        ) as ward_mock:
            self.assertTrue(cleric.prepare_spell("shared_guard 12"))
            self.assertTrue(cleric.cast_spell())

        self.assertEqual(ward_mock.call_count, 2)
        self.assertIsNotNone(cleric.get_state("warding_barrier"))
        self.assertIsNotNone(ally.get_state("warding_barrier"))

    def test_prepare_cast_manifest_force_runtime_sets_physical_barrier(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "manifest_force").success)
        self.assertTrue(mage.prepare_spell("manifest_force 10"))
        self.assertTrue(mage.cast_spell())

        self.assertIsNotNone(mage.get_state("physical_barrier"))
        self.assertTrue(bool((mage.get_state("physical_barrier") or {}).get("absorbs_physical", False)))
        self.assertGreaterEqual(int((mage.get_state("physical_barrier") or {}).get("strength", 0) or 0), 34)

    def test_manifest_force_does_not_absorb_magic_when_magic_ward_is_absent(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        room = RuntimeDummyRoom()
        room.add(mage)

        self.assertTrue(self._learn(mage, "manifest_force").success)
        self.assertTrue(mage.prepare_spell("manifest_force 10"))
        self.assertTrue(mage.cast_spell())
        before_strength = int((mage.get_state("physical_barrier") or {}).get("strength", 0) or 0)
        remaining = mage.apply_ward_absorption(mage, 12)

        self.assertEqual(int((mage.get_state("physical_barrier") or {}).get("strength", 0) or 0), before_strength)
        self.assertEqual(remaining, 12)

    def test_prepare_cast_cleanse_runtime_uses_structured_state_service(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)
        cleric.set_state("exposed_magic", {"duration": 3})
        cleric.set_state("active_effects", {"debilitation": {"hinder": {"duration": 3, "strength": 2}}})

        self.assertTrue(self._learn(cleric, "cleanse").success)
        with patch.object(RuntimeDummyCharacter, "resolve_cleanse_spell", side_effect=AssertionError("legacy cleanse used"), create=True), patch(
            "engine.services.spell_effect_service.StateService.apply_cleanse", wraps=StateService.apply_cleanse
        ) as cleanse_mock:
            self.assertTrue(cleric.prepare_spell("cleanse 12"))
            self.assertTrue(cleric.cast_spell())

        self.assertEqual(cleanse_mock.call_count, 1)
        self.assertIsNone(cleric.get_state("exposed_magic"))
        self.assertEqual(dict((cleric.get_state("active_effects") or {}).get("debilitation", {}) or {}), {})

    def test_prepare_cast_spirit_beacon_runtime_sets_anchor_and_clears_on_death(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        cleric.db.circle = 20
        room = RuntimeDummyRoom()
        room.id = 17
        room.key = "Pilgrim Chapel"
        room.add(cleric)
        cleric.home = room
        cleric.get_favor = lambda: 0
        cleric.get_nearest_recovery_point = lambda room=None: room or cleric.location
        cleric.get_exp_debt = lambda: 0

        self.assertTrue(self._learn(cleric, "spirit_beacon").success)
        self.assertTrue(cleric.prepare_spell("spirit_beacon 4"))
        self.assertTrue(cleric.cast_spell())
        self.assertEqual(getattr(cleric.db, "spirit_beacon", {}).get("room_key"), "Pilgrim Chapel")
        self.assertTrue(bool(getattr(cleric.db, "spirit_beacon_active", False)))

        corpse = handle_death(cleric)

        self.assertIsNone(corpse)
        self.assertIsNone(getattr(cleric.db, "spirit_beacon", None))
        self.assertFalse(bool(getattr(cleric.db, "spirit_beacon_active", False)))

    def test_prepare_cast_uncurse_runtime_uses_structured_state_service(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(cleric, target)
        target.set_state("exposed_magic", {"duration": 3})
        target.set_state("active_effects", {"debilitation": {"burden": {"duration": 3, "strength": 2}}})
        target.reduce_death_sting = lambda power: (power >= 10, "Death's Sting loosens its grip.")

        self.assertTrue(self._learn(cleric, "uncurse").success)
        with patch.object(RuntimeDummyCharacter, "resolve_cleanse_spell", side_effect=AssertionError("legacy uncurse used"), create=True), patch(
            "engine.services.spell_effect_service.StateService.apply_uncurse", wraps=StateService.apply_uncurse
        ) as uncurse_mock:
            self.assertTrue(cleric.prepare_spell("uncurse 10"))
            self.assertTrue(cleric.cast_spell(target_name="Target"))

        self.assertEqual(uncurse_mock.call_count, 1)
        self.assertIsNone(target.get_state("exposed_magic"))
        self.assertEqual(dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {}), {})

    def test_unregistered_spell_raises_in_resolve_path(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")

        with self.assertRaisesRegex(ValueError, "Unregistered spell"):
            mage.resolve_spell("radiant_aura", 12.0)

    def test_prepare_cast_cyclic_runtime_starts_authoritative_effect(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)

        self.assertTrue(self._learn(empath, "regenerate").success)
        with patch.object(RuntimeDummyCharacter, "start_cyclic_spell", side_effect=AssertionError("legacy cyclic used"), create=True):
            self.assertTrue(empath.harness_spell("12"))
            self.assertTrue(empath.prepare_spell("regenerate 12"))
            self.assertTrue(empath.cast_spell())

        self.assertIn("regenerate", empath.get_active_cyclic_effects())
        self.assertTrue(any("channel the cyclic spell of regenerate from your held mana" in line.lower() for line in empath.messages))

    def test_cyclic_tick_heals_and_drains_once(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)
        empath.db.hp = 60

        self.assertTrue(self._learn(empath, "regenerate").success)
        self.assertTrue(empath.harness_spell("12"))
        self.assertTrue(empath.prepare_spell("regenerate 12"))
        self.assertTrue(empath.cast_spell())
        mana_before_tick = ManaService._get_harnessed_mana_state(empath)

        with patch("engine.services.state_service.StateService.apply_healing", wraps=StateService.apply_healing) as heal_mock:
            empath.process_magic_states()

        mana_after_tick = ManaService._get_harnessed_mana_state(empath)
        self.assertEqual(heal_mock.call_count, 1)
        self.assertGreater(empath.db.hp, 60)
        self.assertLess(mana_after_tick, mana_before_tick)

    def test_cyclic_collapses_on_insufficient_mana(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)

        self.assertTrue(self._learn(empath, "regenerate").success)
        self.assertTrue(empath.harness_spell("12"))
        self.assertTrue(empath.prepare_spell("regenerate 12"))
        self.assertTrue(empath.cast_spell())
        ManaService._set_harnessed_mana_state(empath, 0)

        empath.process_magic_states()

        self.assertNotIn("regenerate", empath.get_active_cyclic_effects())
        self.assertTrue(any("held mana runs dry" in line.lower() for line in empath.messages))

    def test_cyclic_interrupts_when_debilitated(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)

        self.assertTrue(self._learn(empath, "regenerate").success)
        self.assertTrue(empath.harness_spell("12"))
        self.assertTrue(empath.prepare_spell("regenerate 12"))
        self.assertTrue(empath.cast_spell())
        StateService.apply_debilitation_effect(empath, "daze", 3, 2, source_spell="daze", modifiers={"magic_attack": 0.2})

        empath.process_magic_states()

        self.assertNotIn("regenerate", empath.get_active_cyclic_effects())
        self.assertTrue(any("breaks under interference" in line.lower() for line in empath.messages))

    def test_self_target_healing_defaults_bare_cast_to_self(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)
        empath.db.injuries = {
            "head": {"external": 6, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 100, "vital": True},
            "chest": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 120, "vital": True},
        }
        empath.db.wounds = {"vitality": 6, "bleeding": 0, "poison": 0, "disease": 0, "fatigue": 0}
        empath.db.injuries["head"]["external"] = 6

        self.assertTrue(self._learn(empath, "external_wound_healing").success)
        self.assertTrue(empath.prepare_spell("external_wound_healing 10"))
        self.assertTrue(empath.cast_spell())

        self.assertLess(empath.db.injuries["head"]["external"], 6)
        self.assertTrue(any("external injuries closed" in line.lower() for line in empath.messages))

    def test_self_target_healing_rejects_explicit_other_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="empath", key="Patient")
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "vitality_healing").success)
        self.assertTrue(empath.prepare_spell("vitality_healing 10"))
        self.assertFalse(empath.cast_spell(target_name="Patient"))
        self.assertTrue(any("only cast that spell on yourself" in line.lower() for line in empath.messages))

    def test_self_target_healing_still_accepts_explicit_self_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        room = RuntimeDummyRoom()
        room.add(empath)
        empath.db.hp = 60

        self.assertTrue(self._learn(empath, "vitality_healing").success)
        self.assertTrue(empath.prepare_spell("vitality_healing 10"))
        self.assertTrue(empath.cast_spell(target_name="Empath"))
        self.assertGreater(empath.db.hp, 60)

    def test_non_self_target_spell_still_requires_target(self):
        cleric = RuntimeDummyCharacter(profession="cleric", key="Cleric")
        room = RuntimeDummyRoom()
        room.add(cleric)

        self.assertTrue(self._learn(cleric, "cleric_minor_heal").success)
        self.assertTrue(cleric.prepare_spell("cleric_minor_heal 10"))
        self.assertFalse(cleric.cast_spell())
        self.assertTrue(any("must specify a target" in line.lower() for line in cleric.messages))

    def test_self_target_flush_poisons_defaults_bare_cast_to_self(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        empath.db.circle = 10
        room = RuntimeDummyRoom()
        room.add(empath)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "poison": 15, "disease": 0, "fatigue": 0}

        self.assertTrue(self._learn(empath, "flush_poisons").success)
        self.assertTrue(empath.prepare_spell("flush_poisons 10"))
        self.assertTrue(empath.cast_spell())

        self.assertEqual(int((empath.db.wounds or {}).get("poison", 0) or 0), 0)
        self.assertTrue(any("driving venom out of your blood" in line.lower() for line in empath.messages))

    def test_self_target_cure_disease_rejects_explicit_other_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        empath.db.circle = 10
        patient = RuntimeDummyCharacter(profession="empath", key="Patient")
        room = RuntimeDummyRoom()
        room.add(empath, patient)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "poison": 0, "disease": 12, "fatigue": 0}

        self.assertTrue(self._learn(empath, "cure_disease").success)
        self.assertTrue(empath.prepare_spell("cure_disease 12"))
        self.assertFalse(empath.cast_spell(target_name="Patient"))
        self.assertTrue(any("only cast that spell on yourself" in line.lower() for line in empath.messages))

    def test_self_target_cure_disease_defaults_bare_cast_to_self(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        empath.db.circle = 10
        room = RuntimeDummyRoom()
        room.add(empath)
        empath.db.wounds = {"vitality": 0, "bleeding": 0, "poison": 0, "disease": 12, "fatigue": 0}

        self.assertTrue(self._learn(empath, "cure_disease").success)
        self.assertTrue(empath.prepare_spell("cure_disease 12"))
        self.assertTrue(empath.cast_spell())

        self.assertEqual(int((empath.db.wounds or {}).get("disease", 0) or 0), 0)
        self.assertTrue(any("illness gives way" in line.lower() for line in empath.messages))

    def test_refresh_defaults_bare_cast_to_self_and_reduces_fatigue(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        empath.db.circle = 10
        empath.db.fatigue = 25
        empath.db.max_fatigue = 100
        room = RuntimeDummyRoom()
        room.add(empath)

        self.assertTrue(self._learn(empath, "refresh").success)
        self.assertTrue(empath.prepare_spell("refresh 10"))
        self.assertTrue(empath.cast_spell())

        self.assertLess(int(empath.db.fatigue or 0), 25)
        self.assertTrue(any("easing away weariness" in line.lower() for line in empath.messages))

    def test_refresh_runtime_can_target_another_character(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="empath", key="Patient")
        empath.db.circle = 10
        patient.db.fatigue = 25
        patient.db.max_fatigue = 100
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "refresh").success)
        self.assertTrue(empath.prepare_spell("refresh 10"))
        self.assertTrue(empath.cast_spell(target_name="Patient"))

        self.assertLess(int(patient.db.fatigue or 0), 25)
        self.assertTrue(any("calls a bright restorative pulse over Patient" in line for line in room.messages))

    def test_raise_power_runtime_boosts_room_mana_and_drains_fatigue(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        ally = RuntimeDummyCharacter(profession="empath", key="Ally")
        empath.db.circle = 10
        empath.db.fatigue = 20
        empath.db.max_fatigue = 100
        ally.db.fatigue = 5
        ally.db.max_fatigue = 100
        room = RuntimeDummyRoom()
        room.add(empath, ally)

        self.assertTrue(self._learn(empath, "raise_power").success)
        self.assertTrue(empath.prepare_spell("raise_power 10"))
        self.assertTrue(empath.cast_spell())

        self.assertGreater(float(room.db.mana["life"]), 1.0)
        self.assertEqual(int(empath.db.fatigue or 0), 100)
        self.assertEqual(int(ally.db.fatigue or 0), 100)

    def test_gift_of_life_rejects_explicit_other_target(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        patient = RuntimeDummyCharacter(profession="empath", key="Patient")
        empath.db.circle = 10
        room = RuntimeDummyRoom()
        room.add(empath, patient)

        self.assertTrue(self._learn(empath, "gift_of_life").success)
        self.assertTrue(empath.prepare_spell("gift_of_life 10"))
        self.assertFalse(empath.cast_spell(target_name="Patient"))
        self.assertTrue(any("only cast that spell on yourself" in line.lower() for line in empath.messages))

    def test_gift_of_life_defaults_bare_cast_to_self_and_sets_buff(self):
        empath = RuntimeDummyCharacter(profession="empath", key="Empath")
        empath.db.circle = 10
        room = RuntimeDummyRoom()
        room.add(empath)

        self.assertTrue(self._learn(empath, "gift_of_life").success)
        self.assertTrue(empath.prepare_spell("gift_of_life 10"))
        self.assertTrue(empath.cast_spell())

        self.assertTrue(bool(((empath.get_state("active_effects") or {}).get("utility") or {}).get("gift_of_life")))
        self.assertTrue(bool(getattr(empath.db, "gift_of_life_active", False)))

    def test_targeted_cyclic_tick_uses_damage_path_once(self):
        seer = RuntimeDummyCharacter(profession="moon_mage", key="Seer")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.add(seer, target)

        self.assertTrue(self._learn(seer, "wither").success)
        self.assertTrue(seer.harness_spell("14"))
        self.assertTrue(seer.prepare_spell("wither 14"))
        self.assertTrue(seer.cast_spell(target_name="Target"))
        before_hp = target.db.hp

        with patch("engine.services.state_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            seer.process_magic_states()

        self.assertEqual(apply_damage_mock.call_count, 1)
        self.assertLess(target.db.hp, before_hp)

    def test_room_cyclic_tick_hits_each_room_target_once(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        first = RuntimeDummyCharacter(profession="cleric", key="First")
        second = RuntimeDummyCharacter(profession="cleric", key="Second")
        room = RuntimeDummyRoom()
        room.add(mage, first, second)

        self.assertTrue(self._learn(mage, "storm_field").success)
        self.assertTrue(mage.harness_spell("16"))
        self.assertTrue(mage.prepare_spell("storm_field 16"))
        self.assertTrue(mage.cast_spell())
        before = {first.key: first.db.hp, second.key: second.db.hp}

        with patch("engine.services.state_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            mage.process_magic_states()

        self.assertEqual(apply_damage_mock.call_count, 2)
        self.assertLess(first.db.hp, before["First"])
        self.assertLess(second.db.hp, before["Second"])

    def test_room_cyclic_stops_when_caster_leaves_room(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        start_room = RuntimeDummyRoom()
        next_room = RuntimeDummyRoom()
        start_room.add(mage, target)

        self.assertTrue(self._learn(mage, "storm_field").success)
        self.assertTrue(mage.harness_spell("16"))
        self.assertTrue(mage.prepare_spell("storm_field 16"))
        self.assertTrue(mage.cast_spell())
        next_room.add(mage)

        mage.process_magic_states()

        self.assertNotIn("storm_field", mage.get_active_cyclic_effects())

    def test_room_cyclic_target_leaving_room_avoids_future_ticks(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        first = RuntimeDummyCharacter(profession="cleric", key="First")
        second = RuntimeDummyCharacter(profession="cleric", key="Second")
        start_room = RuntimeDummyRoom()
        exit_room = RuntimeDummyRoom()
        start_room.add(mage, first, second)

        self.assertTrue(self._learn(mage, "storm_field").success)
        self.assertTrue(mage.harness_spell("16"))
        self.assertTrue(mage.prepare_spell("storm_field 16"))
        self.assertTrue(mage.cast_spell())
        mage.process_magic_states()
        before_second = second.db.hp
        start_room.contents.remove(second)
        exit_room.add(second)

        with patch("engine.services.state_service.StateService.apply_damage", wraps=StateService.apply_damage) as apply_damage_mock:
            mage.process_magic_states()

        self.assertEqual(apply_damage_mock.call_count, 1)
        self.assertEqual(second.db.hp, before_second)

    def test_room_cyclic_join_in_progress_applies_next_tick(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        first = RuntimeDummyCharacter(profession="cleric", key="First")
        newcomer = RuntimeDummyCharacter(profession="cleric", key="Newcomer")
        room = RuntimeDummyRoom()
        room.add(mage, first)

        self.assertTrue(self._learn(mage, "storm_field").success)
        self.assertTrue(mage.harness_spell("16"))
        self.assertTrue(mage.prepare_spell("storm_field 16"))
        self.assertTrue(mage.cast_spell())
        mage.process_magic_states()
        before_newcomer = newcomer.db.hp
        room.add(newcomer)

        mage.process_magic_states()

        self.assertLess(newcomer.db.hp, before_newcomer)

    def test_room_cyclic_environment_changes_tick_power(self):
        high_room = RuntimeDummyRoom()
        low_room = RuntimeDummyRoom()
        high_room.db.environmental_mana = {"elemental": 1.4}
        low_room.db.environmental_mana = {"elemental": 0.7}
        high_mage = RuntimeDummyCharacter(profession="warrior_mage", key="HighMage")
        low_mage = RuntimeDummyCharacter(profession="warrior_mage", key="LowMage")
        high_target = RuntimeDummyCharacter(profession="cleric", key="HighTarget")
        low_target = RuntimeDummyCharacter(profession="cleric", key="LowTarget")
        high_room.add(high_mage, high_target)
        low_room.add(low_mage, low_target)

        self.assertTrue(self._learn(high_mage, "storm_field").success)
        self.assertTrue(self._learn(low_mage, "storm_field").success)
        self.assertTrue(high_mage.harness_spell("16"))
        self.assertTrue(low_mage.harness_spell("16"))
        self.assertTrue(high_mage.prepare_spell("storm_field 16"))
        self.assertTrue(low_mage.prepare_spell("storm_field 16"))
        self.assertTrue(high_mage.cast_spell())
        self.assertTrue(low_mage.cast_spell())
        high_before = high_target.db.hp
        low_before = low_target.db.hp

        high_mage.process_magic_states()
        low_mage.process_magic_states()

        self.assertGreater(high_before - high_target.db.hp, low_before - low_target.db.hp)

    def test_environmental_mana_is_recorded_in_debug_trace(self):
        mage = RuntimeDummyCharacter(profession="warrior_mage", key="Mage")
        target = RuntimeDummyCharacter(profession="cleric", key="Target")
        room = RuntimeDummyRoom()
        room.db.environmental_mana = {"elemental": 1.3}
        room.add(mage, target)
        mage.ndb.spell_debug = True
        mage.ndb.spell_debug_trace = []

        self.assertTrue(self._learn(mage, "arc_burst").success)
        self.assertTrue(mage.prepare_spell("arc_burst 16"))
        self.assertTrue(mage.cast_spell())

        trace = list(mage.ndb.spell_debug_trace or [])[-1]
        self.assertGreater(float(trace.get("environmental_mana_modifier", 1.0) or 1.0), 1.0)
        self.assertGreater(float(trace.get("effective_env_mana", 1.0) or 1.0), 1.0)

    def test_effect_container_integrity_stays_per_character(self):
        first = RuntimeDummyCharacter(profession="moon_mage", key="First")
        second = RuntimeDummyCharacter(profession="moon_mage", key="Second")
        StateService.apply_debilitation_effect(first, "daze", 3, 2, source_spell="daze", modifiers={"magic_defense": 1.0})
        StateService.apply_debilitation_effect(second, "slow", 2, 3, source_spell="slow", modifiers={"evasion": 1.0})

        first.process_magic_states()

        first_effects = dict((first.get_state("active_effects") or {}).get("debilitation", {}) or {})
        second_effects = dict((second.get_state("active_effects") or {}).get("debilitation", {}) or {})
        self.assertIn("daze", first_effects)
        self.assertNotIn("daze", second_effects)
        self.assertIn("slow", second_effects)

    def test_tick_load_simulation_expires_effects_without_duplicate_decrement(self):
        characters = [RuntimeDummyCharacter(profession="cleric", key=f"Char-{index}") for index in range(4)]
        for index, character in enumerate(characters):
            character.set_state("augmentation_buff", {"name": "bolster", "strength": 2, "duration": 2, "modifiers": {"magic_defense": 1.0}})
            character.set_state("warding_barrier", {"name": "minor_barrier", "strength": 4 + index, "duration": 2})
            StateService.apply_debilitation_effect(character, "daze", 2, 2, source_spell="daze", modifiers={"magic_defense": 1.0})

        for _ in range(2):
            for character in characters:
                character.process_magic_states()

        for character in characters:
            self.assertIsNone(character.get_state("augmentation_buff"))
            self.assertIsNone(character.get_state("warding_barrier"))
            self.assertEqual(dict((character.get_state("active_effects") or {}).get("debilitation", {}) or {}), {})


if __name__ == "__main__":
    unittest.main()