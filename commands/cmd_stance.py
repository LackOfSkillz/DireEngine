from commands.command import Command


class CmdStance(Command):
    """
    Check or adjust how aggressive your combat stance is.

    Examples:
      stance
      stance 70
    """

    key = "stance"
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to adjust your stance.")
            self.caller.consume_stun()
            return

        if not self.args:
            stance = self.caller.db.stance or {"offense": 50, "defense": 50}
            self.caller.msg(f"Your stance is {stance['offense']} offense and {stance['defense']} defense.")
            return

        try:
            value = int(self.args.strip())
        except ValueError:
            self.caller.msg("Choose an offense value from 0 to 100, like stance 70.")
            return

        value = max(0, min(100, value))
        self.caller.set_stance(offense=value, defense=100 - value)
        self.caller.msg(f"You shift to {value} offense and {100 - value} defense.")