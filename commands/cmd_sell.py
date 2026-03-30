from evennia import Command


class CmdSell(Command):
    """
    Sell an item to a nearby vendor.

    Examples:
        sell gem
    """

    key = "sell"
    aliases = ["vend"]
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Sell what?")
            return

        args = self.args.strip()
        if args.lower() == "all":
            self.caller.sell_all_items()
            return
        self.caller.sell_item(args)
