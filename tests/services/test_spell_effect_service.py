import unittest
from unittest.mock import patch

from domain.spells.spell_definitions import SPELL_REGISTRY, get_spell
from engine.services.mana_service import ManaService
from engine.services.state_service import StateService
from engine.services.spell_contest_service import SpellContestService
from engine.services.spell_effect_service import SpellEffectService
from world.systems.death import handle_death


class DummyHolder:
    pass


class DummyCharacter:
    def __init__(self, hp=50, max_hp=100, key="Dummy", profession="empath", healing_modifier=1.0):
        self.db = DummyHolder()
        self.ndb = DummyHolder()
        self.db.hp = hp
        self.db.max_hp = max_hp
        self.db.wounds = {"vitality": 0, "bleeding": 0, "poison": 0, "disease": 0, "fatigue": 0, "trauma": 0}
        self.db.injuries = {
            "head": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 100, "vital": True},
            "chest": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}, "max": 120, "vital": True},
        }
        self.db.stats = {"reflex": 10, "magic_resistance": 10}
        self.db.encumbrance_dirty = False
        self.ndb.spell_debug = False
        self.ndb.spell_debug_trace = []
        self.key = key
        self.profession = profession
        self.healing_modifier = healing_modifier
        self.id = 7
        self.states = {}

    def set_hp(self, value):
        self.db.hp = max(0, min(int(value), int(self.db.max_hp or 0)))

    def get_empath_wounds(self):
        return dict(self.db.wounds)

    def get_empath_wound(self, wound_type):
        return int(self.db.wounds.get(str(wound_type or "").strip().lower(), 0) or 0)

    def set_empath_wound(self, wound_type, value):
        wound_key = str(wound_type or "").strip().lower()
        self.db.wounds[wound_key] = max(0, min(100, int(value or 0)))
        return self.db.wounds[wound_key]

    def sync_client_state(self):
        return None

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
        normalized = str(name or "").strip().lower().replace(" ", "_")
        if name in self.db.stats:
            return int(self.db.stats[name] or 0) + self.get_effect_stat_modifier(normalized)
        mapping = {"intelligence": 30, "discipline": 30, "wisdom": 30, "reflex": 10}
        return int(mapping.get(name, 30) or 30) + self.get_effect_stat_modifier(normalized)

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

    def get_effect_stat_modifier(self, stat_name, category="debilitation"):
        total = 0
        for effect in dict((self.get_state("active_effects") or {}).get(category, {}) or {}).values():
            total += int(dict(effect.get("stat_debuffs") or {}).get(stat_name, 0) or 0)
        return total

    def get_encumbrance_modifier(self, category="debilitation"):
        total = 0
        for effect in dict((self.get_state("active_effects") or {}).get(category, {}) or {}).values():
            total += int(effect.get("encumbrance_modifier", 0) or 0)
        return total

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
        self.db = DummyHolder()
        self.key = "Test Room"
        self.contents = []
        for obj in contents:
            if obj is not None:
                obj.location = self
                self.contents.append(obj)


class DummyNpc:
    def __init__(self, key="Critter", *, undead=False):
        self.db = DummyHolder()
        self.db.target = None
        self.db.in_combat = False
        self.db.creature_type = "undead" if undead else "animal"
        self.key = key
        self.id = hash((key, undead)) & 0xFFFF
        self.location = None
        self.states = {}
        self.ndb = DummyHolder()
        self.ndb.threat_table = {}

    def get_state(self, key):
        return self.states.get(key)

    def set_state(self, key, value):
        self.states[key] = value

    def clear_state(self, key):
        self.states.pop(key, None)

    def get_target(self):
        return getattr(self.db, "target", None)

    def set_target(self, target):
        self.db.target = target
        self.db.in_combat = target is not None

    def add_threat(self, target, amount):
        target_id = str(getattr(target, "id", "") or "")
        current = int(self.ndb.threat_table.get(target_id, 0) or 0)
        self.ndb.threat_table[target_id] = current + int(amount or 0)

    def get_threat(self, target):
        return int(self.ndb.threat_table.get(str(getattr(target, "id", "") or ""), 0) or 0)

    def remove_target(self, target):
        self.ndb.threat_table.pop(str(getattr(target, "id", "") or ""), None)

    def get_highest_threat(self):
        if not self.ndb.threat_table or self.location is None:
            return None
        best_id = max(self.ndb.threat_table, key=lambda key: self.ndb.threat_table[key])
        for obj in list(getattr(self.location, "contents", []) or []):
            if str(getattr(obj, "id", "") or "") == best_id:
                return obj
        return None

    def disengage(self, emit_message=True):
        _emit_message = emit_message
        self.db.target = None
        self.db.in_combat = False

    def is_dead(self):
        return False


class DummyCorpse:
    def __init__(self, owner=None, key="corpse"):
        self.db = DummyHolder()
        self.db.is_corpse = True
        self.key = key
        self.id = 99
        self.location = None
        self._owner = owner

    def get_owner(self):
        return self._owner


class DummyHiddenTarget(DummyCharacter):
    def __init__(self, key="Hidden Target", profession="cleric"):
        super().__init__(hp=50, max_hp=100, key=key, profession=profession)
        self.db.stealthed = True
        self.set_state("hidden", {"strength": 25})

    def is_hidden(self):
        return bool(self.get_state("hidden")) or bool(getattr(self.db, "stealthed", False))

    def reveal(self):
        self.db.stealthed = False
        self.clear_state("hidden")


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

    def test_vitality_healing_rejects_other_targets(self):
        caster = DummyCharacter(hp=40, max_hp=100, key="Empath", profession="empath")
        target = DummyCharacter(hp=30, max_hp=100, key="Patient", profession="empath")

        result = SpellEffectService.apply_spell(caster, get_spell("vitality_healing"), 20.0, quality="strong", target=target)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "self_target_only")

    def test_heal_wounds_reduces_carried_empath_wounds(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.set_empath_wound("vitality", 18)
        caster.set_empath_wound("bleeding", 12)

        result = SpellEffectService.apply_spell(caster, get_spell("heal_wounds"), 30.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["healing_mode"], "empath_wounds")
        self.assertGreater(result.data["effect_payload"]["heal_amount"], 0)
        self.assertLess(caster.get_empath_wound("vitality"), 18)
        self.assertLess(caster.get_empath_wound("bleeding"), 12)

    def test_heal_scars_reduces_existing_scars(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.injuries["head"]["scar"] = 3
        caster.db.injuries["chest"]["scar"] = 2

        result = SpellEffectService.apply_spell(caster, get_spell("heal_scars"), 24.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["healing_mode"], "scars")
        self.assertGreater(result.data["effect_payload"]["healed_scars"], 0)
        self.assertLess(sum(part["scar"] for part in caster.db.injuries.values()), 5)

    def test_external_wound_healing_reduces_external_injuries_only(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.injuries["head"]["external"] = 6
        caster.db.injuries["head"]["internal"] = 4

        result = SpellEffectService.apply_spell(caster, get_spell("external_wound_healing"), 12.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["healing_mode"], "external_wounds")
        self.assertLess(caster.db.injuries["head"]["external"], 6)
        self.assertEqual(caster.db.injuries["head"]["internal"], 4)

    def test_internal_wound_healing_reduces_internal_injuries_only(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.injuries["head"]["external"] = 6
        caster.db.injuries["head"]["internal"] = 4

        result = SpellEffectService.apply_spell(caster, get_spell("internal_wound_healing"), 14.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["healing_mode"], "internal_wounds")
        self.assertEqual(caster.db.injuries["head"]["external"], 6)
        self.assertLess(caster.db.injuries["head"]["internal"], 4)

    def test_heal_combines_wound_and_scar_reduction(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.injuries["head"]["external"] = 5
        caster.db.injuries["head"]["internal"] = 3
        caster.db.injuries["head"]["scar"] = 2

        result = SpellEffectService.apply_spell(caster, get_spell("heal"), 30.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["healing_mode"], "combined_heal")
        self.assertLess(caster.db.injuries["head"]["external"], 5)
        self.assertLess(caster.db.injuries["head"]["internal"], 3)
        self.assertLess(caster.db.injuries["head"]["scar"], 2)

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

    def test_bless_routes_through_structured_utility_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Squire", profession="cleric")
        spell = get_spell("bless")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "utility")
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "bless")
        bless_state = dict((target.get_state("active_effects") or {}).get("utility", {}).get("bless", {}) or {})
        self.assertGreater(int(bless_state.get("strength", 0) or 0), 0)
        self.assertTrue(bool(getattr(target.db, "bless_active", False)))

    def test_innocence_clears_normal_targets_and_enrages_undead(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        ally = DummyCharacter(hp=100, max_hp=100, key="Ally", profession="cleric")
        ally.account = object()
        normal = DummyNpc("Forest Wolf")
        undead = DummyNpc("Restless Dead", undead=True)
        room = DummyRoom(caster, ally, normal, undead)
        normal.set_target(caster)
        normal.add_threat(caster, 12)

        result = SpellEffectService.apply_spell(caster, get_spell("innocence"), 20.0, quality="strong")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "innocence")
        self.assertIn("Forest Wolf", result.data["effect_payload"]["released_targets"])
        self.assertIn("Restless Dead", result.data["effect_payload"]["undead_backfires"])
        self.assertIsNone(normal.get_target())
        self.assertFalse(normal.db.in_combat)
        self.assertIs(undead.get_target(), caster)
        innocence_state = dict((caster.get_state("active_effects") or {}).get("utility", {}).get("innocence", {}) or {})
        self.assertTrue(bool(getattr(caster.db, "innocence_active", False)))
        self.assertGreater(int(innocence_state.get("duration", 0) or 0), 0)

    def test_zone_of_protection_applies_group_ward_to_accounted_room_members(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        ally = DummyCharacter(hp=100, max_hp=100, key="Patient", profession="cleric")
        ally.account = object()
        observer = DummyNpc("Training Goblin")
        room = DummyRoom(caster, ally, observer)

        result = SpellEffectService.apply_spell(caster, get_spell("zone_of_protection"), 20.0, quality="strong")

        self.assertTrue(result.success)
        payload = dict(result.data["effect_payload"] or {})
        self.assertEqual(payload["effect_family"], "warding")
        self.assertTrue(bool(payload.get("group_target", False)))
        self.assertEqual(int(payload.get("target_count", 0) or 0), 2)
        caster_ward = dict((caster.get_state("active_effects") or {}).get("warding", {}).get("zone_of_protection", {}) or {})
        ally_ward = dict((ally.get_state("active_effects") or {}).get("warding", {}).get("zone_of_protection", {}) or {})
        observer_ward = dict((observer.get_state("active_effects") or {}).get("warding", {}).get("zone_of_protection", {}) or {})
        self.assertGreater(int(caster_ward.get("strength", 0) or 0), 0)
        self.assertGreater(int(ally_ward.get("strength", 0) or 0), 0)
        self.assertEqual(observer_ward, {})

    def test_spirit_beacon_records_anchor_when_departure_is_forced(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        room = type("Room", (), {"id": 41, "key": "Quiet Chapel"})()
        recovery = type("Recovery", (), {"id": 99, "key": "Haven Shrine"})()
        caster.location = room
        caster.home = room
        caster.get_favor = lambda: 0
        caster.get_nearest_recovery_point = lambda room=None: recovery
        spell = get_spell("spirit_beacon")

        result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "spirit_beacon")
        self.assertEqual(getattr(caster.db, "spirit_beacon", {}).get("room_key"), "Quiet Chapel")
        self.assertEqual(getattr(caster.db, "spirit_beacon", {}).get("recovery_point_key"), "Haven Shrine")
        spirit_state = dict((caster.get_state("active_effects") or {}).get("utility", {}).get("spirit_beacon", {}) or {})
        self.assertEqual(spirit_state.get("beacon_room_key"), "Quiet Chapel")
        self.assertTrue(bool(getattr(caster.db, "spirit_beacon_active", False)))

    def test_spirit_beacon_rejects_when_favor_remains(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        caster.get_favor = lambda: 2
        spell = get_spell("spirit_beacon")

        result = SpellEffectService.apply_spell(caster, spell, 8.0, quality="normal")

        self.assertFalse(result.success)
        self.assertEqual((result.data or {}).get("reason"), "favor_available")

    def test_protection_from_evil_applies_both_ward_and_defensive_modifiers(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Pilgrim", profession="cleric")
        spell = get_spell("protection_from_evil")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "warding")
        self.assertEqual(target.get_state("warding_barrier")["name"], "protection_from_evil")
        augmentation = dict((target.get_state("active_effects") or {}).get("augmentation", {}).get("protection_from_evil", {}) or {})
        self.assertEqual(dict(augmentation.get("modifiers") or {}).get("magic_defense"), 1.0)

    def test_holy_light_routes_through_light_utility_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("holy_light")

        result = SpellEffectService.apply_spell(caster, spell, 10.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "light")
        self.assertEqual(caster.get_state("utility_light")["name"], "holy_light")

    def test_major_physical_protection_scales_above_minor_physical_protection(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")

        minor = SpellEffectService.apply_spell(caster, get_spell("minor_physical_protection"), 20.0, quality="normal")
        major = SpellEffectService.apply_spell(caster, get_spell("major_physical_protection"), 20.0, quality="normal")

        self.assertTrue(minor.success)
        self.assertTrue(major.success)
        self.assertGreater(major.data["effect_payload"]["barrier_strength"], minor.data["effect_payload"]["barrier_strength"])
        self.assertTrue(bool((caster.get_state("physical_barrier") or {}).get("absorbs_physical", False)))

    def test_halo_routes_through_bounded_ward_placeholder(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("halo")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "warding")
        self.assertEqual(caster.get_state("warding_barrier")["name"], "halo")
        augmentation = dict((caster.get_state("active_effects") or {}).get("augmentation", {}).get("halo", {}) or {})
        self.assertEqual(dict(augmentation.get("modifiers") or {}).get("evasion"), 1.0)

    def test_divine_radiance_routes_through_warding_and_emits_light(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("divine_radiance")

        result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "warding")
        self.assertEqual(caster.get_state("warding_barrier")["name"], "divine_radiance")
        self.assertEqual(caster.get_state("utility_light")["spell_id"], "divine_radiance")

    def test_rejuvenation_routes_through_existing_revive_hook(self):
        owner = DummyCharacter(hp=0, max_hp=100, key="Fallen", profession="cleric")
        corpse = DummyCorpse(owner=owner, key="corpse of fallen")
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        caster.perform_cleric_revive = lambda target: (target is corpse, "revived")

        result = SpellEffectService.apply_spell(caster, get_spell("rejuvenation"), 10.0, quality="normal", target=corpse)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "resurrection")
        self.assertEqual(result.data["effect_payload"]["target_key"], "Fallen")
        self.assertEqual(result.data["effect_payload"]["corpse_key"], "corpse of fallen")

    def test_rejuvenation_requires_corpse_target(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Patient", profession="cleric")
        caster.perform_cleric_revive = lambda corpse: (True, "revived")

        result = SpellEffectService.apply_spell(caster, get_spell("rejuvenation"), 10.0, quality="normal", target=target)

        self.assertFalse(result.success)
        self.assertIn("corpse", result.errors[0].lower())

    def test_mass_rejuvenation_returns_deferred_placeholder_failure(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")

        result = SpellEffectService.apply_spell(caster, get_spell("mass_rejuvenation"), 20.0, quality="normal", target=caster)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "deferred_held_mana_ritual")

    def test_manifest_force_routes_through_physical_barrier_mirror(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("manifest_force")

        result = SpellEffectService.apply_spell(caster, spell, 1.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["barrier_strength"], 30)
        self.assertEqual(result.data["effect_payload"]["duration"], 600)
        self.assertTrue(bool(caster.get_state("physical_barrier")))
        self.assertTrue(bool(caster.get_state("warding_barrier")))
        self.assertTrue(bool(caster.get_state("physical_barrier").get("absorbs_physical", False)))

    def test_manifest_force_scales_capacity_and_duration_from_mana(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("manifest_force")

        mid = SpellEffectService.apply_spell(caster, spell, 10.0, quality="normal")
        high = SpellEffectService.apply_spell(caster, spell, 30.0, quality="normal")

        self.assertEqual(mid.data["effect_payload"]["barrier_strength"], 34)
        self.assertEqual(high.data["effect_payload"]["barrier_strength"], 44)
        self.assertGreater(mid.data["effect_payload"]["duration"], 600)
        self.assertEqual(high.data["effect_payload"]["duration"], 2400)

    def test_manifest_force_recast_replaces_remaining_capacity(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("manifest_force")

        first = SpellEffectService.apply_spell(caster, spell, 50.0, quality="normal")
        StateService.consume_ward(caster, "manifest_force", 20)
        replaced = SpellEffectService.apply_spell(caster, spell, 10.0, quality="normal")

        self.assertTrue(first.success)
        self.assertTrue(replaced.success)
        self.assertEqual(caster.get_state("physical_barrier")["strength"], 34)

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

    def test_gauge_flow_sets_capability_flag_and_expires(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        spell = get_spell("gauge_flow")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "gauge_flow")
        self.assertTrue(bool(getattr(caster.db, "gauge_flow_active", False)))
        duration = int(result.data["effect_payload"]["duration"] or 0)
        for _ in range(duration):
            StateService.tick_active_effects(caster)
        self.assertFalse(bool(getattr(caster.db, "gauge_flow_active", False)))

    def test_cyclic_spell_prefers_held_mana_when_available(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.feats = {"learned": ["raw_channeling"], "granted": []}
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(caster, 12)
        spell = get_spell("regenerate")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=caster)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["cyclic_state"]["sustain_source"], "held_mana")

    def test_cyclic_spell_uses_attunement_with_raw_channeling_when_no_held_mana(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.feats = {"learned": ["raw_channeling"], "granted": []}
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(caster, 0)
        spell = get_spell("regenerate")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=caster)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["cyclic_state"]["sustain_source"], "attunement")

    def test_cyclic_spell_requires_harness_without_raw_channeling(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.feats = {"learned": [], "granted": []}
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(caster, 0)
        spell = get_spell("regenerate")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=caster)

        self.assertFalse(result.success)
        self.assertIn("Use HARNESS", result.errors[0])

    def test_cyclic_spell_enforces_single_active_pattern(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.feats = {"learned": ["raw_channeling"], "granted": []}
        ManaService._set_attunement_state(caster, 100.0, 100.0)
        ManaService._set_harnessed_mana_state(caster, 12)
        StateService.apply_cyclic_effect(caster, "regenerate", {"spell_name": "Regenerate", "mana_per_tick": 2, "sustain_source": "held_mana"})
        held_before = ManaService._get_harnessed_mana_state(caster)
        spell = get_spell("storm_field")

        result = SpellEffectService.apply_spell(caster, spell, 20.0, quality="normal", target=None)

        self.assertFalse(result.success)
        self.assertEqual((result.data or {}).get("reason"), "single_cyclic_enforced")
        self.assertEqual(ManaService._get_harnessed_mana_state(caster), held_before)

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

    def test_flush_poisons_clears_caster_poison_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.set_empath_wound("poison", 15)

        result = SpellEffectService.apply_spell(caster, get_spell("flush_poisons"), 20.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "flush_poisons")
        self.assertEqual(result.data["effect_payload"]["removed_amount"], 15)
        self.assertEqual(caster.get_empath_wound("poison"), 0)

    def test_cure_disease_clears_caster_disease_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.set_empath_wound("disease", 12)

        result = SpellEffectService.apply_spell(caster, get_spell("cure_disease"), 20.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "cure_disease")
        self.assertEqual(result.data["effect_payload"]["removed_amount"], 12)
        self.assertEqual(caster.get_empath_wound("disease"), 0)

    def test_flush_poisons_rejects_other_targets(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        target = DummyCharacter(hp=100, max_hp=100, key="Patient", profession="empath")

        result = SpellEffectService.apply_spell(caster, get_spell("flush_poisons"), 20.0, quality="normal", target=target)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "self_target_only")

    def test_mesmerize_pacifies_target_on_success(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        target = DummyNpc("Forest Wolf")
        room = DummyRoom(caster, target)
        target.set_target(caster)
        target.add_threat(caster, 25)

        result = SpellEffectService.apply_spell(caster, get_spell("mesmerize"), 80.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_family"], "debilitation")
        self.assertEqual(result.data["effect_payload"]["effect_type"], "mesmerize")
        self.assertTrue(bool(result.data["effect_payload"].get("pacified", False)))
        self.assertIsNone(target.get_target())
        self.assertFalse(bool(target.db.in_combat))
        self.assertTrue(bool(target.get_state("mesmerized")))

    def test_water_purification_marks_room_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        room = DummyRoom(caster)

        result = SpellEffectService.apply_spell(caster, get_spell("water_purification"), 18.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "water_purification")
        self.assertEqual(getattr(room.db, "water_purification", {}).get("spell_id"), "water_purification")
        self.assertTrue(bool(getattr(caster.db, "water_purification_active", False)))

    def test_swarm_marks_room_state_on_target_room(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        target = DummyNpc("Bandit")
        room = DummyRoom(caster, target)

        result = SpellEffectService.apply_spell(caster, get_spell("swarm"), 18.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "swarm")
        self.assertEqual(getattr(room.db, "swarm", {}).get("spell_id"), "swarm")
        self.assertTrue(bool(getattr(caster.db, "swarm_active", False)))

    def test_branch_break_deals_damage_on_success(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        target = DummyCharacter(hp=100, max_hp=100, key="Bandit", profession="cleric")
        room = DummyRoom(caster, target)

        result = SpellEffectService.apply_spell(caster, get_spell("branch_break"), 80.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_type"], "branch_break")
        self.assertGreater(int(result.data["effect_payload"].get("final_damage", 0) or 0), 0)

    def test_haraweps_bonds_sets_restrained_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        target = DummyNpc("Bandit")
        room = DummyRoom(caster, target)

        result = SpellEffectService.apply_spell(caster, get_spell("haraweps_bonds"), 80.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertTrue(bool(result.data["effect_payload"].get("restrained", False)))
        self.assertTrue(bool(target.get_state("haraweps_bonds")))

    def test_other_target_room_effect_rejects_self_target(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Ranger", profession="ranger")
        room = DummyRoom(caster)

        result = SpellEffectService.apply_spell(caster, get_spell("swarm"), 18.0, quality="normal", target=caster)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "other_target_only")

    def test_refresh_reduces_self_fatigue_and_defaults_to_caster(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.fatigue = 30
        caster.db.max_fatigue = 100

        result = SpellEffectService.apply_spell(caster, get_spell("refresh"), 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "refresh")
        self.assertTrue(result.data["effect_payload"]["self_target"])
        self.assertLess(int(caster.db.fatigue or 0), 30)

    def test_refresh_other_target_is_less_effective(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.fatigue = 30
        caster.db.max_fatigue = 100
        target = DummyCharacter(hp=100, max_hp=100, key="Patient", profession="empath")
        target.db.fatigue = 30
        target.db.max_fatigue = 100

        self_result = SpellEffectService.apply_spell(caster, get_spell("refresh"), 12.0, quality="normal")
        caster.db.fatigue = 30
        other_result = SpellEffectService.apply_spell(caster, get_spell("refresh"), 12.0, quality="normal", target=target)

        self.assertTrue(self_result.success)
        self.assertTrue(other_result.success)
        self.assertLess(int(target.db.fatigue or 0), 30)
        self.assertLess(int((other_result.data or {}).get("effect_payload", {}).get("fatigue_reduced", 0) or 0), int((self_result.data or {}).get("effect_payload", {}).get("fatigue_reduced", 0) or 0))

    def test_raise_power_boosts_room_life_mana_and_drains_group_fatigue(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.fatigue = 20
        caster.db.max_fatigue = 100
        target = DummyCharacter(hp=100, max_hp=100, key="Patient", profession="empath")
        target.account = object()
        target.db.fatigue = 10
        target.db.max_fatigue = 100
        room = DummyRoom(caster, target)
        room.db = DummyHolder()
        room.db.mana = {"holy": 1.0, "life": 1.0, "elemental": 1.0, "lunar": 1.0}
        caster.location = room
        target.location = room

        result = SpellEffectService.apply_spell(caster, get_spell("raise_power"), 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "raise_power")
        self.assertGreater(float(room.db.mana["life"]), 1.0)
        self.assertEqual(int(caster.db.fatigue or 0), 100)
        self.assertEqual(int(target.db.fatigue or 0), 100)

    def test_gift_of_life_sets_utility_buff_state(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")

        result = SpellEffectService.apply_spell(caster, get_spell("gift_of_life"), 12.0, quality="normal")

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["utility_effect"], "gift_of_life")
        self.assertTrue(bool(((caster.get_state("active_effects") or {}).get("utility") or {}).get("gift_of_life")))
        self.assertTrue(bool(getattr(caster.db, "gift_of_life_active", False)))

    def test_gift_of_life_blocks_when_saf_is_active(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Empath", profession="empath")
        caster.db.empath_saf_duration = 10800
        caster.db.empath_saf_burden = 3
        caster.db.empath_permashock = False

        result = SpellEffectService.apply_spell(caster, get_spell("gift_of_life"), 12.0, quality="normal")

        self.assertFalse(result.success)
        self.assertEqual((result.data or {}).get("reason"), "saf")
        self.assertFalse(bool(((caster.get_state("active_effects") or {}).get("utility") or {}).get("gift_of_life")))

    def test_uncurse_routes_through_state_service_and_relieves_death_sting(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Pilgrim", profession="cleric")
        target.set_state("exposed_magic", {"duration": 3})
        target.set_state("active_effects", {"debilitation": {"burden": {"duration": 3, "strength": 2}}})
        target.reduce_death_sting = lambda power: (power >= 10, "Death's Sting loosens its grip.")
        spell = get_spell("uncurse")

        with patch("engine.services.spell_effect_service.StateService.apply_uncurse", wraps=StateService.apply_uncurse) as uncurse_mock:
            result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertEqual(uncurse_mock.call_count, 1)
        self.assertTrue(result.data["effect_payload"]["removed"])
        self.assertTrue(result.data["effect_payload"]["death_sting_relieved"])
        self.assertIsNone(target.get_state("exposed_magic"))
        self.assertEqual(dict((target.get_state("active_effects") or {}).get("debilitation", {}) or {}), {})

    def test_handle_death_clears_spirit_beacon_utility_flag(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        room = type("Room", (), {"id": 41, "key": "Quiet Chapel", "msg_contents": lambda self, message, exclude=None: None})()
        recovery = type("Recovery", (), {"id": 99, "key": "Haven Shrine"})()
        caster.location = room
        caster.home = room
        caster.get_favor = lambda: 0
        caster.get_nearest_recovery_point = lambda room=None: recovery
        caster.get_exp_debt = lambda: 0
        caster.ensure_core_defaults = lambda: None
        caster.msg = lambda message: None
        spell = get_spell("spirit_beacon")

        applied = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal")
        corpse = handle_death(caster)

        self.assertTrue(applied.success)
        self.assertIsNone(corpse)
        self.assertIsNone(getattr(caster.db, "spirit_beacon", None))
        self.assertFalse(bool(getattr(caster.db, "spirit_beacon_active", False)))

    def test_flare_routes_through_targeted_magic_handler(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("flare")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["spell_type"], "targeted_magic")
        self.assertEqual(result.data["effect_payload"]["effect_family"], "targeted_magic")

    def test_strange_arrow_routes_mixed_damage_components(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Mage", profession="warrior_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("strange_arrow")

        result = SpellEffectService.apply_spell(caster, spell, 30.0, quality="strong", target=target)

        self.assertTrue(result.success)
        components = list(result.data["effect_payload"].get("damage_components", []) or [])
        self.assertEqual([entry["damage_type"] for entry in components], ["puncture", "electrical"])
        self.assertGreater(sum(float(entry["final_damage"]) for entry in components), 0.0)

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

    def test_aesrela_everild_uses_overridden_contest_profile_and_stuns(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("aesrela_everild")

        with patch("engine.services.spell_contest_service.SpellContestService._resolve_spell_contest", wraps=SpellContestService._resolve_spell_contest) as contest_mock:
            result = SpellEffectService.apply_spell(caster, spell, 40.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(contest_mock.call_args.kwargs["primary_skill"], "theurgy")
        self.assertEqual(contest_mock.call_args.kwargs["defense_skill"], "targeted_magic")
        self.assertTrue(bool(result.data["effect_payload"].get("stunned", False)))
        self.assertTrue(bool(target.db.stunned))

    def test_revelation_reveals_hidden_target(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyHiddenTarget()
        spell = get_spell("revelation")

        result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal", target=target)

        self.assertTrue(result.success)
        self.assertTrue(bool(result.data["effect_payload"].get("revealed", False)))
        self.assertFalse(target.is_hidden())

    def test_revelation_requires_target(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        spell = get_spell("revelation")

        result = SpellEffectService.apply_spell(caster, spell, 12.0, quality="normal", target=None)

        self.assertFalse(result.success)
        self.assertEqual(result.data["reason"], "invalid_target")

    def test_hand_of_tenemlor_routes_fire_damage_to_left_hand(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Cleric", profession="cleric")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        spell = get_spell("hand_of_tenemlor")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["damage_location"], "left_hand")
        self.assertEqual([entry["damage_type"] for entry in result.data["effect_payload"].get("damage_components", [])], ["fire"])
        self.assertLess(target.db.hp, target.db.max_hp)

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

    def test_burden_applies_stat_and_encumbrance_debuffs(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        target.db.stats["strength"] = 20
        spell = get_spell("burden")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="strong", target=target)

        self.assertTrue(result.success)
        self.assertEqual(result.data["effect_payload"]["effect_type"], "burden")
        self.assertLess(target.get_stat("strength"), 20)
        self.assertGreater(target.get_encumbrance_modifier(), 0)

    def test_burden_expires_and_restores_strength_modifier(self):
        caster = DummyCharacter(hp=100, max_hp=100, key="Seer", profession="moon_mage")
        target = DummyCharacter(hp=100, max_hp=100, key="Target", profession="cleric")
        target.db.stats["strength"] = 20
        spell = get_spell("burden")

        result = SpellEffectService.apply_spell(caster, spell, 24.0, quality="normal", target=target)

        self.assertTrue(result.success)
        duration = int(result.data["effect_payload"]["duration"] or 0)
        for _ in range(duration):
            StateService.tick_active_effects(target)
        self.assertEqual(target.get_stat("strength"), 20)
        self.assertEqual(target.get_encumbrance_modifier(), 0)

    def test_registry_marks_seed_spells_canonical_and_prototypes_default(self):
        self.assertEqual(get_spell("burden").canon_status, "canonical")
        self.assertEqual(get_spell("gauge_flow").canon_status, "canonical")
        self.assertEqual(get_spell("strange_arrow").canon_status, "canonical")
        prototype_ids = [spell_id for spell_id, spell in SPELL_REGISTRY.items() if spell.canon_status == "prototype"]
        self.assertIn("flare", prototype_ids)
        self.assertIn("storm_field", prototype_ids)

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