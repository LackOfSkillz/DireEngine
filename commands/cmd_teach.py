from commands.command import Command


class CmdTeach(Command):
    """
    Start teaching a skill or lesson to another character.

    Examples:
        teach corl tactics
    """

    key = "teach"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        if " to " not in self.args:
            self.caller.msg("Usage: teach <skill> to <target>")
            return

        skill_name, target_name = self.args.split(" to ", 1)
        target, matches, base_query, index, _scope = self.resolve_target(
            target_name.strip(),
            scopes=("characters",),
            default_first=True,
        )
        if not target and matches and index is not None:
            self.msg_target_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(target_name.strip())
        if not target:
            return

        self.caller.start_teaching(skill_name.strip().lower(), target)
