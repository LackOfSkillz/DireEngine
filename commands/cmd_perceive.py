from commands.command import Command
import time


class CmdPerceive(Command):
    """
    Sense life force patterns nearby or in a specific target.

    Examples:
        perceive health
        perceive jekar
    """

    key = "perceive"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if getattr(caller, "is_profession", lambda *_: False)("cleric"):
            if not args:
                caller.msg("Perceive what? Try a corpse.")
                return
            target = caller.search(args, location=caller.location)
            if not target:
                return
            ok, lines = caller.perceive_cleric_corpse(target) if hasattr(caller, "perceive_cleric_corpse") else (False, ["You sense nothing useful."])
            for line in lines:
                caller.msg(line)
            return
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot read life forces that way.")
            return
        last_perceive_time = float(getattr(getattr(caller, "db", None), "last_perceive_time", 0.0) or 0.0)
        if time.time() - last_perceive_time < 20.0:
            caller.msg("You must wait before perceiving again.")
            return
        if not args or args.lower() == "health":
            ok, lines = caller.perceive_empath_health() if hasattr(caller, "perceive_empath_health") else (False, ["You sense nothing."])
            for line in lines:
                caller.msg(line)
            if ok:
                caller.db.last_perceive_time = time.time()
            return
        target = caller.search(args, location=caller.location)
        if not target:
            return
        ok, lines = caller.perceive_empath_target(target) if hasattr(caller, "perceive_empath_target") else (False, ["You cannot make sense of that life force."])
        for line in lines:
            caller.msg(line)
        if ok:
            caller.db.last_perceive_time = time.time()