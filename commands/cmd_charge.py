from evennia import Command


class CmdCharge(Command):
    key = "charge"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.charge_luminar(self.args)