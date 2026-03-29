from evennia import Command


class CmdRework(Command):
    key = "rework"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.rework_trap()