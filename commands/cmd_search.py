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
        self.caller.execute_ability_input("search")