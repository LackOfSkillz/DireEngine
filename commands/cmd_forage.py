from evennia import Command


class CmdForage(Command):
    key = "forage"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.execute_ability_input("forage")