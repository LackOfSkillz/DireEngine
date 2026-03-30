from commands.command import Command


class CmdStabilize(Command):
    """
    Slow a patient's bleeding without directly healing them.

    Examples:
        stabilize jekar
    """

    key = "stabilize"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot do that.")
            return
        if not self.args:
            caller.msg("Stabilize whom?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        ok, message = caller.stabilize_empath_target(target) if hasattr(caller, "stabilize_empath_target") else (False, "You fail to steady their condition.")
        caller.msg(message)
        if ok:
            target.msg("Your bleeding eases as your condition steadies.")