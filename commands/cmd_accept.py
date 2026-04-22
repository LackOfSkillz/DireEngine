from commands.command import Command


class CmdAccept(Command):
    """
    Accept a pending vendor offer.

    Examples:
        accept
    """

    key = "accept"
    aliases = ["confirm"]
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        self.caller.accept_pending_purchase()
