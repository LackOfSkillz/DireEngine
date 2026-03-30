from commands.command import Command


class CmdReposition(Command):
    """
    Shift range and footing to recover a better firing lane.

    Examples:
        reposition
    """

    key = "reposition"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if caller.is_stunned():
            caller.msg("You are too stunned to reposition.")
            caller.consume_stun()
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        ok, message = caller.attempt_ranger_reposition() if hasattr(caller, "attempt_ranger_reposition") else (False, "You cannot reposition right now.")
        caller.msg(message)
        if ok and hasattr(caller, "set_roundtime"):
            caller.set_roundtime(1.5)
