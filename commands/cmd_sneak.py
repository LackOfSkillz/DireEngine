from evennia import Command


class CmdSneak(Command):
    key = "sneak"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        self.caller.execute_ability_input("sneak")