from commands.command import Command


class CmdBalance(Command):
    """
    Check how many coins you carry and how many are in the bank.

    Examples:
        balance
    """

    key = "balance"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        self.caller.show_bank_balance()
