from evennia import Command


class CmdRecover(Command):
    """
    Steady yourself and reduce warrior exhaustion.

    Examples:
      recover
    """

    key = "recover"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("warrior"):
            caller.msg("You are not following the Warrior path.")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        if hasattr(caller, "get_pressure_state") and getattr(caller.db, "in_combat", False):
            if caller.get_pressure_state() in {"high", "extreme"}:
                caller.msg("The pressure is too intense for you to recover right now.")
                return

        ok, message = caller.recover_warrior_exhaustion()
        caller.msg(message)
        if ok:
            caller.set_roundtime(3)