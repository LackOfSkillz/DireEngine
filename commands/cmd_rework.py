from evennia import Command


class CmdRework(Command):
    """
    Rework an existing trap or crafted setup.

    Examples:
        rework trap
    """

    key = "rework"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        self.caller.rework_trap()
