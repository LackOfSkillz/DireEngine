import time

from commands.command import Command


class CmdHunt(Command):
        """
        Scan nearby rooms for signs of living prey.

        Examples:
            hunt
        """

    key = "hunt"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("hunt", 0) or 0):
            caller.msg("You need a moment before scanning the area again.")
            return

        ok, lines = caller.attempt_ranger_hunt() if hasattr(caller, "attempt_ranger_hunt") else (False, ["You cannot make sense of the local signs of life."])
        for line in lines:
            caller.msg(line)
        cooldowns["hunt"] = now + 5
        caller.ndb.cooldowns = cooldowns