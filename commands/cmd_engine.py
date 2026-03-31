from commands.command import Command

from world.systems.engine_flags import get_flag_status_lines, is_enabled, set_flag


ADMIN_PERMISSIONS = ("Admin", "Developer")
INTEREST_FLAG = "interest_activation"


class CmdEngine(Command):
    """
    Inspect or change engine-owned runtime feature flags.

    Usage:
      @engine interest on
      @engine interest off
      @engine interest status
            @engine interest debug
      @engine interest
      @engine status
    """

    key = "@engine"
    aliases = ["engine"]
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def _caller_name(self):
        account = getattr(self.caller, "account", None)
        if account and getattr(account, "key", None):
            return account.key
        if getattr(self.caller, "key", None):
            return self.caller.key
        return "system"

    def _render_status(self):
        lines = ["Engine flags:"]
        lines.extend(f"  {line}" for line in get_flag_status_lines())
        self.caller.msg("\n".join(lines))

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use @engine.")
            return

        args = (self.args or "").strip().lower()
        if not args or args == "status":
            self._render_status()
            return

        parts = args.split()
        if not parts or parts[0] != "interest":
            self.caller.msg("Usage: @engine interest <on|off|status|debug> or @engine status")
            return

        action = parts[1] if len(parts) > 1 else "status"
        if action == "status":
            state = "ON" if is_enabled(INTEREST_FLAG) else "OFF"
            self.caller.msg(f"interest_activation is {state}.")
            return
        if action == "debug":
            from world.systems.interest import collect_interest_debug, render_interest_debug_text

            self.caller.msg(render_interest_debug_text(collect_interest_debug()))
            return
        if action not in {"on", "off"}:
            self.caller.msg("Usage: @engine interest <on|off|status|debug>")
            return

        enabled = set_flag(INTEREST_FLAG, action == "on", actor=self._caller_name())
        self.caller.msg(f"interest_activation is now {'ON' if enabled else 'OFF'}.")