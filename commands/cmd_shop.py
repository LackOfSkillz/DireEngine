from commands.command import Command


class CmdShop(Command):
    """
    See what a nearby vendor is selling.

    Examples:
        shop
        list
    """

    key = "shop"
    aliases = ["list", "browse"]
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        args = (self.args or "").strip()
        if args and self.caller.open_interaction_with(args, preferred_type="vendor", silent=True):
            return
        self.caller.list_vendor_inventory(self.args)