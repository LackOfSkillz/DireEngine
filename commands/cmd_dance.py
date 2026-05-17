from commands.command import Command
from engine.services.dance_service import DanceService


class CmdDance(Command):
    """
        Use a canonical Barbarian battle dance.

    Examples:
      dance
      dance swan
      dance off
    """

    key = "dance"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        result = DanceService.end_dance(caller) if args == "off" else DanceService.begin_dance(caller, args or None)
        for message in list(result.messages or []):
            caller.msg(message)
        for error in list(result.errors or []):
            caller.msg(error)