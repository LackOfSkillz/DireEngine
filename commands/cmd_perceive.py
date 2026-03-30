from commands.command import Command


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
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot read life forces that way.")
            return
        if not args or args.lower() == "health":
            ok, lines = caller.perceive_empath_health() if hasattr(caller, "perceive_empath_health") else (False, ["You sense nothing."])
            for line in lines:
                caller.msg(line)
            return
        target = caller.search(args, location=caller.location)
        if not target:
            return
        ok, lines = caller.perceive_empath_target(target) if hasattr(caller, "perceive_empath_target") else (False, ["You cannot make sense of that life force."])
        for line in lines:
            caller.msg(line)