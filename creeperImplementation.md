# Creeper Command Implementation

Section 1 - Goal

This feature adds an admin-only `creeper` command that can start and stop player command logging without creating a second command-processing pipeline. Logged commands are appended to `creeperlog.md`, and the watched-target configuration persists across reloads by storing it in Evennia server configuration.

Section 2 - Files created

- `c:\Users\gary\dragonsire\utils\creeper.py`
  - Created to hold the persistent creeper configuration, markdown log writing, and central session-input interception helpers.
- `c:\Users\gary\dragonsire\commands\cmd_creeper.py`
  - Created to provide the admin-facing `creeper` command.
- `c:\Users\gary\dragonsire\creeperlog.md`
  - Created as the markdown append target for captured player commands.
- `c:\Users\gary\dragonsire\creeperImplementation.md`
  - Created to document the feature as a tutorial-style reproduction guide.

Section 3 - Files modified

- `c:\Users\gary\dragonsire\commands\default_cmdsets.py`
  - Modified to register `CmdCreeper` in the default character cmdset.
- `c:\Users\gary\dragonsire\server\conf\serversession.py`
  - Modified to intercept live session input in one central place and forward it to the creeper logger before normal Evennia processing continues.

Section 4 - Exact code added

## `utils/creeper.py`

```python
import os
from datetime import datetime

from django.conf import settings
from evennia.server.models import ServerConfig


CREEPER_CONFIG_KEY = "creeper_config"
CREEPER_LOG_PATH = os.path.join(settings.GAME_DIR, "creeperlog.md")


def _normalize_config(config):
    config = config or {}
    all_enabled = bool(config.get("all", False))
    players = config.get("players", []) or []
    normalized_players = sorted({str(player).strip().lower() for player in players if str(player).strip()})
    return {"all": all_enabled, "players": normalized_players}


def get_creeper_config():
    config = ServerConfig.objects.conf(key=CREEPER_CONFIG_KEY, default={"all": False, "players": []})
    return _normalize_config(config)


def save_creeper_config(config):
    normalized = _normalize_config(config)
    ServerConfig.objects.conf(key=CREEPER_CONFIG_KEY, value=normalized)
    return normalized


def start_creeper_for_player(player_name):
    config = get_creeper_config()
    watched = set(config["players"])
    watched.add(str(player_name).strip().lower())
    config["players"] = sorted(watched)
    return save_creeper_config(config)


def stop_creeper_for_player(player_name):
    config = get_creeper_config()
    watched = set(config["players"])
    watched.discard(str(player_name).strip().lower())
    config["players"] = sorted(watched)
    return save_creeper_config(config)


def set_creeper_all(enabled):
    config = get_creeper_config()
    config["all"] = bool(enabled)
    return save_creeper_config(config)


def stop_all_creeper():
    return save_creeper_config({"all": False, "players": []})


def is_creeper_logging_player(player_name):
    config = get_creeper_config()
    if config["all"]:
        return True
    return str(player_name).strip().lower() in set(config["players"])


def _extract_text_payload(payload):
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (list, tuple)):
        if not payload:
            return None
        first = payload[0]
        if isinstance(first, str):
            return first
        if isinstance(first, (list, tuple)) and first:
            nested = first[0]
            return nested if isinstance(nested, str) else None
    return None


def extract_raw_session_command(kwargs):
    if not isinstance(kwargs, dict):
        return None

    if "text" in kwargs:
        return _extract_text_payload(kwargs.get("text"))

    for key, value in kwargs.items():
        if key == "options":
            continue
        candidate = _extract_text_payload(value)
        if candidate:
            return candidate
    return None


def _get_session_player_name(session):
    puppet = session.get_puppet() if hasattr(session, "get_puppet") else None
    if puppet and getattr(puppet, "key", None):
        return puppet.key
    account = getattr(session, "account", None)
    if account and getattr(account, "username", None):
        return account.username
    return None


def _get_session_account_name(session):
    account = getattr(session, "account", None)
    if account and getattr(account, "username", None):
        return account.username
    return "(unloggedin)"


def should_log_session_command(session, raw_command):
    if not raw_command or not str(raw_command).strip():
        return False

    account = getattr(session, "account", None)
    if not account:
        return False

    player_name = _get_session_player_name(session)
    if not player_name:
        return False

    return is_creeper_logging_player(player_name)


def append_creeper_log(session, raw_command):
    player_name = _get_session_player_name(session) or "(unknown player)"
    account_name = _get_session_account_name(session)
    session_id = getattr(session, "sessid", None)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    command_text = str(raw_command).rstrip("\r\n")

    entry = (
        f"## {timestamp}\n"
        f"- Player: {player_name}\n"
        f"- Account: {account_name}\n"
        f"- Session: {session_id}\n"
        f"- Command: {command_text}\n\n"
    )

    with open(CREEPER_LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(entry)


def process_creeper_session_input(session, kwargs):
    raw_command = extract_raw_session_command(kwargs)
    if not should_log_session_command(session, raw_command):
        return
    append_creeper_log(session, raw_command)
```

## `commands/cmd_creeper.py`

```python
from evennia import Command
from evennia.accounts.models import AccountDB

from utils.creeper import get_creeper_config
from utils.creeper import set_creeper_all
from utils.creeper import start_creeper_for_player
from utils.creeper import stop_all_creeper
from utils.creeper import stop_creeper_for_player


ADMIN_PERMISSIONS = ("Admin", "Developer")


class CmdCreeper(Command):
    key = "creeper"
    help_category = "Admin"

    def _is_admin(self):
        account = getattr(self.caller, "account", None)
        if not account:
            return False
        return any(account.check_permstring(permission) for permission in ADMIN_PERMISSIONS)

    def _find_account_name(self, query):
        query = (query or "").strip()
        if not query:
            return None

        account = AccountDB.objects.filter(username__iexact=query).first()
        if account:
            return account.username

        for candidate in AccountDB.objects.all().order_by("id"):
            if str(candidate.username).lower().startswith(query.lower()):
                return candidate.username

        target = self.caller.search(query, global_search=True, quiet=True)
        if isinstance(target, list):
            target = target[0] if target else None
        if target and getattr(target, "account", None):
            return target.account.username
        if target and getattr(target, "key", None):
            return target.key
        return None

    def _render_status(self, config):
        watched = ", ".join(config.get("players", [])) or "none"
        all_enabled = "on" if config.get("all") else "off"
        return f"Creeper status: all={all_enabled}; watched={watched}."

    def func(self):
        if not self._is_admin():
            self.caller.msg("You are not permitted to use creeper.")
            return

        arg = (self.args or "").strip()
        if not arg:
            self.caller.msg(self._render_status(get_creeper_config()))
            self.caller.msg("Usage: creeper <playername> | creeper all | creeper stop <playername> | creeper stop all")
            return

        lowered = arg.lower()
        if lowered == "all":
            config = set_creeper_all(True)
            self.caller.msg("Creeper now logs commands for all players.")
            self.caller.msg(self._render_status(config))
            return

        if lowered == "stop all":
            config = stop_all_creeper()
            self.caller.msg("Creeper logging has been fully disabled.")
            self.caller.msg(self._render_status(config))
            return

        if lowered.startswith("stop "):
            player_name = self._find_account_name(arg[5:].strip())
            if not player_name:
                self.caller.msg("No matching player was found to stop logging.")
                return
            config = stop_creeper_for_player(player_name)
            self.caller.msg(f"Creeper stopped logging {player_name}.")
            self.caller.msg(self._render_status(config))
            return

        player_name = self._find_account_name(arg)
        if not player_name:
            self.caller.msg("No matching player was found to log.")
            return

        config = start_creeper_for_player(player_name)
        self.caller.msg(f"Creeper now logs commands for {player_name}.")
        self.caller.msg(self._render_status(config))
```

## `commands/default_cmdsets.py`

```python
from commands.cmd_creeper import CmdCreeper
```

```python
self.add(CmdCreeper())
```

## `server/conf/serversession.py`

```python
from utils.creeper import process_creeper_session_input
```

```python
class ServerSession(BaseServerSession):
    def data_in(self, **kwargs):
        process_creeper_session_input(self, kwargs)
        return super().data_in(**kwargs)
```

Section 5 - Hook point explanation

Command interception happens in `server/conf/serversession.py` by overriding `ServerSession.data_in`. This location was chosen because the repo already uses a custom server session class in `server/conf/settings.py`, and `data_in` is the central point where live session input reaches the server before command execution. This keeps the feature additive, avoids modifying every command, and avoids logging NPC `execute_cmd` traffic because NPCs do not send input through live sessions.

Section 6 - Command behavior

- `creeper jekar`
  - Adds `jekar` to the watched-player set without removing any existing watched player.
- `creeper all`
  - Enables global logging for all live players.
- `creeper stop jekar`
  - Removes only `jekar` from the watched-player set.
- `creeper stop all`
  - Clears all watched players and disables global logging.

Section 7 - Logging format

Sample log entry:

```md
## 2026-03-27 14:33:12
- Player: jekar
- Account: jekar
- Session: 3
- Command: attack goblin
```

Section 8 - Testing steps

1. Reload the game server.
2. As an admin character, run `creeper jekar`.
3. From Jekar's live session, type a command such as `look`.
4. Open `creeperlog.md` and confirm the command appended.
5. Run `creeper aiden` and repeat with Aiden.
6. Confirm both players now append entries independently.
7. Run `creeper stop jekar`.
8. Confirm Jekar stops appending while Aiden still appends.
9. Run `creeper all`.
10. Confirm any live player command appends.
11. Run `creeper stop all`.
12. Confirm logging stops entirely.
13. Reload the server and re-run `creeper` with no args to confirm the watched configuration persisted.

Section 9 - Porting notes for another Evennia project

To port this into another Evennia game:

1. Copy `utils/creeper.py` into a utility module in the target project.
2. Copy `commands/cmd_creeper.py` into the target command package.
3. Register the command in the target cmdset.
4. Make sure the target game uses a custom `SERVER_SESSION_CLASS`.
5. Add the `data_in` interception call to that custom session class.
6. If the target game uses different admin permissions, replace `("Admin", "Developer")` with the correct permission names.
7. If the target game wants a different logfile location, change `CREEPER_LOG_PATH`.
8. If the target game identifies players by account ID instead of username, replace the watched-player storage format accordingly.

Persistence note:

This implementation stores creeper configuration in Evennia `ServerConfig`, so the watched targets survive reloads.