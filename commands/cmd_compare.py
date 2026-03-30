from evennia import Command


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
        first_item = self.caller.search(first_name.strip())
        second_item = self.caller.search(second_name.strip())

        if not first_item or not second_item:
            return

        self.caller.compare_items(first_item, second_item)
