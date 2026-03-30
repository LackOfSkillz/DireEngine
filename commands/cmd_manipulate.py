from commands.command import Command


class CmdManipulate(Command):
    """
    Calm or influence a living creature without violence.

    Examples:
        manipulate wolf
    """

    key = "manipulate"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to manipulate another mind that way.")
            return
        if not self.args:
            caller.msg("Manipulate whom?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        ok, message = caller.manipulate_empath_target(target) if hasattr(caller, "manipulate_empath_target") else (False, "You fail to bend their emotions.")
        caller.msg(message)