Phase 0 Godot Transport Checklist

Use this only for MT1001-MT1005 validation. Do not start map or UI work until every item below passes.

1. Restart Evennia after the settings change so the portal service picks up the Godot websocket plugin.
2. Confirm the portal is listening on ws://127.0.0.1:4008.
3. In Godot 4, create a minimal scene with a root Node and attach Phase0TestClient.gd.
4. Run the scene and confirm the Output panel prints a connection attempt.
5. In Evennia, connect a character normally and run testgodot.
6. In Godot, capture the exact RAW packet and verify it parses as a JSON array.
7. Confirm the normalized packet shape is:

   {
     "cmd": <string>,
     "args": <array>,
     "kwargs": <dictionary>
   }

8. In Evennia, run testgodot map and confirm the Godot client prints an OOB-style packet with cmd map.
9. In Godot, press Enter to trigger send_command("look").
10. Confirm Evennia executes look and that the response comes back to Godot as a text packet.

Freeze these contracts before proceeding:

- Server message format: JSON array [cmd, args, kwargs]
- Client command format: JSON array ["text", [command_string], {}]

If any step fails:

- If connection fails, re-check server/conf/settings.py and restart both server and portal.
- If RAW payload is not JSON, stop and inspect the active websocket endpoint and port.
- If ping arrives but look does not execute, verify the client is sending ["text", ["look"], {}] exactly.
- If look executes but nothing returns, inspect session/protocol routing before touching MT1006+.