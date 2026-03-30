from commands.command import Command


class CmdPounce(Command):
        """
        Leap from hiding into an opening attack.

        Examples:
            pounce goblin
        """

    key = "pounce"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Pounce whom?")
            return

        ok, message, should_attack = caller.attempt_ranger_pounce(args) if hasattr(caller, "attempt_ranger_pounce") else (False, "You cannot pounce right now.", False)
        caller.msg(message)
        if should_attack:
            caller.execute_cmd(f"attack {args}")