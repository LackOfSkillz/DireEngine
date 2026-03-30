import time

from commands.command import Command


class CmdFocus(Command):
    """
    Gather a small reserve of natural focus.

    Examples:
        focus
    """

    key = "focus"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("focus", 0) or 0):
            caller.msg("You need a moment before centering yourself again.")
            return
        ok, message = caller.focus_ranger_nature() if hasattr(caller, "focus_ranger_nature") else (False, "You fail to gather any useful focus.")
        caller.msg(message)
        cooldowns["focus"] = now + 4
        caller.ndb.cooldowns = cooldowns