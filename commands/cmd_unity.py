from commands.command import Command


class CmdUnity(Command):
    """
    Weave a shared empathic bond between allies.

    Examples:
        unity jekar corl
        unity jekar, corl, aelis
    """

    key = "unity"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to weave unity.")
            return
        raw_args = str(self.args or "").strip()
        if not raw_args:
            caller.msg("Usage: unity <target1> <target2> [target3]")
            return
        if "," in raw_args:
            names = [entry.strip() for entry in raw_args.split(",") if entry.strip()]
        else:
            names = [entry.strip() for entry in raw_args.split() if entry.strip()]
        if len(names) < 2:
            caller.msg("You need at least two allies for unity.")
            return
        targets = []
        for name in names[:3]:
            target = caller.search(name, location=caller.location)
            if not target:
                return
            targets.append(target)
        ok, message = caller.create_empath_unity(targets) if hasattr(caller, "create_empath_unity") else (False, "You fail to weave the bond.")
        caller.msg(message)