from evennia import Command


class CmdPrepare(Command):
        """
        Prepare a spell before charging or casting it.

        Examples:
            prepare ignite
        """

    key = "prepare"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.prepare_spell(self.args)