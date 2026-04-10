from commands.command import Command


class CmdHeal(Command):
    """
        Work an empathic healing technique.

    Examples:
            heal self
            heal vitality
            heal wounds
    """

    key = "heal"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not caller.is_empath():
            caller.msg("You cannot do that.")
            return
        args = str(self.args or "").strip().lower()
        if not args or args in {"self", "me"}:
            ok, message = caller.mend_empath_self() if hasattr(caller, "mend_empath_self") else (False, "You cannot mend yourself.")
            caller.msg(message)
            return
        if args == "vitality":
            ok, message = caller.take_empath_wound("vitality") if hasattr(caller, "take_empath_wound") else (False, "You cannot heal vitality that way.")
            caller.msg(message)
            return
        if args == "wounds":
            ok, message = caller.take_empath_wound("bleeding") if hasattr(caller, "take_empath_wound") else (False, "You cannot heal wounds that way.")
            caller.msg(message)
            return
        caller.msg("Use heal self, heal vitality, heal wounds, or heal scars.")