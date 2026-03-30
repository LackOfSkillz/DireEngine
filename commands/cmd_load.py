from commands.command import Command


class CmdLoad(Command):
    """
    Load a ranged weapon with ammunition.

    Examples:
        load bow
        load
    """

    key = "load"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if caller.is_stunned():
            caller.msg("You are too stunned to load a weapon.")
            caller.consume_stun()
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        args = str(self.args or "").strip()
        ok, message = caller.load_ranged_weapon(args) if hasattr(caller, "load_ranged_weapon") else (False, "You cannot load that.")
        caller.msg(message)
