from commands.command import Command


class CmdUnlock(Command):
    """
    Attempt to unlock a loot box.

    Examples:
        unlock box
    """

    key = "unlock"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Unlock what?")
            return
        target = caller.search(self.args.strip())
        if not target:
            return
        if not hasattr(caller, "unlock_box"):
            caller.msg("You cannot unlock that.")
            return
        caller.unlock_box(target)