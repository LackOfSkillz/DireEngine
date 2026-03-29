from commands.command import Command
from world.area_forge.utils.messages import send_structured


class CmdTestGodot(Command):
    """Send a structured websocket payload to attached Godot sessions."""

    key = "testgodot"
    aliases = ["testmap"]
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        mode = (self.args or "ping").strip().lower()

        if mode == "map":
            payload_type = "map"
            payload = {
                "rooms": [{"id": 0, "x": 0, "y": 0, "name": "Origin", "is_player": True}],
                "edges": [],
                "player_room_id": 0,
            }
        else:
            payload_type = "ping"
            payload = {"ok": True}

        sent = send_structured(self.caller, payload_type, payload)
        if sent:
            self.caller.msg(f"Sent {payload_type} payload to {sent} Godot websocket session(s).")
        else:
            self.caller.msg("No Godot websocket sessions are attached to this caller.")