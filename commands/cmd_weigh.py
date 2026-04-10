from commands.command import Command


class CmdWeigh(Command):
    """
    Weigh a fish at a nearby weigh station.

    Examples:
        weigh trout
    """

    key = "weigh"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        target_name = (self.args or "").strip()
        if not target_name:
            self.caller.msg("Weigh what?")
            return
        self.caller.weigh_fish(target_name)