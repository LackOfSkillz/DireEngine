from commands.command import Command


class CmdFavor(Command):
    """
    Review your current divine favor.

    Examples:
        favor
    """

    key = "favor"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        favor = caller.get_favor() if hasattr(caller, "get_favor") else 0
        message = caller.get_favor_state_message() if hasattr(caller, "get_favor_state_message") else ""
        lines = [f"Favor: {favor}"]
        if message:
            lines.append(message)
        for line in lines:
            caller.msg(line)
