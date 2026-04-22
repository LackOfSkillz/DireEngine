from commands.command import Command


class CmdTalk(Command):
    """
    Interact with a nearby NPC.

    Examples:
        talk armorer
        interact ferryman
    """

    key = "talk"
    aliases = ["interact"]
    locks = "cmd:all()"
    help_category = "Social"

    def func(self):
        target_name = (self.args or "").strip()
        if not target_name:
            self.caller.msg("Talk to whom?")
            return
        self.caller.open_interaction_with(target_name)
