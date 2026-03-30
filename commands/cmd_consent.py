from commands.command import Command


class CmdConsent(Command):
    """
    Manage who may assist with corpse and grave recovery.

    Examples:
        consent arannis
        withdraw consent arannis
    """

    key = "consent"
    aliases = ["withdraw"]
    locks = "cmd:all()"
    help_category = "Character"

    def _parse_duration(self, token):
        raw = str(token or "").strip().lower()
        if not raw:
            return None
        multiplier = 1
        if raw.endswith("m"):
            multiplier = 60
            raw = raw[:-1]
        elif raw.endswith("h"):
            multiplier = 3600
            raw = raw[:-1]
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return max(1, value * multiplier)

    def func(self):
        caller = self.caller
        command_name = str(getattr(self, "cmdstring", self.key) or self.key).strip().lower()
        raw_args = str(self.args or "").strip()
        is_withdraw = command_name == "withdraw"
        if not raw_args and not is_withdraw:
            if hasattr(caller, "get_recovery_consent_lines"):
                caller.msg("\n".join(caller.get_recovery_consent_lines()))
            else:
                caller.msg("Recovery Consent: None")
            return
        query = raw_args
        if is_withdraw and query.lower().startswith("consent "):
            query = query[8:].strip()
        if not query:
            caller.msg("Consent for whom?" if not is_withdraw else "Withdraw consent from whom?")
            return
        duration = None
        parts = query.split()
        if not is_withdraw and len(parts) > 1:
            parsed = self._parse_duration(parts[-1])
            if parsed is not None:
                duration = parsed
                query = " ".join(parts[:-1]).strip()
        target = caller.search(query, location=caller.location)
        if not target:
            return
        if is_withdraw:
            ok, message = caller.withdraw_recovery_consent(target) if hasattr(caller, "withdraw_recovery_consent") else (False, "You cannot change recovery consent.")
        else:
            ok, message = caller.grant_recovery_consent(target, duration=duration) if hasattr(caller, "grant_recovery_consent") else (False, "You cannot change recovery consent.")
        caller.msg(message)
        if ok and target != caller:
            if is_withdraw:
                target.msg(f"{caller.key} withdraws permission for you to handle their remains.")
            else:
                target.msg(f"{caller.key} grants you permission to handle their remains.")