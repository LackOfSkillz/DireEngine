from evennia import Command


class CmdSwim(Command):
    """
    Swim across a swimmable obstacle or exit.

    Examples:
        swim river
    """

    key = "swim"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.attempt_swim(self.args.strip())
