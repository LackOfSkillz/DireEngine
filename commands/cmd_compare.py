from commands.command import Command


class CmdCompare(Command):
    """
    Compare two items to judge their differences.

    Examples:
        compare sword, dagger
    """

    key = "compare"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if " with " not in self.args:
            self.caller.msg("Compare what with what?")
            return

        first_name, second_name = self.args.split(" with ", 1)
        candidates = list(getattr(self.caller, "contents", []) or [])
        if getattr(self.caller, "location", None):
            candidates.extend(obj for obj in list(getattr(self.caller.location, "contents", []) or []) if obj != self.caller)
        first_item, first_matches, first_base, first_index = self.resolve_item_target(first_name.strip(), candidates, default_first=True)
        second_item, second_matches, second_base, second_index = self.resolve_item_target(second_name.strip(), candidates, default_first=True)

        if not first_item and first_matches and first_index is not None:
            self.msg_item_matches(first_base, first_matches)
            return
        if not second_item and second_matches and second_index is not None:
            self.msg_item_matches(second_base, second_matches)
            return
        if not first_item:
            first_item = self.caller.search(first_name.strip())
        if not second_item:
            second_item = self.caller.search(second_name.strip())

        if not first_item or not second_item:
            return

        self.caller.compare_items(first_item, second_item)
