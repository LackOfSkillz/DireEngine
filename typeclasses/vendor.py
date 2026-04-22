from evennia.utils import logger

from server.systems.vendor_profiles import generate_vendor_stock, get_vendor_profile
from typeclasses.npcs import NPC


class Vendor(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.interaction_type = "vendor"
        self.db.is_vendor = True
        self.db.is_shopkeeper = True
        self.db.vendor_type = "general"
        self.db.vendor_profile_id = None
        self.db.accepted_item_types = []
        self.db.trade_difficulty = 20
        self.db.inventory = []
        self.db.inventory_entry_map = {}
        self.db.price_map = {}
        self.db.shop_heat = 0
        self.db.shop_heat_updated_at = 0
        self.db.theft_attempt_log = {}
        self.db.snobbishness = 0.5
        self.db.desc = "A trader with an eye for useful goods and a sharper eye for prices."

    def _get_tone(self, mood="neutral", reputation=0.0):
        snobbishness = float(getattr(getattr(self, "db", None), "snobbishness", 0.5) or 0.5)
        if reputation >= 0.4:
            return "friendly"
        if reputation <= -0.4:
            return "insulted"
        if mood == "insulted":
            return "friendly" if snobbishness < 0.35 else "insulted"
        if mood == "accepted":
            return "friendly" if snobbishness < 0.5 else "neutral"
        return "neutral" if snobbishness < 0.7 else "insulted"

    def _get_dialogue(self, mood="neutral", reputation=0.0):
        tone = self._get_tone(mood, reputation=reputation)
        pools = {
            "friendly": {
                "quote": "Ahh, excellent selection. {item} is {price}.",
                "accepted": "A fair offer. We have a deal at {price}.",
                "counter": "Close enough. Make it {price} and it is yours.",
                "rejected": "That is too lean an offer for {item}.",
            },
            "neutral": {
                "quote": "{item} will cost you {price}.",
                "accepted": "Very well. I will let it go for {price}.",
                "counter": "I might consider {price}, but not less.",
                "rejected": "No. {price} or something nearer it.",
            },
            "insulted": {
                "quote": "{item} is {price}. Try not to waste my time.",
                "accepted": "Fine. {price}, and be done with it.",
                "counter": "You are wasting my time. {price} is my answer.",
                "rejected": "Insulting. Come back when you can make a serious offer.",
            },
        }
        return pools.get(tone, pools["neutral"])

    def _get_memory_context(self, caller):
        if caller and hasattr(caller, "get_vendor_memory"):
            memory = caller.get_vendor_memory(self)
            if isinstance(memory, dict):
                return memory
        return {
            "visits": 0,
            "last_visit": 0,
            "last_purchase_type": None,
            "last_offer_ratio": 0.0,
            "lowball_streak": 0,
            "fair_deal_streak": 0,
        }

    def get_vendor_greeting_lines(self, caller):
        memory = self._get_memory_context(caller)
        visits = int(memory.get("visits", 0) or 0)
        lowball_streak = int(memory.get("lowball_streak", 0) or 0)
        fair_deal_streak = int(memory.get("fair_deal_streak", 0) or 0)
        last_purchase_type = memory.get("last_purchase_type")

        if lowball_streak >= 3:
            return ["Back again? Let us skip the unrealistic offers this time."]
        if fair_deal_streak >= 3:
            return ["Always a pleasure. You have a good eye and a fair sense for a deal."]
        if visits <= 1:
            return ["Welcome. Take your time."]
        if last_purchase_type == "kit":
            return ["Back again? If you are after another full set, I can lay one out properly."]
        return ["Back again? Let us see what catches your eye today."]

    def get_vendor_quote_message(self, caller, purchase):
        reputation = float(caller.get_reputation(self) if hasattr(caller, "get_reputation") else 0.0)
        snobbishness = float(getattr(getattr(self, "db", None), "snobbishness", 0.5) or 0.5)
        memory = self._get_memory_context(caller)
        lines = []
        dialogue = self._get_dialogue("neutral", reputation=reputation)
        item_label = str(purchase.get("label") or "that")
        price_label = str(purchase.get("price_label") or "0 copper")
        lines.append(dialogue["quote"].format(item=item_label, price=price_label))
        if int(memory.get("fair_deal_streak", 0) or 0) >= 3:
            lines.append("I will give you a fair price, as always.")
        elif int(memory.get("lowball_streak", 0) or 0) >= 3:
            lines.append("I expect a serious offer this time.")
        elif memory.get("last_purchase_type") == "kit":
            lines.append("You favored a full set before. I can arrange something similar.")
        if purchase.get("source") == "kit":
            if snobbishness <= 0.35:
                lines.append("Take the whole set and I'll make it worth your while.")
            elif snobbishness >= 0.65:
                lines.append("I don't usually discount... but for a full set, perhaps.")
            else:
                lines.append("A fine eye. I can offer you a better price for the full set.")
            lines.append(f"The full set comes to {price_label}... a modest reduction.")
        if reputation >= 0.4:
            lines.append("Always a pleasure doing business with you.")
        elif reputation <= -0.4:
            lines.append("I'm not inclined to trust your offers.")
        lines.append("Use 'accept' to purchase, or 'offer <amount>' to make a counter-offer.")
        return "\n".join(lines)

    def evaluate_offer(self, caller, purchase, offer_amount):
        quoted_price = max(0, int(purchase.get("quoted_total", purchase.get("price", purchase.get("listed_price", 0))) or 0))
        if quoted_price <= 0:
            return {"status": "rejected", "response": "There is nothing to negotiate."}
        offer_amount = max(0, int(offer_amount or 0))
        snobbishness = float(getattr(getattr(self, "db", None), "snobbishness", 0.5) or 0.5)
        reputation = float(caller.get_reputation(self) if hasattr(caller, "get_reputation") else 0.0)
        min_accept = max(1, int(round(quoted_price * (0.85 + snobbishness * 0.10 - reputation * 0.05))))
        counter_floor = max(min_accept, int(round(quoted_price * (0.93 + snobbishness * 0.04))))
        lowball_threshold = max(1, int(round(quoted_price * 0.6)))
        if offer_amount >= quoted_price:
            response = self._get_dialogue("accepted", reputation=reputation)["accepted"].format(price=caller.format_coins(offer_amount))
            return {"status": "accepted", "agreed_price": offer_amount, "response": response}
        if offer_amount >= min_accept:
            counter_price = max(offer_amount, counter_floor)
            response = self._get_dialogue("counter", reputation=reputation)["counter"].format(price=caller.format_coins(counter_price))
            return {"status": "counter", "agreed_price": counter_price, "response": response}
        response = self._get_dialogue("rejected", reputation=reputation)["rejected"].format(item=purchase.get("label") or "that", price=caller.format_coins(quoted_price))
        return {"status": "rejected", "response": response, "lowball": offer_amount <= lowball_threshold}

    def get_vendor_purchase_message(self, caller, stock_name, price):
        reputation = float(caller.get_reputation(self) if hasattr(caller, "get_reputation") else 0.0)
        message = self._get_dialogue("accepted", reputation=reputation)["accepted"].format(price=caller.format_coins(price))
        if reputation >= 0.4:
            message += " Always a pleasure doing business with you."
        elif reputation <= -0.4:
            message += " Even so, coin spends the same."
        return message + f" You purchase {stock_name}."

    def generate_stock(self, *, force=False, rng=None):
        profile_id = str(getattr(self.db, "vendor_profile_id", "") or "").strip()
        if not profile_id:
            return False
        if not force and getattr(self.db, "inventory", None):
            return False
        profile = get_vendor_profile(profile_id)
        generated = generate_vendor_stock(profile, rng=rng)
        self.db.snobbishness = float(profile.get("snobbishness", getattr(self.db, "snobbishness", 0.5)) or 0.5)
        self.db.inventory = list(generated["inventory"])
        self.db.price_map = dict(generated["price_map"])
        self.db.inventory_entry_map = dict(generated["inventory_entry_map"])
        self.ndb.stock = list(generated["item_ids"])
        logger.log_info(f"[VendorGen] {profile_id} -> {len(generated['inventory'])} items generated")
        return True