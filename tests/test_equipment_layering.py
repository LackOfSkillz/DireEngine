import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyHolder
from typeclasses.characters import Character, _copy_default_equipment


class DummyWearable:
    def __init__(self, key, *, slot=None, equip_slots=None, layer="base", blocks_layers=None):
        self.key = key
        self.id = 0
        self.location = None
        self.db = DummyHolder()
        self.db.wearable = True
        self.db.slot = slot
        self.db.equip_slots = list(equip_slots or [])
        self.db.layer = layer
        self.db.blocks_layers = list(blocks_layers or [])
        self.db.equipped_slots = []
        self.db.worn_by = None
        self.db.is_sheath = False


class EquipmentDummyCharacter(DummyCharacter):
    get_equipment = Character.get_equipment
    is_multi_slot = Character.is_multi_slot
    get_slot_capacity = Character.get_slot_capacity
    normalize_equipment_slot = Character.normalize_equipment_slot
    get_equipment_layer = Character.get_equipment_layer
    get_equipment_layer_priority = Character.get_equipment_layer_priority
    get_equipment_slots_for_item = Character.get_equipment_slots_for_item
    get_equipment_blocked_layers = Character.get_equipment_blocked_layers
    sort_equipment_stack = Character.sort_equipment_stack
    get_worn_items = Character.get_worn_items
    clear_equipment_item = Character.clear_equipment_item
    equip_item = Character.equip_item
    unequip_item = Character.unequip_item
    ensure_equipment_defaults = Character.ensure_equipment_defaults

    def __init__(self):
        super().__init__(profession="warrior")
        self.contents = []
        self.messages = []
        self.db.equipment = _copy_default_equipment()
        self.db.preferred_sheath = None

    def ensure_core_defaults(self):
        self.ensure_equipment_defaults()

    def sync_client_state(self):
        return None

    def msg(self, text):
        self.messages.append(str(text))


class EquipmentLayeringTests(unittest.TestCase):
    def test_distinct_layers_can_stack_on_same_slot(self):
        character = EquipmentDummyCharacter()
        undershirt = DummyWearable("undershirt", slot="chest", layer="under")
        cloak = DummyWearable("cloak", slot="chest", layer="outer")
        undershirt.location = character
        cloak.location = character

        ok, _message = character.equip_item(undershirt)
        self.assertTrue(ok)
        ok, _message = character.equip_item(cloak)
        self.assertTrue(ok)
        self.assertEqual([item.key for item in character.get_equipment()["chest"]], ["undershirt", "cloak"])

    def test_same_layer_conflict_is_rejected(self):
        character = EquipmentDummyCharacter()
        shirt = DummyWearable("shirt", slot="chest", layer="base")
        cuirass = DummyWearable("cuirass", slot="chest", layer="base")
        shirt.location = character
        cuirass.location = character

        ok, _message = character.equip_item(shirt)
        self.assertTrue(ok)
        ok, message = character.equip_item(cuirass)
        self.assertFalse(ok)
        self.assertIn("already wearing something", message)

    def test_multi_slot_item_equip_and_remove_are_atomic(self):
        character = EquipmentDummyCharacter()
        hauberk = DummyWearable("hauberk", equip_slots=["chest", "arms"], layer="outer")
        hauberk.location = character

        ok, _message = character.equip_item(hauberk)
        self.assertTrue(ok)
        self.assertIn(hauberk, character.get_equipment()["chest"])
        self.assertIn(hauberk, character.get_equipment()["arms"])

        ok, _message = character.unequip_item(hauberk)
        self.assertTrue(ok)
        self.assertNotIn(hauberk, character.get_equipment()["chest"])
        self.assertNotIn(hauberk, character.get_equipment()["arms"])

    def test_legacy_torso_slot_normalizes_to_chest(self):
        character = EquipmentDummyCharacter()
        shirt = DummyWearable("shirt", slot="torso", layer="under")
        shirt.location = character

        ok, _message = character.equip_item(shirt)
        self.assertTrue(ok)
        self.assertIn(shirt, character.get_equipment()["chest"])

    def test_existing_item_blocks_new_item_layer(self):
        character = EquipmentDummyCharacter()
        breastplate = DummyWearable("breastplate", slot="chest", layer="outer", blocks_layers=["under", "base"])
        shirt = DummyWearable("shirt", slot="chest", layer="base")
        breastplate.location = character
        shirt.location = character

        ok, _message = character.equip_item(breastplate)
        self.assertTrue(ok)
        ok, message = character.equip_item(shirt)
        self.assertFalse(ok)
        self.assertIn("cannot be layered", message)

    def test_new_item_blocks_existing_item_layer(self):
        character = EquipmentDummyCharacter()
        undershirt = DummyWearable("undershirt", slot="chest", layer="under")
        breastplate = DummyWearable("breastplate", slot="chest", layer="outer", blocks_layers=["under", "base"])
        undershirt.location = character
        breastplate.location = character

        ok, _message = character.equip_item(undershirt)
        self.assertTrue(ok)
        ok, message = character.equip_item(breastplate)
        self.assertFalse(ok)
        self.assertIn("cannot be layered", message)


if __name__ == "__main__":
    unittest.main()