from commands.command import Command
from evennia.utils.create import create_object

from typeclasses.npcs import NPC


class CmdSpawnNPC(Command):
    """
    Create a practice NPC in the room.

    Examples:
      spawnnpc
      spn
    """

    key = "spawnnpc"
    aliases = ["spn"]
    help_category = "Builder"

    def func(self):
        create_object(NPC, key="corl", location=self.caller.location)
        self.caller.msg("You create a practice NPC.")