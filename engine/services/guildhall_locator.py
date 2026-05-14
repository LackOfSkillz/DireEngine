"""Per-profession guildhall room locator."""

_GUILDHALL_REGISTRY = {
    "empath": "Empath Guild",
    "cleric": "Cleric Guild",
    "ranger": "Ranger Guild",
}


def register_guildhall(profession_key, room_key):
    _GUILDHALL_REGISTRY[str(profession_key or "").strip().lower()] = str(room_key or "").strip()


def get_guildhall_room_key(profession_key):
    return _GUILDHALL_REGISTRY.get(str(profession_key or "").strip().lower())


def list_available_guildhalls():
    return dict(_GUILDHALL_REGISTRY)