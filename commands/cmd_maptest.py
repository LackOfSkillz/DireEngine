from commands.command import Command
from world.area_forge.map_api import send_map_update


class CmdMapTest(Command):
    """Send the current browser map payload without moving.

    Usage:
      maptest
      maptest local
      maptest zone
    """

    key = "maptest"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        mode = (self.args or "zone").strip().lower() or "zone"
        if mode not in {"local", "zone"}:
            self.caller.msg("Usage: maptest [local|zone]")
            return

        payload = send_map_update(self.caller, mode=mode)
        self.caller.msg(
            f"Sent {mode} map payload with {len(payload.get('rooms', []))} rooms and {len(payload.get('edges', []))} exits."
        )