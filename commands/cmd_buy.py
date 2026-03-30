from evennia import Command


class CmdBuy(Command):
        """
        Purchase an item from a nearby shop or vendor.

        Examples:
            buy bread
        """

    key = "buy"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        item_name = (self.args or "").strip()
        if not item_name:
            self.caller.msg("Buy what?")
            return

        self.caller.buy_item(item_name)