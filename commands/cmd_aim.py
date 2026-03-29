from evennia import Command


class CmdAim(Command):
    """
    Line up a careful shot against your current target.

    Examples:
      aim
    """

    key = "aim"
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to line up a careful shot.")
            self.caller.consume_stun()
            return

        target = self.caller.db.target
        if not target:
            self.caller.msg("Aim at whom? Set a target first.")
            return

        if target.location != self.caller.location:
            self.caller.set_target(None)
            self.caller.msg("Your target is no longer here.")
            return

        self.caller.db.aiming = target.id
        self.caller.set_state("aiming", target.id)
        self.caller.msg(f"You begin aiming at {target.key}.")