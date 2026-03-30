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
        target_name = (self.args or "").strip() or None
        self.caller.cast_spell(target_name=target_name)