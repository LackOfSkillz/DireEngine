from commands.command import Command


class CmdHeal(Command):
    """
    Transfer another character's wounds onto yourself.

    Examples:
      heal jekar
    """

    key = "heal"
    help_category = "Character"

    def func(self):
        if not self.caller.is_empath():
            self.caller.msg("You cannot do that.")
            return

        if not self.args:
            self.caller.msg("Heal whom?")
            return

        target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.transfer_wounds(target)