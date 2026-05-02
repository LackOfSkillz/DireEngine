from commands.command import Command


class CmdAnalyze(Command):
    """
    Study the current room for useful fieldcraft details.

    Examples:
        analyze
    """

    key = "analyze"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Analyze what?")
            return

        candidates = list(getattr(self.caller, "contents", []) or [])
        if getattr(self.caller, "location", None):
            candidates.extend(obj for obj in list(getattr(self.caller.location, "contents", []) or []) if obj != self.caller)
        target, matches, base_query, index = self.resolve_item_target(self.args.strip(), candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(self.args.strip())
        if not target:
            return

        if not getattr(target.db, "is_box", False):
            self.caller.msg("You can't analyze that.")
            return

        self.caller.analyze_trap(target)