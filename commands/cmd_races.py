from commands.command import Command

from world.races import TEST_RACES, get_race_profile


class CmdRaces(Command):
    """
    List the available races and their high-level identities.
    """

    key = "races"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        lines = ["Available races:", ""]
        for race_key in TEST_RACES:
            profile = get_race_profile(race_key)
            lines.append(f"{profile['name']}: {profile.get('description', '').strip()}")

        if hasattr(self.caller, "can_change_race") and self.caller.can_change_race():
            lines.extend(["", "You may change your race once with: race <name>"])

        self.caller.msg("\n".join(lines))