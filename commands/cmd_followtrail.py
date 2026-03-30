import time

from commands.command import Command


class CmdFollowTrail(Command):
    """
    Follow a visible trail into the next room.

    Examples:
        followtrail wolf
        follow trail wolf
    """

    key = "followtrail"
    aliases = ["follow trail"]
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Follow whose trail?")
            return

        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("followtrail", 0) or 0):
            caller.msg("You need a moment before trying to follow another trail.")
            return

        ok, message = caller.attempt_ranger_follow_trail(args) if hasattr(caller, "attempt_ranger_follow_trail") else (False, "You cannot follow that trail.")
        caller.msg(message)
        cooldowns["followtrail"] = now + 3
        caller.ndb.cooldowns = cooldowns
