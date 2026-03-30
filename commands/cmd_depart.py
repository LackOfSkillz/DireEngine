from commands.command import Command


class CmdDepart(Command):
    """
    Leave death behind and return by the path your favor allows.

    Examples:
        depart
        depart grave
        depart coins
        depart items
        depart full
    """

    key = "depart"
    locks = "cmd:all()"
    help_category = "Character"

    def _clear_confirmation(self, caller):
        caller.db.depart_confirm_mode = None

    def _needs_confirmation(self, mode):
        return mode in {"coins", "items", "full"}

    def func(self):
        caller = self.caller
        if not hasattr(caller, "depart_self"):
            caller.msg("You cannot depart from here.")
            return
        if not hasattr(caller, "is_dead") or not caller.is_dead():
            caller.msg("You are not dead.")
            return

        raw_args = str(self.args or "").strip().lower()
        if raw_args in {"", "help", "preview", "status"}:
            raw_args = "preview"
        corpse = caller.get_death_corpse() if hasattr(caller, "get_death_corpse") else None
        if raw_args == "preview":
            self._clear_confirmation(caller)
            if hasattr(caller, "get_depart_preview_lines"):
                caller.msg("\n".join(caller.get_depart_preview_lines(corpse=corpse)))
            else:
                caller.msg("You linger between death and return, unsure which path remains open.")
            return

        if raw_args == "confirm":
            pending_mode = str(getattr(caller.db, "depart_confirm_mode", "") or "").strip().lower()
            if not pending_mode:
                caller.msg("You have not chosen a costly departure path yet. Use DEPART to review your options.")
                return
            mode = pending_mode
        else:
            mode = raw_args

        chosen_mode = caller.get_depart_mode(corpse=corpse, requested_mode=mode) if hasattr(caller, "get_depart_mode") else None

        if mode and chosen_mode is None:
            self._clear_confirmation(caller)
            caller.msg("You do not have enough favor for that departure path. Choose grave, coins, items, or full.")
            return

        if mode == "default":
            mode = None

        if mode and mode != "grave" and self._needs_confirmation(mode) and raw_args != "confirm":
            caller.db.depart_confirm_mode = mode
            if hasattr(caller, "get_depart_preview_lines"):
                caller.msg("\n".join(caller.get_depart_preview_lines(corpse=corpse)))
            caller.msg(f"DEPART {mode} will spend favor. Type DEPART CONFIRM to proceed.")
            return

        ok, message = caller.depart_self(mode=mode)
        self._clear_confirmation(caller)
        caller.msg(message)
        if ok and getattr(caller, "location", None):
            caller.location.msg_contents(f"{caller.key} draws a ragged breath and returns from the edge of death.", exclude=[caller])
