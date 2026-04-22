from commands.command import Command


class CmdOffer(Command):
    """
    Make a currency offer on a pending vendor purchase.

    Examples:
        offer 4 silver
        offer 4 silver 25 copper
    """

    key = "offer"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        amount_text = (self.args or "").strip()
        if not amount_text:
            self.caller.msg("Offer how much?")
            return
        self.caller.offer_on_pending_purchase(amount_text)
