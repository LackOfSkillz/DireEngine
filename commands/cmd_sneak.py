from commands.command import Command


class CmdSneak(Command):
    """
    Begin moving stealthily between rooms.

    Examples:
        sneak north
        sneak east
    """

    key = "sneak"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        self.caller.execute_ability_input("sneak")
