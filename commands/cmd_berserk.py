from commands.command import Command
from engine.services.berserk_service import BerserkService


class CmdBerserk(Command):
    """
        Enter the canonical Barbarian berserk.

    Examples:
            berserk
    """

    key = "berserk"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("barbarian"):
            caller.msg("You do not have the facilities to properly channel your rage.")
            return

        args = str(self.args or "").strip().lower()
        if not args:
            result = BerserkService.berserk(caller)
            for message in list(result.messages or []):
                caller.msg(message)
            for error in list(result.errors or []):
                caller.msg(error)
            return

        caller.msg("Currently there's only one Berserk available to Barbarians, and it's learned automatically at 2nd level.")
        if args not in {"berserk", "fury", "rage"}:
            caller.msg("Use BERSERK with no modifier for the canonical Barbarian berserk.")
            return

        result = BerserkService.berserk(caller)
        for message in list(result.messages or []):
            caller.msg(message)
        for error in list(result.errors or []):
            caller.msg(error)