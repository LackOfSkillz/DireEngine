from commands.command import Command
from engine.services.messaging import send_action_messages, send_untargeted_action


class CmdTarget(Command):
    """
    Focus your next attacks on a chosen part of the body.

    Examples:
      target head
      target arm
      target leg
    """

    key = "target"
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to aim your attacks.")
            self.caller.consume_stun()
            return

        if not self.args:
            self.caller.msg("Which body part or person do you want to target?")
            return

        part = self.args.strip().lower()
        valid = ["head", "chest", "arm", "leg"]
        if part not in valid:
            target, matches, base_query, index, _scope = self.resolve_target(
                self.args.strip(),
                scopes=("characters",),
                default_first=True,
            )
            if not target and matches and index is not None:
                self.msg_target_matches(base_query, matches)
                return
            if not target:
                target = self.caller.search(self.args.strip())
            if not target:
                return
            self.caller.set_target(target)
            send_action_messages(
                actor=self.caller,
                target=target,
                actor_message=f"You focus on {target.key}.",
                target_message=f"{self.caller.key} focuses on you.",
                room_message=f"{self.caller.key} fixes attention on {target.key}.",
            )
            return

        self.caller.db.target_body_part = part
        send_untargeted_action(
            self.caller,
            actor_message=f"You focus your attacks on the {part}.",
            room_message=f"{self.caller.key} shifts into a more precise stance.",
        )