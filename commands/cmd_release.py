from commands.command import Command


class CmdRelease(Command):
    """
    Release your active empathic link.

    Examples:
        release
    """

    key = "release"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if hasattr(caller, "remove_empath_link") and caller.remove_empath_link():
            caller.msg("You release your connection.")
            return
        caller.msg("You are not maintaining a connection.")
