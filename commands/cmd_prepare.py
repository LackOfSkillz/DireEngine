from commands.command import Command


class CmdPrepare(Command):
    """
    Prepare a spell before charging or casting it, or prepare a corpse for resurrection.

    Examples:
        prepare ignite
        prepare corpse
    """

    key = "prepare"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if getattr(caller, "is_profession", lambda *_: False)("cleric") and args:
            target = caller.search(args, location=caller.location)
            if target and getattr(getattr(target, "db", None), "is_corpse", False):
                ok, message = caller.prepare_corpse(target) if hasattr(caller, "prepare_corpse") else (False, "You cannot prepare that corpse.")
                caller.msg(message)
                return
        caller.prepare_spell(self.args)
