from evennia.utils.create import create_object

from typeclasses.npcs import NPC

from world.systems.fishing import mark_borrowed_item
from world.systems import fishing_economy


class FishingSupplier(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "Old Maren"
        self.db.desc = (
            "An older woman with weathered hands and a patient expression. "
            "She keeps a patient eye on the pond while a tidy spread of poles, hooks, dressed fish, and empty baskets rests beside her scale."
        )
        self.db.is_fishing_supplier = True
        self.db.is_fish_buyer = True
        self.db.is_vendor = True
        self.db.vendor_type = "fish_buyer"
        self.db.accepted_item_types = ["fish", "fish_meat", "fish_skin", "junk"]
        self.db.trade_difficulty = 20
        self.db.trophy_sale_bonus_multiplier = 1.25
        self.db.default_inquiry_response = "Ask for gear if you need a starter kit."
        for alias in ["maren", "old maren", "supplier", "fish buyer"]:
            self.aliases.add(alias)

    def _find_actor_item(self, actor, *, flag_name=None, key=None):
        if actor is None:
            return None
        target_key = str(key or "").strip().lower()
        for item in list(getattr(actor, "contents", []) or []):
            if flag_name and bool(getattr(getattr(item, "db", None), flag_name, False)):
                return item
            if target_key and str(getattr(item, "key", "") or "").strip().lower() == target_key:
                return item
        return None

    def _create_missing_gear(self, actor):
        created = []

        pole = self._find_actor_item(actor, flag_name="is_fishing_pole")
        if pole is None:
            pole = create_object("typeclasses.items.fishing_pole.FishingPole", key="fishing pole", location=actor, home=actor)
            mark_borrowed_item(pole)
            created.append(pole)

        bait = self._find_actor_item(actor, flag_name="is_bait")
        if bait is None:
            bait = create_object("typeclasses.items.bait.Bait", key="worm", location=actor, home=actor)
            bait.db.is_bait = True
            bait.db.bait_family = "worm_cutbait"
            bait.db.bait_type = "worm_cutbait"
            bait.aliases.add("bait")
            mark_borrowed_item(bait)
            created.append(bait)

        hook = self._find_actor_item(actor, flag_name="is_hook")
        if hook is None:
            hook = create_object("typeclasses.objects.Object", key="hook", location=actor, home=actor)
            hook.db.is_hook = True
            hook.db.hook_rating = 10
            hook.db.weight = 0.1
            hook.db.item_type = "fishing_gear"
            hook.db.desc = "A simple barbed hook sized for starter fishing work."
            mark_borrowed_item(hook)
            created.append(hook)

        line = self._find_actor_item(actor, flag_name="is_line")
        if line is None:
            line = create_object("typeclasses.objects.Object", key="line", location=actor, home=actor)
            line.db.is_line = True
            line.db.line_rating = 10
            line.db.weight = 0.1
            line.db.item_type = "fishing_gear"
            line.db.desc = "A coiled starter line, already waxed and ready to tie off."
            mark_borrowed_item(line)
            created.append(line)

        fish_string = self._find_actor_item(actor, flag_name="is_fish_string")
        if fish_string is None:
            fish_string = create_object("typeclasses.items.fish_string.FishString", key="fish string", location=actor, home=actor)
            mark_borrowed_item(fish_string)
            created.append(fish_string)

        return created

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if normalized in {"gear", "kit", "starter gear", "starter kit", "fishing gear"}:
            created = self._create_missing_gear(actor)
            if created:
                actor.msg("Old Maren stoops beside her baskets, sorts out the basics in practiced order, and presses them into your hands one piece at a time.")
            if any(bool(getattr(getattr(item, "db", None), "is_fish_string", False)) for item in created):
                actor.msg("Thread your catch onto this if you plan to keep fishing.")
            if created:
                ordered_items = sorted((str(getattr(item, "key", "gear") or "gear") for item in created), key=lambda entry: (0 if entry == "fishing pole" else 1, entry))
                item_names = ", ".join(ordered_items)
                return f"Start with the pole, then mind your bait. I've set you up with {item_names}."
            return "You already have the basics. Use what you're carrying before you come asking for more."
        return super().handle_inquiry(actor, topic)

    def get_vendor_interaction_lines(self, actor, action="shop"):
        if str(action or "shop").strip().lower() != "shop":
            return []
        fish_items = [item for item in list(getattr(actor, "contents", []) or []) if fishing_economy.is_fish_trade_item(item)]
        for item in list(getattr(actor, "contents", []) or []):
            if fishing_economy.is_fish_string(item):
                fish_items.extend([entry for entry in list(getattr(item, "contents", []) or []) if fishing_economy.is_fish_trade_item(entry)])
        if not fish_items:
            return [f"{self.key} says, 'Bring me fish, cleaned cuts, river salvage, or ask for gear if you need to start from scratch.'"]
        total_value = sum(fishing_economy.get_fish_vendor_sale_value(item, vendor=self) for item in fish_items)
        return [f"{self.key} eyes your catch. 'You've got {len(fish_items)} fishing finds worth about {total_value} coins by my reckoning.'"]

    def get_vendor_sale_message(self, actor, item, value):
        return f"{self.key} counts out {actor.format_coins(value)}. {fishing_economy.get_fish_buyer_reaction(item, value, vendor=self)}"