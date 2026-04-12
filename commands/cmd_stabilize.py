from commands.command import Command


class CmdStabilize(Command):
    """
    Slow a patient's bleeding without directly healing them.

    Examples:
        stabilize jekar
    """

    key = "stabilize"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Stabilize whom?")
            return
        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return
        if getattr(getattr(target, "db", None), "is_corpse", False):
            if getattr(caller, "is_profession", lambda *_: False)("cleric"):
                ok, message = caller.start_cleric_corpse_ritual(target, "stabilize") if hasattr(caller, "start_cleric_corpse_ritual") else (False, "You fail to stabilize the corpse.")
            elif getattr(caller, "is_empath", lambda: False)():
                ok, message = caller.stabilize_corpse(target) if hasattr(caller, "stabilize_corpse") else (False, "You fail to preserve the corpse.")
            else:
                ok, message = (False, "You cannot do that.")
            caller.msg(message)
            if ok and getattr(caller, "location", None):
                caller.location.msg_contents(f"{caller.key} carefully tends to {target.key}, slowing its decay.", exclude=[caller])
            return
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot do that.")
            return
        ok, message = caller.stabilize_empath_target(target) if hasattr(caller, "stabilize_empath_target") else (False, "You fail to steady their condition.")
        caller.msg(message)
        if ok:
            if getattr(caller, "location", None):
                caller.location.msg_contents(f"{caller.key} steadies {target.key}'s condition with practiced calm.", exclude=[caller, target])
            target.msg("Your condition steadies under careful hands.")