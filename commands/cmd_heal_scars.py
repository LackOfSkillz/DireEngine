from commands.command import Command


class CmdHealScars(Command):
    """
    Ease lasting scars through empathic treatment.

    Examples:
        heal scars
        heal scars self
        heal scars jekar
    """

    key = "heal scars"
    aliases = ["healscars"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot do that.")
            return
        args = str(self.args or "").strip()
        target = caller
        if args and args.lower() not in {"self", "me"}:
            target = caller.search(args, location=caller.location)
            if not target:
                return
        elif not args and hasattr(caller, "get_empath_link_state"):
            link_state = caller.get_empath_link_state(require_local=True, emit_break_messages=False)
            if link_state and link_state.get("target"):
                target = link_state.get("target")
        ok, message = caller.heal_empath_scars(target=target) if hasattr(caller, "heal_empath_scars") else (False, "You cannot heal scars that way.")
        caller.msg(message)
