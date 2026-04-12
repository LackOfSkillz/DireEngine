from commands.command import Command


class CmdRecall(Command):
    """
    Recall learned lore, teaching notes, or profession guidance.

    Examples:
        recall
        recall ranger
    """

    key = "recall"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Recall what?")
            return

        self.caller.recall_knowledge(self.args.strip().lower())
