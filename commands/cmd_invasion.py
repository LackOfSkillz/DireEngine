"""@invasion admin command - inspect and set per-zone invasion state."""

from commands.command import Command
from world.invasion import (
    get_current_invasion,
    get_invasion_state,
    list_invasion_types,
    set_current_invasion,
)


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdInvasion(Command):
    """
    Inspect and set per-zone invasion state.

    Usage:
      @invasion
      @invasion --types
      @invasion <zone_id>
      @invasion <zone_id> <type>
    """

    key = "@invasion"
    help_category = "Admin"
    locks = "cmd:perm(Admin) or perm(Developer)"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You do not have permission to use this command.")
            return

        args = [part for part in str(self.args or "").split() if part]
        if not args:
            self._show_all()
            return
        if len(args) == 1 and args[0].strip().lower() in {"--types", "types"}:
            self._show_types()
            return
        if len(args) == 1:
            self._show_zone(args[0])
            return
        self._set_zone(args[0], args[1])

    def _show_all(self):
        state = get_invasion_state()
        lines = [
            "DireEngine Invasions",
            "─" * 40,
        ]
        for zone in state["zones"]:
            status = "active" if zone["active"] else "inactive"
            lines.append(f"{zone['zone_id'] + ':':18}{zone['invasion']:<18} ({status})")
        lines.extend(["", "Active states:"])
        for invasion_type, count in state["counts"].items():
            lines.append(f"  {invasion_type + ':':18}{count}")
        self.caller.msg("\n".join(lines))

    def _show_types(self):
        self.caller.msg("Valid invasion types: " + ", ".join(list_invasion_types()))

    def _show_zone(self, zone_id):
        state = get_invasion_state()
        for zone in state["zones"]:
            if zone["zone_id"].lower() != str(zone_id).strip().lower():
                continue
            meta = dict(zone.get("meta") or {})
            lines = [
                f"Invasion: {zone['zone_id']}",
                "─" * 32,
                f"Current state:   {zone['invasion']}",
                f"Zone name:       {zone['name']}",
                f"Is invaded:      {'yes' if zone['active'] else 'no'}",
                f"Updated by:      {meta.get('source') or 'unknown'}",
                f"Updated at:      {meta.get('updated_at') or 'unknown'}",
            ]
            self.caller.msg("\n".join(lines))
            return
        self.caller.msg(f"Unknown zone: {zone_id}")

    def _set_zone(self, zone_id, invasion_type):
        set_current_invasion(zone_id, invasion_type, source="admin")
        self.caller.msg(f"Invasion for {zone_id} set to {get_current_invasion(zone_id)}.")