import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from domain.spells.spell_definitions import get_spell
from engine.services.circle_service import commit_advancement
from engine.services.mana_service import ManaService
from engine.services.spell_effect_service import SpellEffectService
from engine.services.state_service import StateService
from typeclasses.npcs import GuildLeaderNPC
from typeclasses.rooms import Room


class DummyHolder:
    pass


class DummyRoom:
    def __init__(self, mana=None):
        self.db = DummyHolder()
        self.contents = []
        if mana is not None:
            self.db.mana = dict(mana)

    def msg_contents(self, message, exclude=None):
        _exclude = exclude
        self.last_room_message = message


class RuntimeDummyCharacter:
    def __init__(self, profession="cleric", feats=None):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.location = DummyRoom()
        self.location.contents.append(self)
        self.pk = 1
        self.id = 1
        self.key = "Mage"
        self.profession = profession
        self.db.profession = profession
        self.db.circle = 10
        self.db.hp = 100
        self.db.max_hp = 100
        self.db.feats = feats
        self.db.magic_slot_pool = None
        self.states = {}
        self.messages = []

    def ensure_core_defaults(self):
        return None

    def is_profession(self, profession):
        return self.profession == str(profession or "").strip().lower()

    def get_profession(self):
        return self.profession

    def get_circle(self):
        return self.db.circle

    def get_skill(self, name):
        mapping = {
            "attunement": 100,
            "arcana": 100,
            "targeted_magic": 100,
            "utility": 100,
            "warding": 100,
            "augmentation": 100,
            "debilitation": 100,
            "primary_magic": 100,
            "evasion": 100,
        }
        return mapping.get(name, 100)

    def get_skill_rank(self, name):
        return self.get_skill(name)

    def get_stat(self, name):
        mapping = {"intelligence": 30, "discipline": 30, "wisdom": 30, "reflex": 20}
        return mapping.get(name, 30)

    def get_devotion(self):
        return 0

    def get_devotion_max(self):
        return 0

    def get_empath_shock(self):
        return 0

    def get_empath_healing_modifier(self):
        return 1.0

    def set_hp(self, value):
        self.db.hp = int(value)

    def set_state(self, key, value):
        self.states[key] = value

    def get_state(self, key):
        return self.states.get(key)

    def clear_state(self, key):
        self.states.pop(key, None)

    def adjust_empath_shock(self, amount):
        return amount

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

    def msg(self, text):
        self.messages.append(str(text))


class FeatRuntimeIntegrationTests(unittest.TestCase):
    def test_deep_attunement_increases_regen(self):
        baseline = RuntimeDummyCharacter(feats={"learned": [], "granted": []})
        buffed = RuntimeDummyCharacter(feats={"learned": ["deep_attunement"], "granted": []})
        ManaService._set_attunement_state(baseline, 50.0, 100.0)
        ManaService._set_attunement_state(buffed, 50.0, 100.0)

        baseline_result = ManaService.regenerate_attunement(baseline)
        buffed_result = ManaService.regenerate_attunement(buffed)

        self.assertGreater(float(buffed_result.data["regen"]), float(baseline_result.data["regen"]))

    def test_efficient_harnessing_reduces_harness_cost(self):
        baseline = RuntimeDummyCharacter(feats={"learned": [], "granted": []})
        buffed = RuntimeDummyCharacter(feats={"learned": ["efficient_harnessing"], "granted": []})
        ManaService._set_attunement_state(baseline, 100.0, 100.0)
        ManaService._set_attunement_state(buffed, 100.0, 100.0)

        baseline_result = ManaService.harness_mana(baseline, 20, 100, 100)
        buffed_result = ManaService.harness_mana(buffed, 20, 100, 100)

        self.assertGreater(float(baseline_result.data["attunement_spent"]), float(buffed_result.data["attunement_spent"]))

    def test_focused_preparation_extends_expiry(self):
        baseline = RuntimeDummyCharacter(feats={"learned": [], "granted": []})
        buffed = RuntimeDummyCharacter(feats={"learned": ["focused_preparation"], "granted": []})
        baseline_room = DummyRoom()
        buffed_room = DummyRoom()
        ManaService._set_attunement_state(baseline, 100.0, 100.0)
        ManaService._set_attunement_state(buffed, 100.0, 100.0)

        baseline_result = ManaService.prepare_spell(baseline, baseline_room, "holy", 10, 1, 20, spell_id="test", min_prep_time=5, expiry_window=30)
        buffed_result = ManaService.prepare_spell(buffed, buffed_room, "holy", 10, 1, 20, spell_id="test", min_prep_time=5, expiry_window=30)

        self.assertTrue(baseline_result.success)
        self.assertTrue(buffed_result.success)
        baseline_prepared = ManaService._get_prepared_mana_state(baseline)
        buffed_prepared = ManaService._get_prepared_mana_state(buffed)
        baseline_expiry = float(baseline_prepared["expiry_at"] - baseline_prepared["prep_started_at"])
        buffed_expiry = float(buffed_prepared["expiry_at"] - buffed_prepared["prep_started_at"])
        self.assertGreater(buffed_expiry, baseline_expiry)

    def test_cautious_casting_reduces_backlash_vitality_loss(self):
        baseline = RuntimeDummyCharacter(feats={"learned": [], "granted": []})
        buffed = RuntimeDummyCharacter(feats={"learned": ["cautious_casting"], "granted": []})

        baseline_result = ManaService._apply_backlash_payload(baseline, {"vitality_loss": 20})
        buffed_result = ManaService._apply_backlash_payload(buffed, {"vitality_loss": 20})

        self.assertEqual(baseline_result["vitality_loss"], 20)
        self.assertEqual(buffed_result["vitality_loss"], 15)

    def test_efficient_channeling_reduces_cyclic_drain(self):
        baseline = RuntimeDummyCharacter(feats={"learned": [], "granted": []})
        buffed = RuntimeDummyCharacter(feats={"learned": ["efficient_channeling"], "granted": []})
        ManaService._set_attunement_state(baseline, 100.0, 100.0)
        ManaService._set_attunement_state(buffed, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(baseline, 20)
        ManaService._set_harnessed_mana_state(buffed, 20)
        spell = get_spell("regenerate")

        SpellEffectService.apply_spell(baseline, spell, 20.0, quality="normal", target=baseline)
        SpellEffectService.apply_spell(buffed, spell, 20.0, quality="normal", target=buffed)
        baseline_before = ManaService._get_harnessed_mana_state(baseline)
        buffed_before = ManaService._get_harnessed_mana_state(buffed)

        baseline_tick = StateService.process_cyclic_effects(baseline)
        buffed_tick = StateService.process_cyclic_effects(buffed)

        baseline_cost = float((baseline_tick.data or {}).get("processed_effects", [{}])[0].get("mana_per_tick", 0.0))
        buffed_cost = float((buffed_tick.data or {}).get("processed_effects", [{}])[0].get("mana_per_tick", 0.0))
        self.assertLess(buffed_cost, baseline_cost)
        self.assertGreater(baseline_before - ManaService._get_harnessed_mana_state(baseline), buffed_before - ManaService._get_harnessed_mana_state(buffed))

    def test_efficient_harnessing_only_affects_attunement_sustain(self):
        held_caster = RuntimeDummyCharacter(feats={"learned": ["efficient_channeling", "efficient_harnessing"], "granted": []})
        attune_caster = RuntimeDummyCharacter(feats={"learned": ["efficient_channeling", "efficient_harnessing", "raw_channeling"], "granted": []})
        ManaService._set_attunement_state(held_caster, 100.0, 100.0)
        ManaService._set_attunement_state(attune_caster, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(held_caster, 20)
        ManaService._set_harnessed_mana_state(attune_caster, 0)
        spell = get_spell("regenerate")

        held_start = SpellEffectService.apply_spell(held_caster, spell, 20.0, quality="normal", target=held_caster)
        attune_start = SpellEffectService.apply_spell(attune_caster, spell, 20.0, quality="normal", target=attune_caster)
        self.assertTrue(held_start.success)
        self.assertTrue(attune_start.success)

        held_tick = StateService.process_cyclic_effects(held_caster)
        attune_tick = StateService.process_cyclic_effects(attune_caster)

        self.assertEqual((held_tick.data or {}).get("processed_effects", [{}])[0].get("mana_per_tick"), 1.0)
        self.assertEqual((attune_tick.data or {}).get("processed_effects", [{}])[0].get("mana_per_tick"), 1.0)
        self.assertEqual(int(ManaService._get_attunement_state(held_caster)["current"]), 100)
        self.assertEqual(int(ManaService._get_attunement_state(attune_caster)["current"]), 99)


class CircleGrantIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.room = create_object(Room, key="Feat Circle Room", nohome=True)
        self.created.append(self.room)
        self.leader = create_object(GuildLeaderNPC, key="Feat Leader", location=self.room, home=self.room, nohome=True)
        self.created.append(self.leader)
        self.leader.db.leads_profession = "cleric"

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def test_cleric_circle_two_receives_efficient_channeling(self):
        caller = SimpleNamespace(
            location=self.room,
            db=SimpleNamespace(
                profession="cleric",
                circle=1,
                coins=1000,
                exp_skill_state={"theurgy": {"rank": 200}},
                spellbook={"known_spells": {}},
                magic_slot_pool=None,
                feats={"learned": [], "granted": []},
            ),
            grants=[],
            syncs=0,
        )

        caller.grant_tdp = lambda amount, reason="": caller.grants.append((amount, reason))
        caller.sync_client_state = lambda: setattr(caller, "syncs", caller.syncs + 1)
        caller.get_profession = lambda: caller.db.profession
        caller.get_circle = lambda: caller.db.circle
        caller.get_skill = lambda _skill: 100

        result = commit_advancement(caller)

        self.assertTrue(result.ok)
        self.assertIn("Efficient Channeling", result.message)
        self.assertIn("efficient_channeling", caller.db.feats["granted"])


if __name__ == "__main__":
    unittest.main()