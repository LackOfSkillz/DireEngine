from evennia import Command


class CmdTeach(Command):
    key = "teach"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if " to " not in self.args:
            self.caller.msg("Usage: teach <skill> to <target>")
            return

        skill_name, target_name = self.args.split(" to ", 1)
        target = self.caller.search(target_name.strip())
        if not target:
            return

        self.caller.start_teaching(skill_name.strip().lower(), target)