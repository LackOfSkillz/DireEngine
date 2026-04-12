from commands.command import Command


class CmdAppraise(Command):
    """
    Estimate the value and quality of an item.

    Examples:
        appraise sword
    """

    key = "appraise"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Appraise what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.appraise_target(target)
