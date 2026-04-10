from evennia import Command


class CmdCast(Command):
    """
    Release a prepared spell at its target.

    Examples:
        cast goblin
        cast self
    """

    key = "cast"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        prepared_spell = self.caller.get_state("prepared_spell") if hasattr(self.caller, "get_state") else None
        if not prepared_spell and not str(self.args or "").strip():
            self.caller.msg("If you meant to fish, try 'fish'.")
            return
        target_name = (self.args or "").strip() or None
        self.caller.cast_spell(target_name=target_name)
