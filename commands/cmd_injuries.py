from evennia import Command


class CmdInjuries(Command):
    """
    Review your wounds and see where you are bleeding.

    Examples:
      injuries
      wounds
      bleeding
    """

    key = "injuries"
    aliases = ["bleeding", "wounds", "inj"]
    help_category = "Character"

    def func(self):
        injury_lines = self.caller.get_injury_display_lines(looker=self.caller)
        if injury_lines:
            self.caller.msg("Injuries:")
            for line in injury_lines:
                self.caller.msg(f"  {line}")
        else:
            self.caller.msg("Injuries: none")