from evennia import syscmdkeys

from commands.command import Command

from typeclasses.abilities import get_ability


def _soft_nomatch_message(caller):
    try:
        from systems import onboarding

        if onboarding.is_in_onboarding(caller):
            return "That doesn't mean anything here."
    except Exception:
        pass

    try:
        from systems import aftermath

        if aftermath.is_new_player(caller):
            return "That doesn't mean anything here."
    except Exception:
        pass

    return "You hesitate, but nothing comes of it."


class CmdAbilityNoMatch(Command):
    """
    Fallback handler for unmatched ability input.
    """

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
            self.caller.msg(_soft_nomatch_message(self.caller))
            return
        if hasattr(self.caller, "is_hidden_warrior_ability") and self.caller.is_hidden_warrior_ability(ability):
            self.caller.msg(_soft_nomatch_message(self.caller))
            return

        self.caller.execute_ability_input(ability_key, target_name=target_name)