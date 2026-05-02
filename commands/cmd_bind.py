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
        target, matches, base_query, index, _scope = self.resolve_target(
            self.args.strip(),
            scopes=("room",),
            default_first=True,
        )
        if not target and matches and index is not None:
            self.msg_target_matches(base_query, matches)
            return
        if not target:
            target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        if not getattr(getattr(target, "db", None), "is_corpse", False):
            caller.msg("You can only bind a soul to a corpse.")
            return
        ok, message = caller.start_cleric_corpse_ritual(target, "bind") if hasattr(caller, "start_cleric_corpse_ritual") else (False, "You cannot bind that corpse.")
        caller.msg(message)