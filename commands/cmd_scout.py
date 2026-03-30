import time

from commands.command import Command


class CmdScout(Command):
        """
        Scout the area for visible signs and trails.

        Examples:
            scout
        """

    key = "scout"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("scout", 0) or 0):
            caller.msg("You need a moment before scouting the area again.")
            return

        ok, lines = caller.attempt_ranger_scout() if hasattr(caller, "attempt_ranger_scout") else (False, ["You cannot make sense of the area."])
        for line in lines:
            caller.msg(line)
        cooldowns["scout"] = now + 5
        caller.ndb.cooldowns = cooldowns