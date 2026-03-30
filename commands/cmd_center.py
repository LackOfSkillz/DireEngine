from commands.command import Command


class CmdCenter(Command):
    """
    Steady yourself after heavy empathic strain.

    Examples:
        center
    """

    key = "center"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        ok, message = caller.center_empath_self() if hasattr(caller, "center_empath_self") else (False, "You cannot center yourself right now.")
        caller.msg(message)
