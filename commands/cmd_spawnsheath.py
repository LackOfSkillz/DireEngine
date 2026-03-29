from evennia import Command
from evennia.utils.create import create_object

from typeclasses.sheaths import BackScabbard, BeltSheath, Sheath


class CmdSpawnSheath(Command):
    """
    Create a practice sheath to wear and use.

    Examples:
      spawnsheath
      spawnsheath belt
      spawnsheath back
      sps generic
    """

    key = "spawnsheath"
    aliases = ["sps"]
    help_category = "Builder"

    def func(self):
        arg = (self.args or "").strip().lower()
        sheath_type = {
            "": (BeltSheath, "belt sheath"),
            "belt": (BeltSheath, "belt sheath"),
            "back": (BackScabbard, "back scabbard"),
            "scabbard": (BackScabbard, "back scabbard"),
            "generic": (Sheath, "leather sheath"),
        }.get(arg)
        if not sheath_type:
            self.caller.msg("Try `spawnsheath belt`, `spawnsheath back`, or `spawnsheath generic`.")
            return

        sheath_cls, key = sheath_type
        sheath = create_object(sheath_cls, key=key, location=self.caller)
        self.caller.msg(f"You create {sheath.key}.")