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
        self.caller.list_vendor_inventory()