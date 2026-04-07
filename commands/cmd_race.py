from commands.command import Command

from world.races import TEST_RACES, get_race_display_name, resolve_race_name


class CmdRace(Command):
    """
    Review your race, inspect a target as staff, or change your race once.

    Examples:
        race
        race volgrin
        race kier
    """

    key = "race"
    locks = "cmd:all()"
    help_category = "Character"

    def _is_staff_viewer(self):
        return self.caller.locks.check_lockstring(self.caller, "perm(Builder) or perm(Admin) or perm(Developer)")

    def _render_profile(self, target):
        if not hasattr(target, "get_race_profile_lines"):
            self.caller.msg("That target does not expose race data.")
            return
        self.caller.msg("\n".join(target.get_race_profile_lines()))

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            self._render_profile(caller)
            if hasattr(caller, "can_change_race") and caller.can_change_race():
                caller.msg("You may change your race once with: race <name>")
            return

        normalized_race = resolve_race_name(args, default=None)
        if normalized_race in TEST_RACES:
            if not hasattr(caller, "set_race"):
                caller.msg("You cannot change your race here.")
                return
            current_race = caller.get_race() if hasattr(caller, "get_race") else getattr(getattr(caller, "db", None), "race", None)
            if current_race == normalized_race:
                caller.msg(f"You are already {get_race_display_name(normalized_race)}.")
                return
            if current_race and hasattr(caller, "can_change_race") and not caller.can_change_race():
                caller.msg("You cannot change your race again.")
                return
            caller.set_race(normalized_race, sync=True, emit_messages=False)
            if current_race and hasattr(caller, "mark_race_changed"):
                caller.mark_race_changed()
            caller.msg(f"You are now {get_race_display_name(normalized_race)}.")
            return

        if not self._is_staff_viewer():
            valid = ", ".join(get_race_display_name(race_key) for race_key in TEST_RACES)
            caller.msg(f"Unknown race. Valid options: {valid}")
            return

        target = caller.search(args, global_search=True)
        if not target:
            return

        self._render_profile(target)
