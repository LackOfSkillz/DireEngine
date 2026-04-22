import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyHolder
from typeclasses.characters import Character
from typeclasses.vendor import Vendor


class BarterDummyVendor:
    _get_tone = Vendor._get_tone
    _get_dialogue = Vendor._get_dialogue
    _get_memory_context = Vendor._get_memory_context
    get_vendor_quote_message = Vendor.get_vendor_quote_message
    evaluate_offer = Vendor.evaluate_offer
    get_vendor_purchase_message = Vendor.get_vendor_purchase_message

    def __init__(self):
        self.id = 99
        self.key = "Armorer"
        self.db = DummyHolder()
        self.db.snobbishness = 0.25
        self.db.inventory = [
            {"display_name": "Below Average Leather Vest", "item_id": "leather_vest", "price": 18, "tier": "below_average", "category": "armor", "armor_class": "leather_armor", "armor_slot": "chest", "kit_id": "ranger_leathers", "kit_name": "Ranger Leathers Set"},
            {"display_name": "Average Leather Vest", "item_id": "leather_vest", "price": 25, "tier": "average", "category": "armor", "armor_class": "leather_armor", "armor_slot": "chest", "kit_id": "ranger_leathers", "kit_name": "Ranger Leathers Set"},
            {"display_name": "Above Average Hide Pants", "item_id": "hide_pants", "price": 29, "tier": "above_average", "category": "armor", "armor_class": "leather_armor", "armor_slot": "legs", "kit_id": "ranger_leathers", "kit_name": "Ranger Leathers Set"},
            {"display_name": "Average Chain Robe", "item_id": "chain_robe", "price": 35, "tier": "average", "category": "armor", "armor_class": "chain_armor", "armor_slot": "chest"},
        ]
        self.db.inventory_entry_map = {entry["display_name"].lower(): dict(entry) for entry in self.db.inventory}
        self.db.price_map = {entry["display_name"].lower(): entry["price"] for entry in self.db.inventory}

    def generate_stock(self, **_kwargs):
        return False


class BarterDummyCharacter(DummyCharacter):
    _default_vendor_state = Character._default_vendor_state
    get_vendor_state = Character.get_vendor_state
    reset_vendor_state = Character.reset_vendor_state
    _label_vendor_armor_class = Character._label_vendor_armor_class
    _label_vendor_armor_slot = Character._label_vendor_armor_slot
    _label_vendor_kit = Character._label_vendor_kit
    _armor_class_sort_key = Character._armor_class_sort_key
    _armor_slot_sort_key = Character._armor_slot_sort_key
    format_vendor_click = Character.format_vendor_click
    parse_coin_amount = Character.parse_coin_amount
    get_active_transaction = Character.get_active_transaction
    get_vendor_inventory_catalog = Character.get_vendor_inventory_catalog
    get_vendor_inventory_entries = Character.get_vendor_inventory_entries
    _resolve_vendor_menu_option = Character._resolve_vendor_menu_option
    _derive_vendor_utility_category = Character._derive_vendor_utility_category
    _label_vendor_utility_category = Character._label_vendor_utility_category
    _vendor_utility_category_sort_key = Character._vendor_utility_category_sort_key
    get_vendor_browse_menu = Character.get_vendor_browse_menu
    get_pending_purchase = Character.get_pending_purchase
    clear_pending_purchase = Character.clear_pending_purchase
    _store_pending_purchase = Character._store_pending_purchase
    _build_pending_purchase = Character._build_pending_purchase
    _validate_pending_purchase = Character._validate_pending_purchase
    _get_selected_kit_entries = Character._get_selected_kit_entries
    _find_vendor_catalog_entry = Character._find_vendor_catalog_entry
    get_equipment_layer = Character.get_equipment_layer
    get_equipment_layer_priority = Character.get_equipment_layer_priority
    _normalize_armor_compare_class = Character._normalize_armor_compare_class
    _get_tier_rank = Character._get_tier_rank
    get_item_stats = Character.get_item_stats
    compare_items = Character.compare_items
    compare_kit = Character.compare_kit
    _format_comparison_delta = Character._format_comparison_delta
    _get_vendor_entry_comparison_lines = Character._get_vendor_entry_comparison_lines
    _get_vendor_kit_comparison_lines = Character._get_vendor_kit_comparison_lines
    get_equipped_items_by_slot = Character.get_equipped_items_by_slot
    get_top_layer_item = Character.get_top_layer_item
    _get_vendor_reputation_key = Character._get_vendor_reputation_key
    _get_vendor_reputation_store = Character._get_vendor_reputation_store
    _get_vendor_offer_streak_store = Character._get_vendor_offer_streak_store
    _get_vendor_memory_store = Character._get_vendor_memory_store
    get_reputation = Character.get_reputation
    adjust_reputation = Character.adjust_reputation
    get_vendor_offer_streak = Character.get_vendor_offer_streak
    set_vendor_offer_streak = Character.set_vendor_offer_streak
    get_vendor_memory = Character.get_vendor_memory
    update_vendor_memory = Character.update_vendor_memory
    record_vendor_visit = Character.record_vendor_visit
    record_vendor_offer = Character.record_vendor_offer
    record_vendor_purchase = Character.record_vendor_purchase
    get_effective_vendor_reputation = Character.get_effective_vendor_reputation
    get_vendor_reputation_modifier = Character.get_vendor_reputation_modifier
    get_vendor_memory_modifier = Character.get_vendor_memory_modifier
    get_vendor_kit_modifier = Character.get_vendor_kit_modifier
    apply_discount_pipeline = Character.apply_discount_pipeline
    is_full_kit_purchase = Character.is_full_kit_purchase
    calculate_kit_price = Character.calculate_kit_price
    get_vendor_base_price = Character.get_vendor_base_price
    split_numbered_query = Character.split_numbered_query
    resolve_vendor_inventory_entry = Character.resolve_vendor_inventory_entry
    msg_vendor_matches = Character.msg_vendor_matches
    list_vendor_inventory = Character.list_vendor_inventory
    accept_pending_purchase = Character.accept_pending_purchase
    offer_on_pending_purchase = Character.offer_on_pending_purchase
    buy_item = Character.buy_item
    get_vendor_price = Character.get_vendor_price

    def __init__(self):
        super().__init__(profession="ranger")
        self.vendor = BarterDummyVendor()
        self.db.vendor_state = None
        self.db.pending_purchase = None
        self.db.equipment = {}
        self.messages = []
        self.coins = 100
        self.purchased = []

    def get_nearby_vendor(self, item=None):
        _item = item
        return self.vendor

    def can_trade_with(self, vendor):
        _vendor = vendor
        return True, ""

    def get_equipment(self):
        return dict(getattr(self.db, "equipment", {}) or {})

    def _resolve_pending_vendor(self, pending):
        if int((pending or {}).get("vendor_id", 0) or 0) == self.vendor.id:
            return self.vendor
        return None

    def msg(self, text):
        self.messages.append(str(text))

    def format_coins(self, amount):
        return f"{int(amount)} coins"

    def has_coins(self, amount):
        return self.coins >= int(amount)

    def remove_coins(self, amount):
        self.coins -= int(amount)

    def create_vendor_inventory_item(self, item_name, vendor=None):
        _vendor = vendor
        self.purchased.append(str(item_name))
        return True

    def use_skill(self, *_args, **_kwargs):
        return None


class VendorBarterTests(unittest.TestCase):
    def test_buy_creates_quote_offer_counters_and_accept_completes(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        pending = character.get_pending_purchase()
        self.assertEqual(pending["label"], "Average Leather Vest")
        self.assertEqual(pending["price"], 25)
        self.assertIn("timestamp", pending)
        self.assertIn("Use 'accept'", character.messages[-1])

        self.assertTrue(character.offer_on_pending_purchase("2 silver 2 copper"))
        pending = character.get_pending_purchase()
        self.assertEqual(pending["price"], 24)
        self.assertIn("24 coins", character.messages[-2])

        self.assertTrue(character.accept_pending_purchase())
        self.assertEqual(character.purchased, ["leather_vest"])
        self.assertEqual(character.coins, 76)
        self.assertIsNone(character.get_pending_purchase())

    def test_low_offer_is_rejected_and_keeps_pending_purchase(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        self.assertFalse(character.offer_on_pending_purchase("10"))
        self.assertEqual(character.get_pending_purchase()["price"], 25)
        self.assertIn("25 coins", character.messages[-1])

    def test_new_buy_replaces_existing_pending_quote(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        first_pending = character.get_pending_purchase()
        self.assertEqual(first_pending["label"], "Average Leather Vest")

        self.assertTrue(character.buy_item("Average Chain Robe"))
        replaced_pending = character.get_pending_purchase()
        self.assertEqual(replaced_pending["label"], "Average Chain Robe")
        self.assertIn("set aside the previous quote", character.messages[-2].lower())

    def test_stale_pending_quote_is_rejected_and_cleared(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        character.vendor.db.inventory_entry_map.pop("average leather vest", None)

        self.assertFalse(character.offer_on_pending_purchase("24"))
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("gone stale", character.messages[-1].lower())

        self.assertTrue(character.buy_item("Average Chain Robe"))
        character.vendor.db.inventory_entry_map.pop("average chain robe", None)

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("gone stale", character.messages[-1].lower())

    def test_expired_pending_quote_fails_and_clears(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        pending = character.get_pending_purchase()
        pending["timestamp"] -= 121
        character._store_pending_purchase(pending)

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("no longer valid", character.messages[-1].lower())

    def test_price_drift_invalidates_pending_quote(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        character.vendor.db.price_map["average leather vest"] = 31

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("price has changed", character.messages[-1].lower())

    def test_tier_drift_invalidates_pending_quote(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        character.vendor.db.inventory_entry_map["average leather vest"]["tier"] = "above_average"

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("stock has changed", character.messages[-1].lower())

    def test_kit_validation_is_atomic_when_one_entry_drifts(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.list_vendor_inventory("kits"))
        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertTrue(character.buy_item("kit"))
        character.vendor.db.inventory_entry_map["above average hide pants"]["price"] = 35
        character.vendor.db.price_map["above average hide pants"] = 35

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertEqual(character.purchased, [])
        self.assertIn("price has changed", character.messages[-1].lower())

    def test_cross_vendor_state_invalidates_pending_quote(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        other_vendor = BarterDummyVendor()
        other_vendor.id = 100
        other_vendor.key = "Different Armorer"
        character.vendor = other_vendor

        self.assertFalse(character.accept_pending_purchase())
        self.assertIsNone(character.get_pending_purchase())
        self.assertIn("no longer here", character.messages[-1].lower())

    def test_double_accept_fails_after_transaction_is_cleared(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.buy_item("Average Leather Vest"))
        self.assertTrue(character.accept_pending_purchase())
        self.assertFalse(character.accept_pending_purchase())
        self.assertIn("do not have a pending purchase", character.messages[-1].lower())

    def test_reputation_clamps_and_adjusts_price(self):
        character = BarterDummyCharacter()

        self.assertEqual(character.get_reputation(character.vendor), 0.0)
        self.assertEqual(character.adjust_reputation(character.vendor, 2.0), 1.0)
        discounted_price = character.get_vendor_price(character.vendor, "Average Leather Vest")
        self.assertEqual(character.adjust_reputation(character.vendor, -3.0), -1.0)
        inflated_price = character.get_vendor_price(character.vendor, "Average Leather Vest")
        self.assertLess(discounted_price, inflated_price)

    def test_reputation_changes_offer_thresholds(self):
        character = BarterDummyCharacter()

        self.assertEqual(character.adjust_reputation(character.vendor, 1.0), 1.0)
        high_rep_result = character.vendor.evaluate_offer(character, {"listed_price": 25, "label": "Average Leather Vest"}, 21)
        self.assertEqual(high_rep_result["status"], "counter")

        self.assertEqual(character.adjust_reputation(character.vendor, -2.0), -1.0)
        low_rep_result = character.vendor.evaluate_offer(character, {"listed_price": 25, "label": "Average Leather Vest"}, 21)
        self.assertEqual(low_rep_result["status"], "rejected")

    def test_high_snobbish_vendor_gives_smaller_kit_discount_and_stiffer_flavor(self):
        character = BarterDummyCharacter()
        character.vendor.db.snobbishness = 0.9

        self.assertTrue(character.list_vendor_inventory("kits"))
        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertTrue(character.buy_item("kit"))

        pending = character.get_pending_purchase()
        self.assertEqual(pending["base_total"], 73)
        self.assertEqual(pending["quoted_total"], character.calculate_kit_price(pending, character.vendor))
        self.assertLess(pending["quoted_total"], pending["base_total"])
        self.assertIn("i don't usually discount", character.messages[-1].lower())

    def test_buy_kit_accept_delivers_every_item_in_selection(self):
        character = BarterDummyCharacter()

        self.assertTrue(character.list_vendor_inventory("kits"))
        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertTrue(character.buy_item("kit"))

        pending = character.get_pending_purchase()
        self.assertEqual(pending["kind"], "kit")
        self.assertTrue(character.is_full_kit_purchase(pending))
        self.assertEqual(pending["item_count"], 3)
        self.assertEqual(pending["base_total"], 72)
        self.assertEqual(pending["quoted_total"], 68)
        self.assertEqual(pending["price"], 68)
        self.assertIn("make it worth your while", character.messages[-1].lower())
        self.assertIn("modest reduction", character.messages[-1].lower())

        self.assertTrue(character.accept_pending_purchase())
        self.assertEqual(
            character.purchased,
            ["leather_vest", "leather_vest", "hide_pants"],
        )
        self.assertEqual(character.coins, 32)
