from commands.command import Command
from world.systems.justice import pay_fine


class CmdPayFine(Command):
    """
    Pay an outstanding legal fine.

    Examples:
        payfine
        payfine 50
    """

    key = "payfine"
    aliases = ["pay fine"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        amount_text = str(self.args or "").strip()
        amount = None
        if amount_text:
            try:
                amount = int(amount_text)
            except ValueError:
                caller.msg("Usage: payfine <amount>")
                return

        result = pay_fine(caller, amount=amount)
        if not result.get("ok"):
            caller.msg(str(result.get("reason") or "You cannot pay your fine right now."))
            return

        caller.msg(
            f"You pay {int(result.get('paid', 0) or 0)} silver to the authorities. "
            f"Remaining debt: {int(result.get('remaining', 0) or 0)} silver."
        )
