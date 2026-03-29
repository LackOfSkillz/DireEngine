from evennia import Command


class CmdStudy(Command):
    key = "study"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        target_name = (self.args or "").strip()
        if not target_name:
            self.caller.msg("Study what?")
            return

        target = self.caller.search(target_name)
        if not target:
            return

        self.caller.study_item(target)