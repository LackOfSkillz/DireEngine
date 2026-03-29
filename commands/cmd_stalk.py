from evennia import Command


class CmdStalk(Command):
    key = "stalk"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        if not self.args:
            self.caller.msg("Stalk whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.use_ability("stalk", target=target)