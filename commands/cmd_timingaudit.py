from commands.command import Command


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdTimingAudit(Command):
    """
    Inspect current timing registrations and timing audit warnings.

    Usage:
      timingaudit
    """

    key = "timingaudit"
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use timingaudit.")
            return

        from world.systems.timing_audit import collect_timing_audit, render_timing_audit_text

        self.caller.msg(render_timing_audit_text(collect_timing_audit()))