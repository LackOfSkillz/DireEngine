from commands.command import Command


class CmdRestore(Command):
    """
    Restore a prepared corpse's fading memories.

    Examples:
        restore corpse
    """

    key = "restore"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can perform that rite.")
            return
        if not self.args:
            caller.msg("Restore which corpse?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        if not getattr(getattr(target, "db", None), "is_corpse", False):
            caller.msg("You can only restore a corpse.")
            return
        ok, message = caller.start_cleric_corpse_ritual(target, "restore") if hasattr(caller, "start_cleric_corpse_ritual") else (False, "You cannot restore that corpse.")
        caller.msg(message)