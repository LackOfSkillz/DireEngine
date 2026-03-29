from evennia import Command


class CmdEndTeach(Command):
    key = "endteach"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        teaching = self.caller.get_state("teaching")
        if not teaching:
            self.caller.msg("You are not teaching anyone.")
            return

        self.caller.clear_state("teaching")
        self.caller.msg("You stop teaching.")