import os
import unittest
from unittest.mock import patch

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from domain.combat.resolution import AttackResolution
from engine.services.combat_service import CombatService
from engine.services.result import ActionResult
from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyHolder
from typeclasses.characters import Character
from typeclasses.corpse import Corpse
from typeclasses.rooms import Room


class DummyWeapon:
    def __init__(self, key="shortbow"):
        self.key = key
        self.db = DummyHolder()
        self.db.item_type = "weapon"
        self.db.is_ranged = True
        self.db.weapon_range_type = "bow"
        self.db.ammo_type = "arrow"
        self.db.skill = "short_bow"
        self.db.ammo_loaded = False


class DummyAmmoItem:
    def __init__(self, key="Practice shortbow arrows", *, world_id="practice_shortbow_arrows", quantity=1, ammo_type="arrow", ammo_class="short_bow", tier="average"):
        self.key = key
        self.db = DummyHolder()
        self.db.item_type = "ammunition"
        self.db.world_id = world_id
        self.db.quantity = quantity
        self.db.ammo_type = ammo_type
        self.db.ammo_class = ammo_class
        self.db.tier = tier
        self.deleted = False

    def delete(self):
        self.deleted = True


class DummyQuiverItem:
    def __init__(self, key="hunting quiver"):
        self.key = key
        self.db = DummyHolder()
        self.db.item_type = "container"
        self.db.type = "ammo_container"
        self.db.functional_type = "quiver"
        self.db.ammo_container = True
        self.db.ammo_type = "arrow"
        self.db.capacity = 30
        self.db.quickdraw_bonus = 0.05
        self.db.slot = "back"
        self.db.equip_slots = ["back"]
        self.db.layer = "accessory"
        self.db.blocks_layers = []
        self.db.tier = "average"
        self.db.contents = [
            {
                "item_id": "practice_shortbow_arrows",
                "quantity": 10,
                "ammo_type": "arrow",
                "ammo_class": "short_bow",
                "tier": "average",
                "name": "Practice shortbow arrows",
            }
        ]


class DummyRoom:
    get_loose_ammo = Room.get_loose_ammo
    set_loose_ammo = Room.set_loose_ammo
    add_loose_ammo = Room.add_loose_ammo
    get_loose_ammo_display_lines = Room.get_loose_ammo_display_lines

    def __init__(self):
        self.db = DummyHolder()
        self.db.loose_ammo = []
        self.contents = []

    def msg_contents(self, *_args, **_kwargs):
        return None


class DummyCorpse:
    get_ammo_inventory = Corpse.get_ammo_inventory
    set_ammo_inventory = Corpse.set_ammo_inventory
    add_ammo_stacks = Corpse.add_ammo_stacks
    spill_ammo_to_room = Corpse.spill_ammo_to_room

    def __init__(self, location=None):
        self.db = DummyHolder()
        self.db.ammo_inventory = []
        self.location = location


class AmmoDummyCharacter(DummyCharacter):
    get_visible_carried_items = Character.get_visible_carried_items
    get_equipment = Character.get_equipment
    get_equipped_items_by_slot = Character.get_equipped_items_by_slot
    get_equipment_layer = Character.get_equipment_layer
    get_equipment_layer_priority = Character.get_equipment_layer_priority
    _get_tier_rank = Character._get_tier_rank
    _get_quiver_tier_rank = Character._get_quiver_tier_rank
    _set_quiver_ammo = Character._set_quiver_ammo
    _migrate_legacy_quiver_state = Character._migrate_legacy_quiver_state
    get_equipped_quiver = Character.get_equipped_quiver
    get_quiver_ammo = Character.get_quiver_ammo
    get_quiver_capacity = Character.get_quiver_capacity
    get_quiver_supported_ammo_type = Character.get_quiver_supported_ammo_type
    store_ammo_in_quiver = Character.store_ammo_in_quiver
    consume_quiver_ammo = Character.consume_quiver_ammo
    get_quiver = Character.get_quiver
    set_quiver = Character.set_quiver
    get_quiver_display_line = Character.get_quiver_display_line
    get_loaded_ammo = Character.get_loaded_ammo
    set_loaded_ammo = Character.set_loaded_ammo
    get_ammo_inventory = Character.get_ammo_inventory
    set_ammo_inventory = Character.set_ammo_inventory
    get_embedded_ammo = Character.get_embedded_ammo
    set_embedded_ammo = Character.set_embedded_ammo
    add_embedded_ammo = Character.add_embedded_ammo
    receive_ammo_stacks = Character.receive_ammo_stacks
    get_held_ammo_items = Character.get_held_ammo_items
    get_ammo_stack_from_item = Character.get_ammo_stack_from_item
    is_ammo_compatible_with_weapon = Character.is_ammo_compatible_with_weapon
    consume_held_ammo_item = Character.consume_held_ammo_item
    resolve_loadable_ammo = Character.resolve_loadable_ammo
    has_ranged_weapon_equipped = Character.has_ranged_weapon_equipped
    get_equipped_ranged_weapon = Character.get_equipped_ranged_weapon
    get_equipped_ammo_state = Character.get_equipped_ammo_state
    load_ranged_weapon = Character.load_ranged_weapon
    consume_loaded_ammo = Character.consume_loaded_ammo

    def __init__(self, key="ranger"):
        super().__init__(profession="ranger")
        self.key = key
        self.messages = []
        self.contents = []
        self.weapon = DummyWeapon()
        self.quiver = DummyQuiverItem()
        self.contents.append(self.weapon)
        self.contents.append(self.quiver)
        self.location = None
        self.db.equipment = {"back": [self.quiver]}
        self.db.loaded_ammo = None
        self.db.ammo_inventory = []
        self.db.embedded_ammo = []

    def ensure_core_defaults(self):
        if not hasattr(self.db, "equipment"):
            self.db.equipment = {"back": [self.quiver]}
        if not hasattr(self.db, "loaded_ammo"):
            self.db.loaded_ammo = None
        if not hasattr(self.db, "ammo_inventory"):
            self.db.ammo_inventory = []
        if not hasattr(self.db, "embedded_ammo"):
            self.db.embedded_ammo = []

    def get_wielded_weapon(self):
        return self.weapon

    def get_weapon(self):
        return self.weapon

    def search(self, query, candidates=None, location=None):
        pool = list(candidates or getattr(location, "contents", []) or self.contents)
        lowered = str(query or "").strip().lower()
        for obj in pool:
            if lowered in str(getattr(obj, "key", "") or "").strip().lower():
                return obj
        return None

    def sync_client_state(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def add_held_ammo(self, ammo_item):
        self.contents.append(ammo_item)
        return ammo_item


class AmmoDepletionTests(unittest.TestCase):
    def test_load_ammo_consumes_one_from_quiver(self):
        attacker = AmmoDummyCharacter()

        ok, message = attacker.load_ranged_weapon()

        self.assertTrue(ok)
        self.assertIn("load", message.lower())
        self.assertEqual(attacker.get_quiver()["quantity"], 9)
        self.assertEqual(attacker.get_loaded_ammo()["quantity"], 1)

    def test_load_rejects_when_already_loaded(self):
        attacker = AmmoDummyCharacter()
        ok, _message = attacker.load_ranged_weapon()
        self.assertTrue(ok)

        ok, message = attacker.load_ranged_weapon()

        self.assertFalse(ok)
        self.assertIn("already loaded", message)

    def test_load_prefers_held_ammo_over_quiver(self):
        attacker = AmmoDummyCharacter()
        held = attacker.add_held_ammo(DummyAmmoItem(quantity=1))

        ok, _message = attacker.load_ranged_weapon()

        self.assertTrue(ok)
        self.assertEqual(attacker.get_quiver()["quantity"], 10)
        self.assertEqual(attacker.get_loaded_ammo()["item_id"], "practice_shortbow_arrows")
        self.assertTrue(held.deleted)

    def test_load_uses_quiver_when_no_held_ammo(self):
        attacker = AmmoDummyCharacter()

        ok, _message = attacker.load_ranged_weapon()

        self.assertTrue(ok)
        self.assertEqual(attacker.get_quiver()["quantity"], 9)
        self.assertEqual(attacker.get_loaded_ammo()["quantity"], 1)

    def test_load_fails_when_neither_held_nor_quiver_has_compatible_ammo(self):
        attacker = AmmoDummyCharacter()
        attacker.db.equipment = {}

        ok, message = attacker.load_ranged_weapon()

        self.assertFalse(ok)
        self.assertIn("no quiver equipped", message)

    def test_special_held_ammo_overrides_quiver(self):
        attacker = AmmoDummyCharacter()
        attacker.add_held_ammo(
            DummyAmmoItem(
                key="Fire arrow",
                world_id="fire_arrow",
                quantity=1,
                ammo_type="arrow",
                ammo_class="short_bow",
                tier="epic",
            )
        )

        ok, _message = attacker.load_ranged_weapon()

        self.assertTrue(ok)
        self.assertEqual(attacker.get_quiver()["quantity"], 10)
        self.assertEqual(attacker.get_loaded_ammo()["item_id"], "fire_arrow")
        self.assertEqual(attacker.get_loaded_ammo()["tier"], "epic")

    def test_quiver_display_line_reads_equipped_item_state(self):
        attacker = AmmoDummyCharacter()

        self.assertEqual(attacker.get_quiver_display_line(), "Quiver (10 Practice shortbow arrows)")

        attacker.load_ranged_weapon()

        self.assertEqual(attacker.get_quiver_display_line(), "Quiver (9 Practice shortbow arrows)")

    def test_ranged_attack_hit_embeds_ammo(self):
        room = DummyRoom()
        attacker = AmmoDummyCharacter(key="attacker")
        target = AmmoDummyCharacter(key="target")
        attacker.location = room
        target.location = room
        room.contents = [attacker, target]
        ok, _message = attacker.load_ranged_weapon()
        self.assertTrue(ok)

        with patch.object(CombatService, "_validate_attack", return_value=None), patch.object(CombatService, "_prepare_attack", return_value=ActionResult.ok(data={"outcome": "ready"})), patch.object(CombatService, "_build_context", return_value={"is_ranged_weapon": True, "fatigue_cost": 0, "ambush": False, "current_range": "near"}), patch("engine.services.combat_service.resolve_attack", side_effect=lambda _a, _t, context=None: AttackResolution(hit=True, damage=1, roundtime=1, details=dict(context or {}))), patch.object(CombatService, "_apply_post_resolution_state", return_value=None), patch("engine.services.combat_service.StateService.apply_damage", return_value=ActionResult.ok(data={"amount": 1, "injury_events": []})), patch("engine.services.combat_service.CombatXP.award"), patch("engine.services.combat_service.StateService.apply_fatigue"), patch("engine.services.combat_service.StateService.apply_roundtime"):
            result = CombatService.attack(attacker, target)

        self.assertTrue(result.success)
        self.assertIsNone(attacker.get_loaded_ammo())
        self.assertEqual(attacker.get_quiver()["quantity"], 9)
        self.assertEqual(target.get_embedded_ammo()[0]["quantity"], 1)
        self.assertEqual(room.get_loose_ammo(), [])

    def test_ranged_attack_miss_drops_ammo_to_room(self):
        room = DummyRoom()
        attacker = AmmoDummyCharacter(key="attacker")
        target = AmmoDummyCharacter(key="target")
        attacker.location = room
        target.location = room
        room.contents = [attacker, target]
        ok, _message = attacker.load_ranged_weapon()
        self.assertTrue(ok)

        with patch.object(CombatService, "_validate_attack", return_value=None), patch.object(CombatService, "_prepare_attack", return_value=ActionResult.ok(data={"outcome": "ready"})), patch.object(CombatService, "_build_context", return_value={"is_ranged_weapon": True, "fatigue_cost": 0, "ambush": False, "current_range": "near"}), patch("engine.services.combat_service.resolve_attack", side_effect=lambda _a, _t, context=None: AttackResolution(hit=False, damage=0, roundtime=1, details=dict(context or {}))), patch.object(CombatService, "_apply_post_resolution_state", return_value=None), patch("engine.services.combat_service.CombatXP.award"), patch("engine.services.combat_service.StateService.apply_fatigue"), patch("engine.services.combat_service.StateService.apply_roundtime"):
            result = CombatService.attack(attacker, target)

        self.assertTrue(result.success)
        self.assertIsNone(attacker.get_loaded_ammo())
        self.assertEqual(attacker.get_quiver()["quantity"], 9)
        self.assertEqual(room.get_loose_ammo()[0]["quantity"], 1)
        self.assertEqual(target.get_embedded_ammo(), [])

    def test_killing_hit_moves_ammo_to_corpse(self):
        room = DummyRoom()
        corpse = DummyCorpse(location=room)
        target = AmmoDummyCharacter(key="target")
        target.location = room
        target.get_death_corpse = lambda: corpse

        CombatService._resolve_ranged_ammo_outcome(
            None,
            target,
            {
                "ammo": {
                    "item_id": "practice_shortbow_arrows",
                    "quantity": 1,
                    "ammo_type": "arrow",
                    "ammo_class": "short_bow",
                    "tier": "average",
                    "name": "Practice shortbow arrows",
                },
                "outcome": "kill",
            },
            True,
        )

        self.assertEqual(corpse.get_ammo_inventory()[0]["quantity"], 1)
        self.assertEqual(room.get_loose_ammo(), [])

    def test_corpse_decay_spills_ammo_to_room(self):
        room = DummyRoom()
        corpse = DummyCorpse(location=room)
        corpse.add_ammo_stacks(
            [
                {
                    "item_id": "practice_shortbow_arrows",
                    "quantity": 2,
                    "ammo_type": "arrow",
                    "ammo_class": "short_bow",
                    "tier": "average",
                    "name": "Practice shortbow arrows",
                }
            ]
        )

        spilled = corpse.spill_ammo_to_room()

        self.assertEqual(spilled[0]["quantity"], 2)
        self.assertEqual(room.get_loose_ammo()[0]["quantity"], 2)
        self.assertEqual(corpse.get_ammo_inventory(), [])


if __name__ == "__main__":
    unittest.main()