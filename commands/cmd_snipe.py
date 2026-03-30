from commands.command import Command


class CmdSnipe(Command):
    """
    Fire a concealed aimed shot from hiding.

    Examples:
        snipe goblin
    """

    key = "snipe"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if caller.is_stunned():
            caller.msg("You are too stunned to line up a snipe.")
            caller.consume_stun()
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Snipe whom?")
            return
        ok, message, should_attack = caller.prepare_ranger_snipe(args) if hasattr(caller, "prepare_ranger_snipe") else (False, "You are not properly positioned to snipe.", False)
        caller.msg(message)
        if should_attack:
            caller.execute_cmd(f"attack {args}")
