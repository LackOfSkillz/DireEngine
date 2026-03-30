from commands.command import Command


class CmdDeposit(Command):
    """
    Deposit coins into your bank account.

    Examples:
        deposit 50
        deposit all
    """

    key = "deposit"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        amount_text = (self.args or "").strip()
        if not amount_text:
            self.caller.msg("Deposit how much?")
            return
        self.caller.deposit_coins(amount_text)
