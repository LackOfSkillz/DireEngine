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
        if not raw or " about " not in raw.lower():
            self.caller.msg("Ask whom about what?")
            return

        target_name, _, topic = raw.partition(" about ")
        if not topic:
            marker = raw.lower().find(" about ")
            target_name = raw[:marker].strip()
            topic = raw[marker + len(" about "):].strip()

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
