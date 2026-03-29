from evennia import Command


class CmdDisarm(Command):
    key = "disarm"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Disarm what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not self.caller.is_box_target(target):
            self.caller.msg("You can't disarm that.")
            return

        self.caller.disarm_box(target)