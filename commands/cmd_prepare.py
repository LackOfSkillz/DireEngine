from evennia import Command


class CmdPrepare(Command):
    key = "prepare"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.prepare_spell(self.args)