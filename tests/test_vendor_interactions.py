import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_clickvendor import CmdClickVendor
from commands.cmd_shop import CmdShop
from commands.cmd_talk import CmdTalk
from tests.test_vendor_browse import BrowseDummyCharacter, DummyHolder, DummyVendor
from typeclasses.characters import Character
from typeclasses.npcs import NPC


class DummyAliasHandler:
    def __init__(self, *aliases):
        self._aliases = [str(alias) for alias in aliases if str(alias).strip()]

    def all(self):
        return list(self._aliases)


class InteractionVendor(DummyVendor):
    handle_interaction = NPC.handle_interaction
    open_vendor_ui = NPC.open_vendor_ui
    at_object_receive_click = NPC.at_object_receive_click

    def __init__(self):
        super().__init__()
        self.aliases = DummyAliasHandler("armorer", "smith")
        self.db.is_vendor = True
        self.db.is_shopkeeper = True
        self.db.interaction_type = "vendor"


class InteractionNpc:
    handle_interaction = NPC.handle_interaction
    open_vendor_ui = NPC.open_vendor_ui
    at_object_receive_click = NPC.at_object_receive_click

    def __init__(self, npc_id=100, key="Guide", interaction_type="guide"):
        self.id = npc_id
        self.key = key
        self.aliases = DummyAliasHandler(key.lower())
        self.db = DummyHolder()
        self.db.interaction_type = interaction_type
        self.db.is_vendor = False


class DummyLocation:
    def __init__(self, *contents):
        self.contents = list(contents)


class InteractionCharacter(BrowseDummyCharacter):
    _match_interaction_target = Character._match_interaction_target
    open_vendor_ui = Character.open_vendor_ui
    open_interaction_with = Character.open_interaction_with
    get_nearby_vendor = Character.get_nearby_vendor
    is_vendor_target = Character.is_vendor_target
    get_vendor_type = Character.get_vendor_type
    vendor_accepts_item = Character.vendor_accepts_item

    def __init__(self, *occupants):
        super().__init__()
        self.vendor = None
        self.location = DummyLocation(*occupants)


class VendorInteractionTests(unittest.TestCase):
    def test_click_npc_opens_vendor_ui(self):
        vendor = InteractionVendor()
        character = InteractionCharacter(vendor)

        command = CmdClickVendor()
        command.caller = character
        command.args = str(vendor.id)
        command.func()

        self.assertEqual(character.get_vendor_state().get("vendor_id"), vendor.id)
        self.assertIn("looks up as you approach", character.messages[0])
        self.assertIn("Browse Kits", character.messages[-1])

    def test_talk_routes_to_same_vendor_interaction(self):
        vendor = InteractionVendor()
        character = InteractionCharacter(vendor)

        command = CmdTalk()
        command.caller = character
        command.args = "armorer"
        command.func()

        self.assertEqual(character.get_vendor_state().get("vendor_id"), vendor.id)
        self.assertIn("Browse Kits", character.messages[-1])

    def test_shop_vendor_name_opens_vendor_before_browse_selection(self):
        vendor = InteractionVendor()
        character = InteractionCharacter(vendor)

        command = CmdShop()
        command.caller = character
        command.args = "smith"
        command.func()

        self.assertEqual(character.get_vendor_state().get("vendor_id"), vendor.id)
        self.assertIn("Browse Kits", character.messages[-1])

    def test_non_vendor_interaction_does_not_open_shop_ui(self):
        npc = InteractionNpc()
        character = InteractionCharacter(npc)

        command = CmdTalk()
        command.caller = character
        command.args = "guide"
        command.func()

        self.assertEqual(character.messages[-1], "Guide acknowledges you but has nothing to offer yet.")
        self.assertNotIn("Browse Kits", "\n".join(character.messages))
