from commands.command import Command


class CmdDepart(Command):
    """
    Leave death behind and release your claim on the body.

    Examples:
        depart
        depart confirm
    """

    key = "depart"
    locks = "cmd:all()"
    help_category = "Character"

    def _clear_confirmation(self, caller):
        caller.db.depart_confirm_mode = None
        caller.db.depart_confirm_expires_at = 0.0

    def func(self):
        caller = self.caller
        if not hasattr(caller, "depart_self"):
            caller.msg("You cannot depart from here.")
            return
        try:
            from systems import onboarding

            handled, message = onboarding.note_depart_action(caller)
            if handled:
                caller.msg(message)
                return
        except Exception:
            pass
        if not hasattr(caller, "is_dead") or not caller.is_dead():
            caller.msg("You are not dead.")
            return

        raw_args = str(self.args or "").strip().lower()
        if raw_args in {"", "standard"}:
            if hasattr(caller, "can_confirm_depart"):
                if not caller.begin_depart_confirmation(depart_type="standard"):
                    caller.msg("Your choice is already before you. Type DEPART CONFIRM to follow through.")
                    return
            caller.msg("Are you sure you wish to depart? This will forfeit your body.")
            return

        if raw_args == "confirm":
            pending_mode = str(getattr(caller.db, "depart_confirm_mode", "") or "").strip().lower() or "standard"
            if hasattr(caller, "can_confirm_depart") and not caller.can_confirm_depart(depart_type=pending_mode):
                self._clear_confirmation(caller)
                caller.msg("Your resolve slips. Type DEPART again if you still wish to let go.")
                return
            mode = pending_mode
        elif raw_args in {"grave", "coins", "items", "full", "default"}:
            mode = None if raw_args == "default" else raw_args
            if raw_args in {"coins", "items", "full"}:
                if hasattr(caller, "begin_depart_confirmation"):
                    if not caller.begin_depart_confirmation(depart_type=raw_args):
                        caller.msg("That departure path is already pending. Type DEPART CONFIRM to proceed.")
                        return
                caller.msg(f"DEPART {raw_args} will spend favor. Type DEPART CONFIRM to proceed.")
                return
        else:
            caller.msg("Type DEPART to begin letting go, then DEPART CONFIRM to follow through.")
            return

        ok, message = caller.depart_self(mode=mode)
        self._clear_confirmation(caller)
        caller.msg(message)
