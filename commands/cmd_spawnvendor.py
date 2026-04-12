from commands.command import Command
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
        vendor_type = str(self.args or "").strip().lower() or "general"
        if vendor_type not in {"general", "gem_buyer", "pawn"}:
            self.caller.msg("Vendor type must be general, gem_buyer, or pawn.")
            return
        vendor = create_object(Vendor, key="merchant", location=self.caller.location)
        vendor.db.vendor_type = vendor_type
        vendor.db.inventory = ["lockpick", "trap kit", "book", "gem pouch"] if vendor_type == "general" else []
        self.caller.msg(f"You create a practice {vendor_type} vendor.")
