from commands.command import Command


class CmdBind(Command):
    """
    Bind a restored soul securely to its corpse.

    Examples:
        bind corpse
    """

    key = "bind"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can perform that rite.")
            return
        if not self.args:
            caller.msg("Bind which corpse?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        if not getattr(getattr(target, "db", None), "is_corpse", False):
            caller.msg("You can only bind a soul to a corpse.")
            return
        ok, message = caller.start_cleric_corpse_ritual(target, "bind") if hasattr(caller, "start_cleric_corpse_ritual") else (False, "You cannot bind that corpse.")
        caller.msg(message)