from commands.command import Command


class CmdPray(Command):
    """
    Offer a prayer at a shrine or perform a cleric ritual.

    Examples:
        pray
        pray focus
        pray devotion
        pray shrine
    """

    key = "pray"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        if args == "shrine":
            ok, message = caller.pray_at_shrine() if hasattr(caller, "pray_at_shrine") else (False, "You feel no divine presence here.")
            caller.msg(message)
            return
        if hasattr(caller, "is_profession") and caller.is_profession("cleric"):
            ritual = args or "prayer"
            ok, message = caller.perform_cleric_ritual(ritual) if hasattr(caller, "perform_cleric_ritual") else (False, "You cannot shape that ritual.")
            caller.msg(message)
            return
        caller.msg("Usage: pray shrine")
