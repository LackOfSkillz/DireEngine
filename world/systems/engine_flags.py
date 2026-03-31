from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from evennia.server.models import ServerConfig
from evennia.utils import logger


ENGINE_FLAGS = {
    "interest_activation": False,
}

ENGINE_FLAGS_CONFIG_KEY = "engine_flags"


def _normalize_flags(raw_flags=None):
    normalized = deepcopy(ENGINE_FLAGS)
    if isinstance(raw_flags, Mapping):
        for key in ENGINE_FLAGS:
            if key in raw_flags:
                normalized[key] = bool(raw_flags.get(key))
    return normalized


def get_flags():
    stored = ServerConfig.objects.conf(key=ENGINE_FLAGS_CONFIG_KEY, default=None)
    return _normalize_flags(stored)


def is_enabled(flag: str) -> bool:
    normalized_flag = str(flag or "").strip().lower()
    if normalized_flag not in ENGINE_FLAGS:
        raise KeyError(f"Unknown engine flag: {flag}")
    return bool(get_flags().get(normalized_flag, False))


def set_flag(flag: str, value: bool, actor=None) -> bool:
    normalized_flag = str(flag or "").strip().lower()
    if normalized_flag not in ENGINE_FLAGS:
        raise KeyError(f"Unknown engine flag: {flag}")

    flags = get_flags()
    normalized_value = bool(value)
    flags[normalized_flag] = normalized_value
    ServerConfig.objects.conf(key=ENGINE_FLAGS_CONFIG_KEY, value=flags)

    actor_name = str(actor or "system").strip() or "system"
    state = "ENABLED" if normalized_value else "DISABLED"
    logger.log_info(f"[Engine] {normalized_flag} {state} by {actor_name}")
    return normalized_value


def get_flag_status_lines():
    flags = get_flags()
    return [
        f"{name}: {'ON' if bool(enabled) else 'OFF'}"
        for name, enabled in sorted(flags.items())
    ]