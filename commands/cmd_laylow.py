from commands.command import Command
from world.systems.justice import process_lay_low


class CmdLayLow(Command):
    """
    Try to reduce heat from the justice system.

    Examples:
        laylow
    """

    key = "laylow"
    aliases = ["lay low"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        result = process_lay_low(caller)
        if not result.get("ok"):
            caller.msg(str(result.get("reason") or "You cannot lay low right now."))
            return
        caller.msg("You keep a low profile and obscure your trail.")
