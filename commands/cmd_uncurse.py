from commands.command import Command


class CmdUncurse(Command):
    """
    Ease or remove Death's Sting from a living target.

    Examples:
        uncurse arannis
    """

    key = "uncurse"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can invoke that mercy.")
            return
        if not self.args:
            caller.msg("Uncurse whom?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        power = max(10, int((caller.get_skill("attunement") + caller.get_skill("magic")) / 4)) if hasattr(caller, "get_skill") else 10
        if hasattr(caller, "spend_attunement") and not caller.spend_attunement(max(5, int(round(power / 3)))):
            caller.msg("You lack the attunement to complete the rite.")
            return
        ok, message = target.reduce_death_sting(power) if hasattr(target, "reduce_death_sting") else (False, "They cannot be unbound that way.")
        caller.msg(message)
        if ok:
            target.msg(f"{caller.key}'s prayer eases the mark death left on you.")
            if getattr(caller, "location", None):
                caller.location.msg_contents(f"{caller.key} murmurs a brief rite over {target.key}, lifting some of death's burden.", exclude=[caller, target])