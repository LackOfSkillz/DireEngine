from commands.command import Command


class CmdSacrifice(Command):
    """
    Sacrifice unabsorbed experience at a shrine to gain favor.

    Examples:
        sacrifice 1000
        sacrifice 5000
    """

    key = "sacrifice"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Usage: sacrifice <amount>")
            return
        ok, lines = caller.sacrifice_for_favor(args) if hasattr(caller, "sacrifice_for_favor") else (False, ["You cannot make that offering right now."])
        for line in lines if isinstance(lines, list) else [str(lines)]:
            caller.msg(line)
