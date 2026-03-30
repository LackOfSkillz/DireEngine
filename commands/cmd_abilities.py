from collections import defaultdict

from evennia import Command

from typeclasses.abilities import get_ability_map


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
        ability_map = get_ability_map(self.caller)
        available = []
        locked = []

        for ability in ability_map.values():
            if not self.caller.passes_guild_check(ability):
                continue
            if hasattr(self.caller, "is_hidden_warrior_ability") and self.caller.is_hidden_warrior_ability(ability):
                continue

            visible = self.caller.can_see_ability(ability)
            meets_requirements, requirement_message = self.caller.meets_ability_requirements(ability)

            if visible and meets_requirements:
                available.append(ability)
                continue

            visible_if = getattr(ability, "visible_if", {}) or {}
            skill_name = visible_if.get("skill") or (getattr(ability, "required", {}) or {}).get("skill")
            min_rank = int(visible_if.get("min_rank", 0) or 0)
            reason = requirement_message
            if not reason and skill_name:
                reason = f"requires rank {min_rank} in {skill_name}"
            locked.append((ability, reason or "locked"))

        if not available and not locked:
            self.caller.msg("You know no abilities.")
            return

        groups = defaultdict(list)
        for ability in available:
            groups[ability.category].append(ability.key)

        lines = ["Abilities:"]
        for category in sorted(groups):
            lines.append(f"{category.upper()}:")
            for key in sorted(groups[category]):
                lines.append(f"  - {key}")

        for ability, reason in sorted(locked, key=lambda entry: entry[0].key):
            lines.append(f"  - {ability.key} (locked{f' - {reason}' if reason else ''})")

        self.caller.msg("\n".join(lines))