from evennia import Command


class CmdClimb(Command):
    key = "climb"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.attempt_climb(self.args.strip())