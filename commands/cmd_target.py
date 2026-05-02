from commands.command import Command


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
            self.caller.msg(f"You focus on {target.key}.")
            return

        self.caller.db.target_body_part = part
        self.caller.msg(f"You focus your attacks on the {part}.")