from commands.command import Command


class CmdHarness(Command):
    """
    Harness raw mana into a held pool.

    Examples:
        harness 10
    """

    key = "harness"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.harness_spell(self.args)