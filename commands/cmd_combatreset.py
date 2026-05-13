from commands.command import Command


class CmdCombatReset(Command):
    """
    Reset a character's combat and wound state.

    Examples:
        combatreset AedanSmoke
    """

    key = "combatreset"
    aliases = ["cmbreset"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Combat reset whom?")
            return

        target = caller.search(query, global_search=True)
        if not target:
            return
        if not hasattr(target, "combat_reset_state"):
            caller.msg(f"You cannot combat reset {target.key}.")
            return

        target.combat_reset_state()
        caller.msg(f"You reset {target.key}'s combat state.")
        if target != caller:
            target.msg("A restoring force clears your combat state and lingering wounds.")
