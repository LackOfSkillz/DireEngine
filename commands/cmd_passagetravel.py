from commands.command import Command
from world.systems.theft import move_through_passage


class CmdPassageTravel(Command):
    """
    Travel through a discovered passage network.

    Examples:
        passage
    """

    key = "passage"
    aliases = ["passage travel", "passagetravel"]
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        room = getattr(caller, "location", None)
        if not room:
            caller.msg("You find no hidden route here.")
            return

        success, outcome = move_through_passage(caller, room)
        if not success:
            caller.msg(str(outcome))
            return
        caller.msg("You emerge from a hidden passage.")
        caller.apply_thief_roundtime(2)
