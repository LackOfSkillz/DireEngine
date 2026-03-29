from evennia import Command


class CmdAdvance(Command):
    """
    Close back into melee with your current target.

    Examples:
      advance
      adv
    """

    key = "advance"
    aliases = ["adv"]
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to press the attack.")
            self.caller.consume_stun()
            return

        if self.caller.is_in_roundtime():
            self.caller.msg_roundtime_block()
            return

        target = self.caller.db.target
        if not target:
            self.caller.msg("Advance toward what?")
            return

        if target.location != self.caller.location:
            self.caller.set_target(None)
            self.caller.msg("Your target is no longer here.")
            return

        if self.caller.get_range(target) == "melee":
            self.caller.msg(f"You are already in melee with {target.key}.")
            return

        self.caller.set_target(target)
        target.set_target(self.caller)
        self.caller.set_range(target, "melee")
        self.caller.msg(f"You close the distance on {target.key}.")
        target.msg(f"{self.caller.key} closes the distance on you.")
        if self.caller.location:
            self.caller.location.msg_contents(
                f"{self.caller.key} closes the distance on {target.key}.",
                exclude=[self.caller, target],
            )