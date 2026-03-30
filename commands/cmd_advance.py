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

        current_range = self.caller.get_range(target)
        if current_range == "melee":
            self.caller.msg(f"You are already in melee with {target.key}.")
            return

        self.caller.set_target(target)
        target.set_target(self.caller)
        desired_range = "near" if current_range == "far" else "melee"
        keep_distance_bonus = target.get_ranger_keep_distance_bonus() if hasattr(target, "get_ranger_keep_distance_bonus") else 0
        if desired_range == "melee" and keep_distance_bonus and target.has_ranged_weapon_equipped() and self.caller.get_range(target) != "melee":
            hold_roll = target.get_stat("agility") + keep_distance_bonus + 20
            pressure_roll = self.caller.get_stat("reflex") + 20
            if hold_roll >= pressure_roll:
                desired_range = "near"

        self.caller.set_range(target, desired_range)
        if desired_range == "near":
            self.caller.msg(f"You press closer to {target.key}, but they keep a little space.")
            target.msg(f"{self.caller.key} closes in, but you keep them at near range.")
        else:
            self.caller.msg(f"You close the distance on {target.key}.")
            target.msg(f"{self.caller.key} closes the distance on you.")
        if self.caller.location:
            self.caller.location.msg_contents(
                f"{self.caller.key} closes the distance on {target.key}.",
                exclude=[self.caller, target],
            )