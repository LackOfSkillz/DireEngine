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