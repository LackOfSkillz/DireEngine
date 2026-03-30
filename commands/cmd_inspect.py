from evennia import Command


class CmdInspect(Command):
    """
    Inspect an item or object more closely.

    Examples:
        inspect sword
        inspect chest
    """

    key = "inspect"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Inspect what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not self.caller.is_box_target(target):
            self.caller.msg("You see nothing special.")
            return

        self.caller.inspect_box(target)
