from evennia import Command


class CmdSearch(Command):
    key = "search"
    locks = "cmd:all()"
    help_category = "Perception"

    def func(self):
        self.caller.execute_ability_input("search")