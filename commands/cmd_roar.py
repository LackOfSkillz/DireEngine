from commands.command import Command
from engine.services.roar_service import RoarService


class CmdRoar(Command):
    """
        Use a canonical Barbarian roar.

    Examples:
      roar
            roar kuniyo
            roar everild
    """

    key = "roar"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        result = RoarService.invoke(caller, args or None)
        for message in list(result.messages or []):
            caller.msg(message)
        for error in list(result.errors or []):
            caller.msg(error)