from evennia import Command


class CmdOpen(Command):
    """
    Open a container, door, or similar object.

    Examples:
        open chest
        open door
    """

    key = "open"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Open what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not self.caller.is_box_target(target):
            self.caller.msg("You can't open that.")
            return

        self.caller.open_box(target)
