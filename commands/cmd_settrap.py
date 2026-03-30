from evennia import Command


class CmdSetTrap(Command):
    """
    Place a trap from a prepared device.

    Examples:
        settrap box
    """

    key = "settrap"
    aliases = ["set trap"]
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.deploy_trap()
