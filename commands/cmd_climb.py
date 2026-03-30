from evennia import Command


class CmdClimb(Command):
        """
        Climb a marked obstacle or exit.

        Examples:
            climb wall
            climb ladder
        """

    key = "climb"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.attempt_climb(self.args.strip())