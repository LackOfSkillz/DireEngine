from commands.command import Command
from commands.navigation import traverse_named_exit


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
        if traverse_named_exit(self.caller, direction):
            return
        self.caller.execute_cmd(direction)