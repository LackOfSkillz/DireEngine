from evennia import Command


class CmdObserve(Command):
    key = "observe"
    locks = "cmd:all()"
    help_category = "Perception"

    def func(self):
        self.caller.use_ability("observe")