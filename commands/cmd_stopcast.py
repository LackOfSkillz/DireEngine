from evennia import Command


class CmdStopCast(Command):
    """
    Cancel your current spell preparation or casting.

    Examples:
        stopcast
    """

    key = "stopcast"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        if self.caller.get_state("active_cyclic"):
            self.caller.clear_state("active_cyclic")
            self.caller.msg("You release your sustained spell.")
            return

        self.caller.msg("You are not sustaining a spell.")
