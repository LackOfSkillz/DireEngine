from commands.command import Command


class CmdPray(Command):
    """
    Offer a prayer at a shrine.

    Examples:
        pray shrine
    """

    key = "pray"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        if args != "shrine":
            caller.msg("Usage: pray shrine")
            return
        ok, message = caller.pray_at_shrine() if hasattr(caller, "pray_at_shrine") else (False, "You feel no divine presence here.")
        caller.msg(message)
