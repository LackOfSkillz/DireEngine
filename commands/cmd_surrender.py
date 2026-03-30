from commands.command import Command

from utils.crime import call_guards


class CmdSurrender(Command):
    """
    Yield the fight and stop resisting.

    Examples:
        surrender
    """

    key = "surrender"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_criminal") or not caller.is_criminal():
            caller.msg("You are not wanted.")
            return

        caller.db.surrendered = True
        call_guards(caller.location, caller)
        caller.msg("You surrender yourself to the authorities.")
