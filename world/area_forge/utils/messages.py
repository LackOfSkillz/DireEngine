"""Structured websocket messaging helpers for browser and Godot clients."""


SUPPORTED_PROTOCOL_KEYS = {
    "godotclient/websocket",
    "webclient/websocket",
    "websocket",
    "ajax",
}


def _supports_structured_session(session):
    protocol_key = str(getattr(session, "protocol_key", "") or "").lower()
    if protocol_key in SUPPORTED_PROTOCOL_KEYS:
        return True
    if protocol_key.startswith("webclient/"):
        return True
    return bool(getattr(session, "csessid", None))


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def send_structured(caller, msg_type, data, session=None, **kwargs):
    payload = _json_safe(data)

    if session:
        sessions = [session]
    else:
        sessions_attr = getattr(caller, "sessions", None)
        sessions = list(sessions_attr.all()) if sessions_attr else []

    sent = 0
    for active_session in sessions:
        if not _supports_structured_session(active_session):
            continue
        active_session.data_out(**{msg_type: ([payload], kwargs)})
        sent += 1

    return sent