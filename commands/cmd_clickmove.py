from commands.command import Command


class CmdClickMove(Command):
    """Internal wrapper for clickable exit links."""

    key = "__clickmove__"
    locks = "cmd:all()"
    help_category = "System"
    auto_help = False

    def func(self):
        direction = (self.args or "").strip()
        if not direction:
            return

        self.caller.msg(f"> {direction}")
        self.caller.execute_cmd(direction)