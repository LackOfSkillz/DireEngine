from commands.command import Command

from domain.learning.tdp_cost import tdp_cost_for_character
from world.races.utils import get_racial_tdp_modifier


STAT_DESCRIPTIONS = {
    "strength": "damage, burden capacity, and weapon round times",
    "stamina": "hit points and burden capacity",
    "agility": "attack accuracy, evasion, and balance",
    "reflex": "evasion, parry, shield, and multi-opponent defense",
    "charisma": "social pressure, trading, and bardic presence",
    "discipline": "experience pool size and concentration",
    "wisdom": "experience absorption and magical control",
    "intelligence": "experience pool size and spell potency",
}


class CmdStatInfo(Command):
    """
    Review one of your core attributes.

    Usage:
        strength
        stamina
        agility
        reflex
        charisma
        discipline
        wisdom
        intelligence
    """

    key = "strength"
    aliases = ["stamina", "agility", "reflex", "charisma", "discipline", "wisdom", "intelligence"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()
        stat = str(getattr(self, "cmdstring", self.key) or self.key).strip().lower()
        if stat not in STAT_DESCRIPTIONS:
            caller.msg(f"Unknown stat: {stat}")
            return
        current = int(getattr(caller, "get_stat", lambda name: (getattr(caller.db, "stats", {}) or {}).get(name, 0))(stat) or 0)
        race = str(getattr(caller.db, "race", "human") or "human").strip().lower()
        modifier = get_racial_tdp_modifier(race, stat)
        cost = tdp_cost_for_character(caller, stat)
        tdp = int(getattr(caller.db, "tdp", 0) or 0)
        caller.msg(
            "\n".join(
                [
                    stat.title(),
                    f"  Current value: {current}",
                    f"  Racial modifier: {modifier:+d} ({race.replace('_', ' ').title()})",
                    f"  Cost to raise to {current + 1}: {cost} TDPs",
                    f"  Affects: {STAT_DESCRIPTIONS[stat]}",
                    "",
                    f"  Time Development Points available: {tdp}",
                ]
            )
        )