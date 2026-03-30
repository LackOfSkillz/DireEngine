from evennia import Command


class CmdCharge(Command):
        """
        Charge power into a prepared spell.

        Examples:
            charge
            charge 5
        """

    key = "charge"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        self.caller.charge_luminar(self.args)