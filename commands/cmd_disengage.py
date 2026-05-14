from commands.command import Command
from engine.services.messaging import send_action_messages, send_untargeted_action


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

        if hasattr(self.caller, "break_combat_rhythm"):
            self.caller.break_combat_rhythm(show_message=True)

        self.caller.set_roundtime(3)
        if target:
            send_action_messages(
                actor=self.caller,
                target=target,
                actor_message="You step back and disengage.",
                target_message=f"{self.caller.key} disengages from you.",
                room_message=f"{self.caller.key} disengages from {target.key}.",
            )
        else:
            send_untargeted_action(
                self.caller,
                actor_message="You step back and disengage.",
                room_message=f"{self.caller.key} steps back from the fight.",
            )