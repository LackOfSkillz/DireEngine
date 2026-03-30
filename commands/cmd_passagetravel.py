import random

from commands.command import Command


class CmdPassageTravel(Command):
    """
    Travel through a discovered passage network.

    Examples:
        passage travel cellar
    """

    key = "passage travel"
    aliases = ["passagetravel"]
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if not getattr(caller.db, "in_passage", False):
            caller.msg("You are not inside a hidden passage.")
            return

        room = getattr(caller, "location", None)
        if not room or not hasattr(room, "get_passage_destinations"):
            caller.db.in_passage = False
            caller.msg("The passage has no clear exit.")
            return

        destinations = room.get_passage_destinations()
        if not destinations:
            caller.db.in_passage = False
            caller.msg("The passage has no clear exit.")
            return

        target_room = random.choice(destinations)
        caller.move_to(target_room, quiet=True, move_type="passage")
        caller.db.in_passage = False
        caller.msg("You emerge from a hidden passage.")
