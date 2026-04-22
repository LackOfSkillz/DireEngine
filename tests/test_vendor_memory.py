import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.test_vendor_barter import BarterDummyCharacter, BarterDummyVendor
from typeclasses.characters import Character
from typeclasses.npcs import NPC
from typeclasses.vendor import Vendor


class MemoryDummyVendor(BarterDummyVendor):
    _get_memory_context = Vendor._get_memory_context
    get_vendor_greeting_lines = Vendor.get_vendor_greeting_lines
    get_vendor_quote_message = Vendor.get_vendor_quote_message
    evaluate_offer = Vendor.evaluate_offer
    get_vendor_purchase_message = Vendor.get_vendor_purchase_message
    open_vendor_ui = NPC.open_vendor_ui

    def __init__(self):
        super().__init__()
        self.db.is_vendor = True
        self.db.is_shopkeeper = True


class MemoryCharacter(BarterDummyCharacter):
    open_vendor_ui = Character.open_vendor_ui
    is_vendor_target = Character.is_vendor_target

    def __init__(self, vendor=None):
        super().__init__()
        if vendor is not None:
            self.vendor = vendor


class VendorMemoryTests(unittest.TestCase):
    def test_vendor_open_tracks_visits_and_changes_greeting(self):
        vendor = MemoryDummyVendor()
        character = MemoryCharacter(vendor)

        self.assertTrue(vendor.open_vendor_ui(character))
        memory = character.get_vendor_memory(vendor)
        self.assertEqual(memory["visits"], 1)
        self.assertIn("Welcome. Take your time.", character.messages)

        character.messages.clear()
        self.assertTrue(vendor.open_vendor_ui(character))
        memory = character.get_vendor_memory(vendor)
        self.assertEqual(memory["visits"], 2)
        self.assertIn("Back again? Let us see what catches your eye today.", character.messages)

    def test_lowball_offers_build_memory_and_change_quote_flavor(self):
        vendor = MemoryDummyVendor()
        character = MemoryCharacter(vendor)

        self.assertTrue(character.buy_item("Average Leather Vest"))
        self.assertFalse(character.offer_on_pending_purchase("10"))
        self.assertFalse(character.offer_on_pending_purchase("10"))
        self.assertFalse(character.offer_on_pending_purchase("10"))

        memory = character.get_vendor_memory(vendor)
        self.assertLess(memory["last_offer_ratio"], 0.8)
        self.assertEqual(memory["lowball_streak"], 3)
        self.assertEqual(character.get_vendor_memory_modifier(vendor), 0.03)

        character.messages.clear()
        self.assertTrue(character.buy_item("Average Chain Robe"))
        self.assertIn("I expect a serious offer this time.", character.messages[-1])

    def test_fair_deal_streak_applies_small_price_bonus_and_quote_flavor(self):
        vendor = MemoryDummyVendor()
        character = MemoryCharacter(vendor)

        baseline_price = character.get_vendor_price(vendor, "Average Chain Robe")
        character.update_vendor_memory(vendor, {"fair_deal_streak": 3})
        discounted_price = character.get_vendor_price(vendor, "Average Chain Robe")

        self.assertLess(discounted_price, baseline_price)
        self.assertEqual(character.get_vendor_memory_modifier(vendor), -0.02)

        character.messages.clear()
        self.assertTrue(character.buy_item("Average Leather Vest"))
        self.assertIn("I will give you a fair price, as always.", character.messages[-1])

    def test_successful_purchase_tracks_last_purchase_type(self):
        vendor = MemoryDummyVendor()
        character = MemoryCharacter(vendor)

        self.assertTrue(character.list_vendor_inventory("kits"))
        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertTrue(character.buy_item("kit"))
        self.assertTrue(character.accept_pending_purchase())

        memory = character.get_vendor_memory(vendor)
        self.assertEqual(memory["last_purchase_type"], "kit")

        character.reset_vendor_state(vendor)
        character.messages.clear()
        self.assertTrue(character.buy_item("Average Chain Robe"))
        self.assertIn("You favored a full set before. I can arrange something similar.", character.messages[-1])
