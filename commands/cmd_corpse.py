from commands.command import Command


class CmdCorpse(Command):
    """
    Review the state of your corpse while you are dead.

    Examples:
        corpse
    """

    key = "corpse"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_dead") or not caller.is_dead():
            caller.msg("You are not dead.")
            return
        if not hasattr(caller, "get_corpse_status_lines"):
            caller.msg("You cannot sense your corpse from here.")
            return

        caller.msg("\n".join(caller.get_corpse_status_lines()))