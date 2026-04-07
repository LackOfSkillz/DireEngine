from commands.command import Command
from commands.navigation import traverse_named_exit


class CmdGo(Command):
    """
    Travel through a visible exit by name.

    Examples:
        go north
        go guild
    """

    key = "go"
    locks = "cmd:all()"
    help_category = "Movement"

    def func(self):
        destination = str(self.args or "").strip()
        if not destination:
            self.caller.msg("Go where?")
            return
        if traverse_named_exit(self.caller, destination):
            return
        self.caller.msg(f"You can't go '{destination}'.")