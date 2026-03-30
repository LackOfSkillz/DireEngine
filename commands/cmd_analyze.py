from evennia import Command


class CmdAnalyze(Command):
    """
    Study the current room for useful fieldcraft details.

    Examples:
        analyze
    """

    key = "analyze"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Analyze what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not getattr(target.db, "is_box", False):
            self.caller.msg("You can't analyze that.")
            return

        self.caller.analyze_trap(target)