from commands.command import Command


class CmdCompanion(Command):
    """
    Call or dismiss your wilderness companion.

    Examples:
        companion
        companion call
        companion dismiss
    """

    key = "companion"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()

        if not args:
            if not hasattr(caller, "get_ranger_companion"):
                caller.msg("You have no companion bond to inspect.")
                return
            companion = caller.get_ranger_companion()
            caller.msg(
                f"Companion: {caller.get_ranger_companion_label()} [{companion.get('state', 'inactive')}] bond {int(companion.get('bond', 0) or 0)}/100"
            )
            return

        if args == "call":
            ok, message = caller.call_ranger_companion() if hasattr(caller, "call_ranger_companion") else (False, "You cannot call a companion.")
            caller.msg(message)
            return

        if args == "dismiss":
            ok, message = caller.dismiss_ranger_companion() if hasattr(caller, "dismiss_ranger_companion") else (False, "You cannot dismiss a companion.")
            caller.msg(message)
            return

        caller.msg("Usage: companion call or companion dismiss")