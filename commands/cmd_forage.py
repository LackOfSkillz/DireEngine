from evennia import Command


class CmdForage(Command):
    key = "forage"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.use_ability("forage")