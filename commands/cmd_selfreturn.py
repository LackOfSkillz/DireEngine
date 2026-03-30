from commands.command import Command


class CmdSelfReturn(Command):
    """
    Placeholder for future cleric self-resurrection.

    Examples:
        selfreturn
    """

    key = "selfreturn"
    aliases = ["self-return"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can reach toward that mystery.")
            return
        if not hasattr(caller, "is_dead") or not caller.is_dead():
            caller.msg("You are not beyond life, so no self-return is needed.")
            return
        if hasattr(caller, "get_devotion") and caller.get_devotion() < 85:
            caller.msg("Your devotion is not yet strong enough for self-return.")
            return
        if hasattr(caller, "get_favor") and caller.get_favor() <= 0:
            caller.msg("You would need at least one thread of favor to attempt self-return.")
            return
        caller.msg("You reach toward the rite of self-return, but that mystery has not yet been fully opened.")