from commands.command import Command


class CmdOpen(Command):
    """
    Open a container, door, or similar object.

    Examples:
        open chest
        open door
    """

    key = "open"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        if not self.args:
            self.caller.msg("Open what?")
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

        if not self.caller.is_box_target(target):
            self.caller.msg("You can't open that.")
            return

        self.caller.open_box(target)
