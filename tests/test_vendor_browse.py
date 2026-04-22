import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from tests.services.test_structured_spell_pipeline import DummyCharacter, DummyHolder
from typeclasses.characters import Character


class DummyVendor:
    def __init__(self):
        self.id = 99
        self.key = "Armorer"
        self.db = DummyHolder()
        self.db.vendor_profile_id = "ranger_armor_vendor"
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


class GeneralGoodsDummyVendor:
    def __init__(self):
        self.id = 100
        self.key = "Outfitter"
        self.db = DummyHolder()
        self.db.vendor_profile_id = "general_goods_vendor"
        self.db.inventory = [
            {"display_name": "Starter Pack", "item_id": "starter_pack", "price": 9, "category": "container", "utility_category": "containers", "functional_type": "pack"},
            {"display_name": "Coil of Rope", "item_id": "coil_of_rope", "price": 5, "category": "misc", "utility_category": "tools", "functional_type": "rope"},
            {"display_name": "River Fishing Pole", "item_id": "river_fishing_pole", "price": 18, "category": "misc", "utility_category": "fishing", "functional_type": "fishing_pole"},
            {"display_name": "Miner's Pick", "item_id": "miners_pick", "price": 20, "category": "misc", "utility_category": "mining", "functional_type": "mining_tool"},
        ]
        self.db.inventory_entry_map = {entry["display_name"].lower(): dict(entry) for entry in self.db.inventory}
        self.db.price_map = {entry["display_name"].lower(): entry["price"] for entry in self.db.inventory}

    def generate_stock(self, **_kwargs):
        return False


class BrowseDummyCharacter(DummyCharacter):
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
    _get_vendor_memory_store = Character._get_vendor_memory_store
    get_reputation = Character.get_reputation
    adjust_reputation = Character.adjust_reputation
    _get_vendor_offer_streak_store = Character._get_vendor_offer_streak_store
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
        self.vendor = DummyVendor()
        self.db.vendor_state = None
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


class GeneralGoodsBrowseDummyCharacter(BrowseDummyCharacter):
    def __init__(self):
        super().__init__()
        self.vendor = GeneralGoodsDummyVendor()


class VendorBrowseTests(unittest.TestCase):
    def test_shop_navigation_persists_and_buy_uses_filtered_index(self):
        character = BrowseDummyCharacter()

        self.assertTrue(character.list_vendor_inventory())
        self.assertIn("Browse Kits", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("inventory"))
        self.assertIn("Leather Armor", character.messages[-1])
        self.assertLess(character.messages[-1].find("Leather Armor"), character.messages[-1].find("Chain Armor"))
        self.assertNotIn("(3)", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertEqual(character.db.vendor_state["filters"], {"armor_class": "leather_armor"})
        self.assertIn("Chest", character.messages[-1])
        self.assertNotIn("(2)", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("chest"))
        self.assertEqual(
            character.db.vendor_state["filters"],
            {"armor_class": "leather_armor", "armor_slot": "chest"},
        )
        self.assertIn("Below Average Leather Vest", character.messages[-1])
        self.assertIn("Average Leather Vest", character.messages[-1])

        self.assertTrue(character.buy_item("2"))
        self.assertEqual(character.get_pending_purchase()["label"], "Average Leather Vest")
        self.assertEqual(character.coins, 100)

        self.assertTrue(character.accept_pending_purchase())
        self.assertEqual(character.purchased[-1], "leather_vest")
        self.assertEqual(character.coins, 75)

        self.assertTrue(character.list_vendor_inventory("back"))
        self.assertEqual(character.db.vendor_state["filters"], {"armor_class": "leather_armor"})
        self.assertIn("Use 'shop <number>' or 'shop <slot>' to view items.", character.messages[-1])

    def test_shop_can_browse_kits_as_grouped_sets(self):
        character = BrowseDummyCharacter()

        self.assertTrue(character.list_vendor_inventory("kits"))
        self.assertIn("Ranger Leathers Set", character.messages[-1])
        self.assertNotIn("(3)", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("1"))
        self.assertEqual(character.db.vendor_state["filters"], {"kit_id": "ranger_leathers"})
        self.assertIn("Chest: Below Average Leather Vest", character.messages[-1])
        self.assertIn("Legs: Above Average Hide Pants", character.messages[-1])

        self.assertTrue(character.buy_item("kit"))
        self.assertEqual(character.get_pending_purchase()["kind"], "kit")

    def test_shop_groups_general_goods_by_utility_section(self):
        character = GeneralGoodsBrowseDummyCharacter()

        self.assertTrue(character.list_vendor_inventory())
        self.assertIn("General Goods", character.messages[-1])
        self.assertIn("Containers", character.messages[-1])
        self.assertIn("Fishing", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("fishing"))
        self.assertEqual(character.db.vendor_state["filters"], {"utility_category": "fishing"})
        self.assertIn("River Fishing Pole", character.messages[-1])
        self.assertNotIn("Starter Pack", character.messages[-1])

        self.assertTrue(character.list_vendor_inventory("back"))
        self.assertEqual(character.db.vendor_state["filters"], {})
        self.assertIn("Tools", character.messages[-1])
