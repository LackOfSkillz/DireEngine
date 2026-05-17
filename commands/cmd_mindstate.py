from commands.command import Command


def render_mindstate(caller):
    entries = caller.get_active_learning_entries()
    if not entries:
        caller.msg(f"Active Learning: clear [0/{caller.get_mindstate_cap()}]")
        return

    caller.msg("Active Learning:")
    for entry in entries:
        caller.msg(
            f"  {entry['skill']}: rank {entry['rank']}, {entry['label']} [{entry['mindstate']}/{entry['cap']}]"
        )


class CmdMindstate(Command):
    """
    Show the skills you are actively learning right now.

    Examples:
      mindstate
      learn
      mnd
    """

    key = "mindstate"
    aliases = ["learning", "mnd"]
    help_category = "Character"

    def func(self):
        render_mindstate(self.caller)