import time

from commands.command import Command


class CmdReadLand(Command):
    """
    Read the terrain for signs, movement, and favorable ground.

    Examples:
        read land
    """

    key = "read land"
    aliases = ["readland"]
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("read_land", 0) or 0):
            caller.msg("You need a moment before trying to read the land again.")
            return

        ok, lines = caller.attempt_ranger_read_land() if hasattr(caller, "attempt_ranger_read_land") else (False, ["You cannot make sense of the land here."])
        for line in lines:
            caller.msg(line)
        cooldowns["read_land"] = now + 5
        caller.ndb.cooldowns = cooldowns