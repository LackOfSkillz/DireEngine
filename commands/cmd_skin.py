from evennia import Command


class CmdSkin(Command):
    key = "skin"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Skin what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.skin_target(target)