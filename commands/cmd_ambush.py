from evennia import Command


class CmdAmbush(Command):
    """
    Prepare a hidden ambush against a target.

    Examples:
        ambush goblin
    """

    key = "ambush"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        if not self.args:
            self.caller.msg("Ambush whom?")
            return

        self.caller.execute_ability_input("ambush", target_name=self.args.strip())
