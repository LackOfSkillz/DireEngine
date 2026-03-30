from commands.command import Command


class CmdRace(Command):
    """
    Review the traits tied to your race.

    Examples:
        race
        race kier
    """

    key = "race"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        target = caller

        if self.args:
            if not caller.locks.check_lockstring(caller, "perm(Builder) or perm(Admin) or perm(Developer)"):
                caller.msg("You can only inspect your own race profile.")
                return
            target = caller.search(self.args.strip(), global_search=True)
            if not target:
                return

        if not hasattr(target, "get_race_profile_lines"):
            caller.msg("That target does not expose race data.")
            return

        caller.msg("\n".join(target.get_race_profile_lines()))