from evennia import Command


class CmdUseSkill(Command):
    """
    Try using a named skill directly.

    Examples:
      use tend
      use disengage
    """

    key = "use"
    help_category = "Character"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to do that.")
            self.caller.consume_stun()
            return

        if not self.args:
            self.caller.msg("Which skill do you want to use?")
            return

        skill = self.args.strip().lower()
        self.caller.use_skill(skill)