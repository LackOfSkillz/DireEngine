from commands.command import Command


class CmdMindstate(Command):
    """
    Show the skills you are actively learning right now.

    Examples:
      mindstate
      learn
      mnd
    """

    key = "mindstate"
    aliases = ["learn", "learning", "mnd"]
    help_category = "Character"

    def func(self):
        entries = self.caller.get_active_learning_entries()
        if not entries:
            self.caller.msg(f"Active Learning: clear [0/{self.caller.get_mindstate_cap()}]")
            return

        self.caller.msg("Active Learning:")
        for entry in entries:
            self.caller.msg(
                f"  {entry['skill']}: rank {entry['rank']}, {entry['label']} [{entry['mindstate']}/{entry['cap']}]"
            )