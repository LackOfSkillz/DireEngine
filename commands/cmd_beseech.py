import time

from commands.command import Command


class CmdBeseech(Command):
    """
    Call on a nearby aspect of nature for a short-lived blessing.

    Examples:
        beseech wind
        beseech earth
        beseech sky
    """

    key = "beseech"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        if not args:
            caller.msg("Beseech what? Choose wind, earth, or sky.")
            return
        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("beseech", 0) or 0):
            caller.msg("You need a moment before calling on the land again.")
            return
        ok, message = caller.beseech_ranger_aspect(args) if hasattr(caller, "beseech_ranger_aspect") else (False, "There is nothing here to answer your call.")
        caller.msg(message)
        cooldowns["beseech"] = now + 3
        caller.ndb.cooldowns = cooldowns