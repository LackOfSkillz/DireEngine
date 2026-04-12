from commands.command import Command


class CmdUnhide(Command):
    """
    Stop hiding and reveal yourself.

    Examples:
      unhide
      reveal
    """

    key = "unhide"
    aliases = ["reveal"]
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        if not any((caller.is_hidden(), caller.is_sneaking(), caller.is_stalking(), caller.is_ambushing())):
            caller.msg("You are not hiding.")
            return

      # IMPORTANT: Do not clear roundtime here.
      # Roundtime represents action recovery, not stealth state.
        caller.break_stealth()
        caller.msg("You step out of hiding.")