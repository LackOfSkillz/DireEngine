from commands.command import Command


class CmdMend(Command):
    """
    Mend your own transferred wounds.

    Examples:
        mend self
    """

    key = "mend"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        if args not in {"", "self", "me"}:
            caller.msg("For now you can only 'mend self'.")
            return
        ok, message = caller.mend_empath_self() if hasattr(caller, "mend_empath_self") else (False, "You cannot mend yourself.")
        caller.msg(message)