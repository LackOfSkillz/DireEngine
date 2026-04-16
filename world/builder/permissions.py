from __future__ import annotations


def is_builder(user) -> bool:
    if user is None:
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    return bool(getattr(user, "is_builder", False))


def require_builder(user):
    if not is_builder(user):
        raise PermissionError("Builder access required")
    return user