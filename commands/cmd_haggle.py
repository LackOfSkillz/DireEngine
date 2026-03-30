from evennia import Command


class CmdHaggle(Command):
        """
        Try to negotiate a better shop price.

        Examples:
            haggle sword
        """

    key = "haggle"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Haggle with whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.haggle_with(target)