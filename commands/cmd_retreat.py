import random

from evennia import Command


class CmdRetreat(Command):
    """
    Try to open distance from your current target.

    Examples:
      retreat
      ret
    """

    key = "retreat"
    aliases = ["ret"]
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to disengage.")
            self.caller.consume_stun()
            return

        if self.caller.is_in_roundtime():
            self.caller.msg_roundtime_block()
            return

        target = self.caller.db.target
        if not target:
            self.caller.msg("Retreat from what?")
            return

        if target.location != self.caller.location:
            self.caller.set_target(None)
            self.caller.msg("Your target is no longer here.")
            return

        retreat_roll = random.randint(1, 100)
        player_score = self.caller.get_stat("agility") + retreat_roll + 10
        player_score -= (self.caller.db.fatigue or 0) * 0.2
        player_score += (self.caller.db.balance or 0) * 0.1
        player_score -= self.caller.get_leg_penalty()
        if hasattr(self.caller, "get_ranger_keep_distance_bonus"):
            player_score += self.caller.get_ranger_keep_distance_bonus()

        enemy_score = target.get_stat("reflex") + random.randint(1, 100)
        if hasattr(target, "get_pressure"):
            enemy_score += target.get_pressure(self.caller)

        if player_score > enemy_score:
            self.caller.set_range(target, "far")
            self.caller.msg(f"You successfully retreat from {target.key}!")
            target.msg(f"{self.caller.key} retreats out to far range.")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} retreats from {target.key}.",
                    exclude=[self.caller, target],
                )
        elif player_score > enemy_score - 10:
            self.caller.set_range(target, "near")
            self.caller.msg(f"You manage to pull back slightly from {target.key}.")
            target.msg(f"{self.caller.key} pulls back slightly from you.")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} pulls back slightly from {target.key}.",
                    exclude=[self.caller, target],
                )
        else:
            self.caller.msg(f"You fail to disengage from {target.key}!")
            target.msg(f"{self.caller.key} tries to retreat from you but cannot break away.")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} fails to break away from {target.key}.",
                    exclude=[self.caller, target],
                )

        self.caller.set_roundtime(1.5)