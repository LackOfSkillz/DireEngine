from world.worlddata.services.export_zone_service import write_zone_export
from world.worlddata.services.import_zone_service import load_zone

from commands.command import Command


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdZone(Command):
    """
    Export and import authored world zones.

    Usage:
      @zone export <zone_id>
      @zone load <zone_id>
            @zone load <zone_id> --dry
            @zone load <zone_id> YES
    """

    key = "@zone"
    aliases = ["zone"]
    help_category = "Admin"

    def _format_summary(self, result: dict) -> str:
        if result.get("dry_run"):
            lines = [
                f"Zone dry-run: {result['zone_id']}",
                f"Rooms to create: {result['rooms']}",
                f"Exits to create: {result['exits']}",
                f"NPCs to place: {result['npcs']}",
                f"Items to place: {result['items']}",
            ]
        else:
            lines = [
                "Zone loaded:",
                f"{result['rooms']} rooms",
                f"{result['exits']} exits",
                f"{result['npcs']} NPCs",
                f"{result['items']} items",
                f"NPCs placed: {result['npcs']}",
                f"Items placed: {result['items']}",
                f"Containers linked: {result['containers_linked']}",
            ]
        for warning in list(result.get("warnings") or []):
            lines.append(f"Warning: {warning}")
        return "\n".join(lines)

    def _parse_load_args(self, raw_args: str) -> tuple[str, bool, bool]:
        tokens = [token for token in str(raw_args or "").strip().split() if token]
        if not tokens:
            raise ValueError("zone_id is required.")
        dry_run = any(token == "--dry" for token in tokens)
        confirmed = any(token.upper() == "YES" for token in tokens)
        zone_tokens = [token for token in tokens if token != "--dry" and token.upper() != "YES"]
        if len(zone_tokens) != 1:
            raise ValueError("Usage: @zone load <zone_id> [--dry] [YES]")
        return zone_tokens[0], dry_run, confirmed

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use @zone.")
            return

        parts = str(self.args or "").strip().split(None, 1)
        if len(parts) != 2:
            self.caller.msg("Usage: @zone export <zone_id> or @zone load <zone_id>")
            return

        action = parts[0].strip().lower()

        try:
            if action == "export":
                zone_id = parts[1].strip()
                if not zone_id:
                    self.caller.msg("zone_id is required.")
                    return
                output_path = write_zone_export(zone_id)
                self.caller.msg(f"Zone exported to {output_path}")
                return
            if action == "load":
                zone_id, dry_run, confirmed = self._parse_load_args(parts[1])
                if dry_run:
                    result = load_zone(zone_id, dry_run=True)
                    self.caller.msg(self._format_summary(result))
                    return

                pending_zone_id = str(getattr(self.caller.ndb, "pending_zone_load", "") or "").strip()
                if not confirmed or pending_zone_id != zone_id:
                    self.caller.ndb.pending_zone_load = zone_id
                    self.caller.msg("Type YES to confirm zone wipe:")
                    self.caller.msg(f"@zone load {zone_id} YES")
                    return

                self.caller.ndb.pending_zone_load = None
                result = load_zone(zone_id, dry_run=False)
                self.caller.msg(self._format_summary(result))
                return
        except Exception as error:
            self.caller.msg(str(error))
            return

        self.caller.msg("Unknown action. Use export or load.")