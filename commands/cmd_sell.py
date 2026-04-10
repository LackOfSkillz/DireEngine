from commands.command import Command


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
        lowered = args.lower()
        if " to " in lowered:
            item_name, _separator, _vendor_name = args.rpartition(" to ")
            if str(item_name or "").strip():
                args = str(item_name).strip()
                lowered = args.lower()
            else:
                self.caller.msg("Try 'sell <item>'.")
                return
        if lowered == "all":
            self.caller.sell_all_items()
            return
        if lowered == "fish":
            self.caller.sell_all_fish()
            return
        self.caller.sell_item(args)
