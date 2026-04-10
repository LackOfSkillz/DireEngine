from commands.command import Command


class CmdUnity(Command):
    """
    Weave a shared empathic bond between allies.

    Examples:
        unity corl
        unity status
    """

    key = "unity"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to weave unity.")
            return
        raw_args = str(self.args or "").strip()
        if not raw_args:
            caller.msg("Usage: unity <target> or unity status")
            return
        if raw_args.lower() == "status":
            unity = caller.get_empath_unity_state() if hasattr(caller, "get_empath_unity_state") else None
            if not unity:
                caller.msg("You are not holding a shared burden together.")
                return
            caller.msg(f"Unity: {unity['primary_target'].key} <-> {unity['secondary_target'].key}")
            caller.msg(f"Stability: {int(unity.get('stability', 0) or 0)}")
            caller.msg(f"Condition: {str(unity.get('condition') or 'steady').title()}")
            return
        target = caller.search(raw_args, location=caller.location)
        if not target:
            return
        ok, message = caller.create_empath_unity(target) if hasattr(caller, "create_empath_unity") else (False, "You fail to weave the bond.")
        caller.msg(message)