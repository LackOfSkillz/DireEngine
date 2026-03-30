from commands.command import Command


class CmdPurge(Command):
    """
    Force poison or disease out of your own body.

    Examples:
        purge poison
        purge disease
    """

    key = "purge"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot do that.")
            return
        if not self.args:
            caller.msg("Purge what? Use 'purge poison' or 'purge disease'.")
            return
        ok, message = caller.purge_empath_condition(self.args.strip()) if hasattr(caller, "purge_empath_condition") else (False, "You fail to purge the corruption.")
        caller.msg(message)