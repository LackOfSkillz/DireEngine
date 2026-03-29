from evennia import Command


class CmdSneak(Command):
    key = "sneak"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        self.caller.use_ability("sneak")