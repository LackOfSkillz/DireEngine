from evennia import Command


class CmdSearch(Command):
    """
    Search the room for hidden objects, exits, or clues.

    Examples:
        search
        search chest
    """

    key = "search"
    locks = "cmd:all()"
    help_category = "Perception"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if args:
            target = caller.search(args, location=caller.location)
            if not target:
                return
            if hasattr(caller, "search_loot_target") and bool(getattr(getattr(target, "db", None), "is_npc", False)):
                caller.search_loot_target(target)
                return
        caller.execute_ability_input("search")
