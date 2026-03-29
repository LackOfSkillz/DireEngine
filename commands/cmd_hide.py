from evennia import Command


class CmdHide(Command):
    key = "hide"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        self.caller.use_ability("hide")