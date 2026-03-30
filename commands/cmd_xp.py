from commands.command import Command


class CmdXP(Command):
    """
    Review unabsorbed experience available for sacrifice.

    Examples:
        xp
    """

    key = "xp"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        amount = caller.get_unabsorbed_xp() if hasattr(caller, "get_unabsorbed_xp") else 0
        caller.msg(f"Unabsorbed Experience: {amount:,}")
