from evennia import Command


class CmdSell(Command):
    key = "sell"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Sell what?")
            return

        self.caller.sell_item(self.args.strip())