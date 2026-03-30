import random
import time

from commands.command import Command


class CmdTrack(Command):
    """
    Track a bounty target or follow a ranger trail.

    Examples:
        track outlaw
        track wolf
    """

    key = "track"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()

        if hasattr(caller, "is_profession") and caller.is_profession("ranger") and args:
            cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
            now = time.time()
            if now < float(cooldowns.get("track", 0) or 0):
                caller.msg("You need a moment before trying to pick up the trail again.")
                return

            ok, message = caller.attempt_ranger_track(args)
            caller.msg(message)
            cooldowns["track"] = now + 5
            caller.ndb.cooldowns = cooldowns
            return

        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("track", 0) or 0):
            caller.msg("You need a moment before trying to pick up the trail again.")
            return

        target = caller.get_bounty_target() if hasattr(caller, "get_bounty_target") else None
        if not target:
            caller.msg("You are not tracking anyone.")
            return
        if not getattr(target, "location", None):
            return
        if not (getattr(target.db, "warrants", None) or {}):
            caller.db.active_bounty = None
            caller.msg("Your bounty is no longer valid.")
            return
        sessions = getattr(target, "sessions", None)
        if not sessions or not list(sessions.all()):
            caller.msg("Your target has gone to ground.")
            return
        if getattr(target.db, "is_hidden_from_tracking", False):
            caller.msg("Your target has gone to ground. You cannot find them.")
            return

        region = getattr(target.db, "last_known_region", None) or "an unknown region"
        caller.msg(f"Your target was last seen in {region}.")
        if random.randint(1, 100) < 30:
            caller.msg("Your information may be outdated.")
        last_warning = float(getattr(target.ndb, "last_track_warning", 0) or 0)
        if now - last_warning >= 60:
            target.msg("You feel like someone is hunting you.")
            target.ndb.last_track_warning = now

        cooldowns["track"] = now + 5
        caller.ndb.cooldowns = cooldowns
