from collections import defaultdict

from evennia import Command


class CmdAbilities(Command):
    """
    List the abilities currently visible to you.

    Examples:
      abilities
    """

    key = "abilities"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        abilities = self.caller.get_visible_abilities()

        if not abilities:
            self.caller.msg("You know no abilities.")
            return

        groups = defaultdict(list)
        for ability in abilities:
            groups[ability.category].append(ability.key)

        lines = []
        for category in sorted(groups):
            lines.append(f"{category.upper()}:")
            for key in sorted(groups[category]):
                lines.append(f"  - {key}")

        self.caller.msg("\n".join(lines))