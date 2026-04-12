from commands.command import Command


class CmdPray(Command):
    """
    Offer a prayer for favor or perform a cleric ritual.

    Examples:
        pray
        pray focus
        pray devotion
    """

    key = "pray"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        cleric_ritual_args = {"focus", "devotion", "prayer"}
        if args in cleric_ritual_args and hasattr(caller, "is_profession") and caller.is_profession("cleric"):
            ok, message = caller.perform_cleric_ritual(args) if hasattr(caller, "perform_cleric_ritual") else (False, "You cannot shape that ritual.")
            caller.msg(message)
            return
        if args and args not in {"shrine"}:
            caller.msg("Usage: pray")
            return
        ok, message = caller.pray_for_favor() if hasattr(caller, "pray_for_favor") else (False, "You cannot gather yourself for prayer right now.")
        caller.msg(message)
