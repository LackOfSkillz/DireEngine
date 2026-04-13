from commands.command import Command


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
        active_cyclic = self.caller.get_active_cyclic_effects() if hasattr(self.caller, "get_active_cyclic_effects") else {}
        if active_cyclic:
            if hasattr(self.caller, "stop_cyclic_spell"):
                self.caller.stop_cyclic_spell()
            self.caller.msg("You release your sustained spell.")
            return

        self.caller.msg("You are not sustaining a spell.")
