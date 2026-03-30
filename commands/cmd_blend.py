import time

from commands.command import Command


class CmdBlend(Command):
    """
    Sink into available cover and strengthen your concealment.

    Examples:
        blend
    """

    key = "blend"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("blend", 0) or 0):
            caller.msg("You need a moment before trying to blend into the terrain again.")
            return

        ok, message = caller.attempt_ranger_blend() if hasattr(caller, "attempt_ranger_blend") else (False, "You cannot blend into the terrain here.")
        caller.msg(message)
        cooldowns["blend"] = now + 4
        caller.ndb.cooldowns = cooldowns