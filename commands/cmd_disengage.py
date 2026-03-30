from evennia import Command


class CmdDisengage(Command):
    """
    Step out of a fight and clear your current target.

    Examples:
      disengage
      dis
    """

    key = "disengage"
    aliases = ["dis"]
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to pull away.")
            self.caller.consume_stun()
            return

        if self.caller.is_in_roundtime():
            self.caller.msg_roundtime_block()
            return

        if not self.caller.db.in_combat:
            self.caller.msg("You are not fighting anyone right now.")
            return

        target = self.caller.db.target

        self.caller.set_target(None)
        self.caller.db.target_body_part = None

        if target and target.db.target == self.caller:
            target.set_target(None)
            target.msg(f"{self.caller.key} breaks away from the fight.")

        if hasattr(self.caller, "break_combat_rhythm"):
            self.caller.break_combat_rhythm(show_message=True)

        self.caller.set_roundtime(3)
        self.caller.msg("You step back and disengage.")
        if self.caller.location:
            self.caller.location.msg_contents(
                f"{self.caller.key} steps back from the fight.",
                exclude=self.caller,
            )