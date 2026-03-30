from evennia import Command


class CmdStalk(Command):
        """
        Begin quietly following a target.

        Examples:
            stalk goblin
        """

    key = "stalk"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        if not self.args:
            self.caller.msg("Stalk whom?")
            return

        self.caller.execute_ability_input("stalk", target_name=self.args.strip())