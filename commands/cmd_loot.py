from commands.command import Command


class CmdLoot(Command):
    """
    Collect coins and valuables from a fallen target.

    Examples:
        loot goblin
    """

    key = "loot"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Loot what?")
            return
        candidates = [obj for obj in list(getattr(caller.location, "contents", []) or []) if obj != caller]
        target, matches, base_query, index = self.resolve_item_target(self.args.strip(), candidates, default_first=True)
        if not target:
            if matches and index is not None:
                self.msg_item_matches(base_query, matches)
            else:
                target = caller.search(self.args.strip(), location=caller.location)
            if not target:
                return
        if not hasattr(caller, "loot_target"):
            caller.msg("You cannot loot that.")
            return
        caller.loot_target(target)
