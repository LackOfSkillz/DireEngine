from commands.command import Command


class CmdWithdraw(Command):
    """
    Withdraw coins from your bank account.

    Examples:
        withdraw 50
        withdraw all
    """

    key = "withdraw"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        amount_text = (self.args or "").strip()
        if not amount_text:
            self.caller.msg("Withdraw how much?")
            return
        self.caller.withdraw_coins(amount_text)
