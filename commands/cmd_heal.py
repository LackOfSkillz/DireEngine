from commands.command import Command


class CmdHeal(Command):
    """
    Transfer another character's wounds onto yourself.

    Examples:
      heal jekar
    """

    key = "heal"
    help_category = "Character"

    def func(self):
        if not self.caller.is_empath():
            self.caller.msg("You cannot do that.")
            return
        if not self.args or str(self.args).strip().lower() in {"self", "me"}:
            ok, message = self.caller.mend_empath_self() if hasattr(self.caller, "mend_empath_self") else (False, "You cannot mend yourself.")
            self.caller.msg(message)
            return
        self.caller.msg("Empaths heal through touch and transfer. Use perceive, touch <target>, link <target>, link deepen <target>, assess, stabilize <target>, take <type> <amount> from <target>, redirect <type> <amount> from <source> to <target>, purge <type>, center, unity <ally1> <ally2>, manipulate <target>, and mend self.")