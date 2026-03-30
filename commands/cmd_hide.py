from evennia import Command


class CmdHide(Command):
        """
        Attempt to hide from view.

        Examples:
            hide
        """

    key = "hide"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        self.caller.execute_ability_input("hide")