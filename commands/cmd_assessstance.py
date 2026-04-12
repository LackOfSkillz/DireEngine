from commands.command import Command


class CmdAssessStance(Command):
    """
    Review what your current stance settings mean in combat.

    Examples:
        assessstance
    """

    key = "assessstance"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Assess whose stance?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.assess_stance(target)
