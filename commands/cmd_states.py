from commands.command import Command


class CmdStates(Command):
    """
    Inspect your active internal states.

    Examples:
      states
    """

    key = "states"
    help_category = "Character"

    def func(self):
        states = self.caller.db.states or {}

        if not states:
            self.caller.msg("No active states.")
            return

        lines = [f"{key}: {value}" for key, value in states.items()]
        self.caller.msg("\n".join(lines))