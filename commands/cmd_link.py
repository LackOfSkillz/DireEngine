from commands.command import Command


class CmdLink(Command):
    """
    Deepen an empathic bond with a patient.

    Examples:
        link jekar
        link persistent jekar
        link focus scholarship
        link status
    """

    key = "link"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to deepen an empathic link.")
            return
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Usage: link <target>, link persistent <target>, link focus <skill>, or link status")
            return
        if args.lower() == "status":
            state = caller.get_empath_link_state(require_local=False, emit_break_messages=False) if hasattr(caller, "get_empath_link_state") else None
            if not state:
                caller.msg("You are not maintaining a connection.")
                return
            caller.msg(f"Link: {state.get('type')} to {state['target'].key}")
            caller.msg(f"Strength: {int(state.get('strength', 0) or 0)}")
            caller.msg(f"Stability: {int(state.get('stability', 0) or 0)}")
            caller.msg(f"Condition: {str(state.get('condition') or 'steady').title()}")
            bonus_skill = str(state.get("link_bonus_skill") or "").strip()
            bonus_value = int(state.get("link_bonus_value", 0) or 0)
            if bonus_skill and bonus_value > 0:
                caller.msg(f"Borrowed Focus: {caller.format_skill_name(bonus_skill)} (+{bonus_value})")
            return
        if args.lower().startswith("focus "):
            skill_name = args[6:].strip()
            if not skill_name:
                caller.msg("Focus on which skill?")
                return
            ok, message = caller.set_empath_link_focus(skill_name) if hasattr(caller, "set_empath_link_focus") else (False, "You cannot shape the link that way.")
            caller.msg(message)
            return
        persistent = False
        target_name = args
        if args.lower().startswith("persistent "):
            persistent = True
            target_name = args[11:].strip()
        if not target_name:
            caller.msg("Link whom?")
            return
        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        ok, lines = caller.link_empath_target(target, persistent=persistent) if hasattr(caller, "link_empath_target") else (False, ["You fail to deepen the bond."])
        for line in lines if isinstance(lines, list) else [str(lines)]:
            caller.msg(line)