import time


JAIL_ROOM_ID = 9999


def is_in_custody(player):
    return bool(getattr(getattr(player, "db", None), "is_in_custody", False))


def is_jailed(player):
    return bool(getattr(getattr(player, "db", None), "is_jailed", False))


def enter_custody(player, guard_id, room_id, now):
    if player is None:
        return False
    db_state = getattr(player, "db", None)
    if db_state is None:
        return False
    db_state.is_in_custody = True
    db_state.custody_guard_id = int(guard_id or 0) or None
    db_state.custody_started_at = float(now or time.time())
    db_state.custody_location_id = int(room_id or 0) or None
    return True


def clear_custody(player):
    if player is None:
        return False
    db_state = getattr(player, "db", None)
    if db_state is None:
        return False
    db_state.is_in_custody = False
    db_state.custody_guard_id = None
    db_state.custody_started_at = 0.0
    db_state.custody_location_id = None
    return True


def enter_jail(player, now):
    if player is None:
        return False
    db_state = getattr(player, "db", None)
    if db_state is None:
        return False
    db_state.is_jailed = True
    db_state.jail_entered_at = float(now or time.time())
    return True


def release_player(player):
    if player is None:
        return False
    db_state = getattr(player, "db", None)
    if db_state is None:
        return False
    db_state.is_jailed = False
    db_state.jail_entered_at = 0.0
    return True