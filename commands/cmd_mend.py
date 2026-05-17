from commands.command import Command
from engine.services.wound_transfer_service import WoundTransferService


class CmdMend(Command):
    """
    Mend your own transferred wounds.

    Examples:
        mend self
    """

    key = "mend"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        if args not in {"", "self", "me"}:
            caller.msg("For now you can only 'mend self'.")
            return
        result = WoundTransferService.mend_self(caller)
        caller.msg((result.messages or result.errors)[0])