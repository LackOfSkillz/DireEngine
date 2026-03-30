from commands.command import Command


class CmdRejuvenate(Command):
    """
    Improve a corpse's condition before resurrection.

    Examples:
        rejuvenate corpse
    """

    key = "rejuvenate"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can perform that rite.")
            return
        if not self.args:
            caller.msg("Rejuvenate which corpse?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        ok, message = caller.rejuvenate_corpse(target) if hasattr(caller, "rejuvenate_corpse") else (False, "You cannot rejuvenate that.")
        caller.msg(message)
        if ok and getattr(caller, "location", None):
            caller.location.msg_contents(f"{caller.key} traces a gentle rite over {target.key}, renewing its fading pattern.", exclude=[caller])
