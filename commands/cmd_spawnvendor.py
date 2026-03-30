from evennia import Command
from evennia.utils.create import create_object

from typeclasses.vendor import Vendor


class CmdSpawnVendor(Command):
        """
        Spawn a test vendor in the current room.

        Examples:
            spawnvendor
        """

    key = "spawnvendor"
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Builder"

    def func(self):
        vendor = create_object(Vendor, key="merchant", location=self.caller.location)
        vendor.db.inventory = ["lockpick", "trap kit", "book"]
        self.caller.msg("You create a practice vendor.")