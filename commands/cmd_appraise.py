from commands.command import Command


class CmdAppraise(Command):
    """
    Estimate the value and quality of an item.

    Examples:
        appraise sword
    """

    key = "appraise"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if not self.args:
            self.caller.msg("Appraise what?")
            return

        target, matches, base_query, index = self.resolve_item_target(
            self.args.strip(),
            getattr(self.caller, "contents", []),
            default_first=True,
        )
        if not target and getattr(self.caller, "location", None):
            room_candidates = [obj for obj in list(getattr(self.caller.location, "contents", []) or []) if obj != self.caller]
            target, matches, base_query, index = self.resolve_item_target(self.args.strip(), room_candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(self.args.strip())
        if not target:
            return

        self.caller.appraise_target(target)
