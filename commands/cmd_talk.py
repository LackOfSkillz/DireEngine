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
        target, matches, base_query, index, _scope = self.resolve_target(
            target_name,
            scopes=("npcs",),
            default_first=True,
        )
        if not target and matches and index is not None:
            self.msg_target_matches(base_query, matches)
            return
        if target and hasattr(target, "handle_interaction"):
            target.handle_interaction(self.caller)
            return
        self.caller.open_interaction_with(target_name)
