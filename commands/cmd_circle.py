from evennia import Command

from world.systems.warrior import format_warrior_ability_name


class CmdCircle(Command):
    """
    View your current profession circle and advancement progress.

    Examples:
        circle
    """

    key = "circle"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("warrior"):
            caller.msg("You are not following the Warrior path.")
            return

        circle = caller.get_warrior_circle()
        next_unlocks = caller.get_next_warrior_unlocks()
        lines = [f"Warrior Circle: {circle}"]
        if next_unlocks:
            unlock_circle, ability_key = next_unlocks[0]
            lines.append(f"Next: {format_warrior_ability_name(ability_key)} (Circle {unlock_circle})")
        else:
            lines.append("Next: You have mastered the current Warrior path.")
        caller.msg("\n".join(lines))
