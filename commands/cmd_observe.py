from evennia import Command


class CmdObserve(Command):
    key = "observe"
    locks = "cmd:all()"
    help_category = "Perception"

    def func(self):
        self.caller.execute_ability_input("observe")