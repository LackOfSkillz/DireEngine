from evennia import Command


class CmdAmbush(Command):
    key = "ambush"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        if not self.args:
            self.caller.msg("Ambush whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.use_ability("ambush", target=target)