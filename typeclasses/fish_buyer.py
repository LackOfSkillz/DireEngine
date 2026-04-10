from typeclasses.vendor import Vendor

from world.systems import fishing_economy


class FishBuyer(Vendor):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.vendor_type = "fish_buyer"
        self.db.accepted_item_types = ["fish"]
        self.db.trade_difficulty = 25
        self.db.desc = "A weathered fish buyer with a waxed ledger, a brass hook scale, and a practiced eye for good catches."

    def get_vendor_interaction_lines(self, actor, action="shop"):
        if action != "shop":
            return []
        fish_items = [item for item in list(getattr(actor, "contents", []) or []) if fishing_economy.is_fish_item(item)]
        for item in list(getattr(actor, "contents", []) or []):
            if fishing_economy.is_fish_string(item):
                fish_items.extend([entry for entry in list(getattr(item, "contents", []) or []) if fishing_economy.is_fish_item(entry)])
        if not fish_items:
            return [f"{self.key} says, 'Bring me fish and I'll make it worth your while.'"]
        total_value = sum(fishing_economy.get_fish_sale_value(item) for item in fish_items)
        return [f"{self.key} glances over your catch. 'You've got {len(fish_items)} fish worth about {total_value} coins before any trophy bonus.'"]

    def get_vendor_sale_message(self, actor, item, value):
        return f"{self.key} counts out {actor.format_coins(value)}. {fishing_economy.get_fish_buyer_reaction(item, value)}"
