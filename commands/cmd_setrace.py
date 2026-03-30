from commands.command import Command

from world.races import TEST_RACES, get_race_display_name, resolve_race_name


class CmdSetRace(Command):
    """
    Set a character's race for testing or admin work.

    Examples:
        setrace kier = elf
        setrace kier = s'kra mur
    """

    key = "setrace"
    locks = "cmd:perm(Developer) or perm(Admin) or perm(Builder)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        if not args or "=" not in args:
            caller.msg("Usage: setrace <player> = <race>")
            return

        target_name, _, race_text = args.partition("=")
        target_name = target_name.strip()
        race_text = race_text.strip()
        if not target_name or not race_text:
            caller.msg("Usage: setrace <player> = <race>")
            return

        target = caller.search(target_name, global_search=True)
        if not target:
            return

        canonical_race = resolve_race_name(race_text, default=None)
        if canonical_race is None:
            valid = ", ".join(get_race_display_name(race_key) for race_key in TEST_RACES)
            caller.msg(f"Invalid race. Valid options: {valid}")
            return

        if not hasattr(target, "set_race"):
            caller.msg("That target cannot have a race applied.")
            return

        target.set_race(canonical_race, sync=True, emit_messages=True)
        display_name = get_race_display_name(canonical_race)
        caller.msg(f"Set {target.key}'s race to {display_name}.")
        if caller != target:
            target.msg(f"Your race is now {display_name}.")