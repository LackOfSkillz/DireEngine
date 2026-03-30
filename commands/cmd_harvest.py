from evennia import Command


class CmdHarvest(Command):
    """
    Harvest a usable resource from the current room.

    Examples:
        harvest
        harvest herb
    """

    key = "harvest"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Harvest what?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        if not getattr(target.db, "is_box", False):
            self.caller.msg("You can't harvest that.")
            return

        self.caller.harvest_trap(target)
