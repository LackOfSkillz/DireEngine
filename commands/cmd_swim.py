from evennia import Command


class CmdSwim(Command):
    key = "swim"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.attempt_swim(self.args.strip())