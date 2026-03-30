from commands.command import Command


class CmdPayFine(Command):
    """
    Pay an outstanding legal fine.

    Examples:
        payfine
    """

    key = "payfine"
    aliases = ["pay fine"]
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "has_unpaid_fine") or not caller.has_unpaid_fine():
            caller.msg("You have no outstanding fines.")
            return

        fine_due = int(getattr(caller.db, "fine_due", 0) or 0)
        coins = int(getattr(caller.db, "coins", 0) or 0)
        if coins < fine_due:
            caller.msg("You do not have enough coin.")
            return

        caller.db.coins = coins - fine_due
        caller.db.fine_due = 0

        items = caller.get_confiscated_items() if hasattr(caller, "get_confiscated_items") else []
        if items:
            from utils.crime import return_confiscated_items

            return_confiscated_items(caller)

        caller.db.confiscated_items = []
        caller.db.collateral_locked = False
        caller.db.fine_due_timestamp = None
        caller.msg("You pay your fine. Your standing is restored.")
