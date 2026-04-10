from commands.command import Command


class CmdAsk(Command):
    """
    Ask an NPC about a topic.

    Examples:
        ask elarion about join
        ask elarion about advancement
    """

    key = "ask"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        raw = str(self.args or "").strip()
        lowered = raw.lower()
        marker = " about "
        if not raw or (" about " not in lowered and " for " not in lowered):
            self.caller.msg("Ask whom about what?")
            return

        if " for " in lowered and (" about " not in lowered or lowered.find(" for ") < lowered.find(" about ")):
            marker = " for "

        target_name, _, topic = raw.partition(marker)
        if not topic:
            marker_index = lowered.find(marker)
            target_name = raw[:marker_index].strip()
            topic = raw[marker_index + len(marker):].strip()

        target = self.caller.search(target_name.strip())
        if not target:
            return

        if not hasattr(target, "handle_inquiry"):
            self.caller.msg(f"{target.key} has nothing useful to say about that.")
            return

        response = target.handle_inquiry(self.caller, topic.strip())
        if not response:
            self.caller.msg(f"{target.key} has nothing useful to say about that.")
            return

        self.caller.msg(f'{target.key} says, "{response}"')
