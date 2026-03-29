from evennia import Command


class CmdUnwield(Command):
    """
    Lower the weapon you are currently wielding.

    Examples:
      unwield
      unw
    """

    key = "unwield"
    aliases = ["unw"]
    help_category = "Equipment"

    def func(self):
        weapon = self.caller.get_weapon()
        if not weapon:
            self.caller.msg("You are not wielding anything right now.")
            return

        self.caller.clear_equipped_weapon()
        self.caller.msg(f"You stop wielding {weapon.key}.")