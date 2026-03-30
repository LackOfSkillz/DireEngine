from collections.abc import Mapping


DEFAULT_RANGER_COMPANION = {
    "type": "wolf",
    "state": "inactive",
    "bond": 50,
}

VALID_COMPANION_TYPES = {"wolf"}
VALID_COMPANION_STATES = {"inactive", "active"}


def normalize_ranger_companion(data=None):
    payload = dict(DEFAULT_RANGER_COMPANION)
    if isinstance(data, Mapping):
        payload.update(data)
    companion_type = str(payload.get("type", "wolf") or "wolf").strip().lower()
    if companion_type not in VALID_COMPANION_TYPES:
        companion_type = "wolf"
    state = str(payload.get("state", "inactive") or "inactive").strip().lower()
    if state not in VALID_COMPANION_STATES:
        state = "inactive"
    bond = max(0, min(100, int(payload.get("bond", 50) or 0)))
    return {
        "type": companion_type,
        "state": state,
        "bond": bond,
    }


def is_companion_active(data=None):
    return normalize_ranger_companion(data).get("state") == "active"


def get_companion_tracking_bonus(data=None):
    companion = normalize_ranger_companion(data)
    if companion["state"] != "active":
        return 0
    return 4 + int(companion["bond"] / 25)


def get_companion_awareness_bonus(data=None):
    companion = normalize_ranger_companion(data)
    if companion["state"] != "active":
        return 0
    return 2 + int(companion["bond"] / 34)


def get_companion_label(data=None):
    return str(normalize_ranger_companion(data).get("type", "wolf") or "wolf").replace("_", " ").title()