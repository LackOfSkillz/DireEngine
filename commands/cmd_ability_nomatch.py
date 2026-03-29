from evennia import Command, syscmdkeys

from typeclasses.abilities import get_ability


class CmdAbilityNoMatch(Command):
    key = syscmdkeys.CMD_NOMATCH
    locks = "cmd:all()"
    auto_help = False

    def func(self):
        raw = str(self.args or "").strip()
        if not raw:
            return

        ability_key, _, target_name = raw.partition(" ")
        ability_key = ability_key.strip().lower()
        target_name = target_name.strip() or None

        ability = get_ability(ability_key, self.caller)
        if not ability:
            self.caller.msg(f"Command '{ability_key}' is not available.")
            return

        self.caller.execute_ability_input(ability_key, target_name=target_name)