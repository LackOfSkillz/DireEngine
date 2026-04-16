from __future__ import annotations

from time import time
from uuid import uuid4


SESSION_AVAILABLE = True
_SESSIONS: dict[str, dict] = {}


def _normalize_user(user) -> str:
    if isinstance(user, str):
        username = user.strip()
    else:
        username = str(getattr(user, "username", "") or "").strip()
    if not username:
        raise ValueError("user is required.")
    return username


def create_session(user, area_id) -> dict:
    username = _normalize_user(user)
    normalized_area_id = str(area_id or "").strip()
    if not normalized_area_id:
        raise ValueError("area_id is required.")

    session = {
        "session_id": str(uuid4()),
        "user": username,
        "area_id": normalized_area_id,
        "created_at": time(),
    }
    _SESSIONS[session["session_id"]] = dict(session)
    return dict(session)


def get_session(session_id) -> dict | None:
    normalized_session_id = str(session_id or "").strip()
    if not normalized_session_id:
        return None
    session = _SESSIONS.get(normalized_session_id)
    return dict(session) if isinstance(session, dict) else None