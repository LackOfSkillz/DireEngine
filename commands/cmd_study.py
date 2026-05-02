from commands.command import Command


class CmdStudy(Command):
    """
    Study an item, lesson, or topic source.

    Examples:
        study book
    """

    key = "study"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        target_name = (self.args or "").strip()
        if not target_name:
            self.caller.msg("Study what?")
            return

        candidates = list(getattr(self.caller, "contents", []) or [])
        if getattr(self.caller, "location", None):
            candidates.extend(obj for obj in list(getattr(self.caller.location, "contents", []) or []) if obj != self.caller)
        target, matches, base_query, index = self.resolve_item_target(target_name, candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(target_name)
        if not target:
            return

        self.caller.study_item(target)
