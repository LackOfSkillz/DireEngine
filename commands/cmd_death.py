from commands.command import Command


class CmdDeath(Command):
    """
    Review your current death-state penalties and recovery anchors.

    Examples:
        death
    """

    key = "death"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "get_death_status_lines"):
            caller.msg("You feel wholly untouched by death.")
            return

        lines = caller.get_death_status_lines()
        if not lines:
            caller.msg("You are free of Death's Sting and carry no grave burden here.")
            return

        caller.msg("\n".join(lines))