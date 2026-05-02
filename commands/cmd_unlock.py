from commands.command import Command


class CmdUnlock(Command):
    """
    Attempt to unlock a loot box.

    Examples:
        unlock box
    """

    key = "unlock"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Unlock what?")
            return
        candidates = list(getattr(caller, "contents", []) or [])
        if getattr(caller, "location", None):
            candidates.extend(obj for obj in list(getattr(caller.location, "contents", []) or []) if obj != caller)
        target, matches, base_query, index = self.resolve_item_target(self.args.strip(), candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = caller.search(self.args.strip())
        if not target:
            return
        if not hasattr(caller, "unlock_box"):
            caller.msg("You cannot unlock that.")
            return
        caller.unlock_box(target)