from commands.command import Command


class CmdPreserve(Command):
    """
    Preserve a corpse's lingering memories.

    Examples:
        preserve corpse
    """

    key = "preserve"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can preserve lingering memories that way.")
            return
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Preserve what?")
            return
        target = caller.search(args, location=caller.location)
        if not target:
            return
        ok, message = caller.preserve_corpse(target) if hasattr(caller, "preserve_corpse") else (False, "You cannot preserve that.")
        caller.msg(message)
