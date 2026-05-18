from evennia.utils import logger


PROCEDURAL_LANDING_AREAS = {"The Landing", "New Landing"}
CANONICAL_MIGRATION_MESSAGE = "The world shifts slightly, and you find yourself somewhere familiar yet new."


def resolve_canonical_arrival_room(fallback=None):
    destination = None
    try:
        from server.conf.at_server_startstop import _resolve_landing_arrival_room

        destination = _resolve_landing_arrival_room()
    except Exception:
        destination = None
    if destination:
        return destination, "canonical"

    fallback_room = fallback() if callable(fallback) else fallback
    if fallback_room:
        return fallback_room, "fallback"
    return None, "missing"


def is_procedural_landing_room(room):
    if room is None:
        return False
    if getattr(getattr(room, "db", None), "canonical_map_id", None) is not None:
        return False
    if bool(getattr(getattr(room, "db", None), "is_canonical_crossing", False)):
        return False
    area_name = str(getattr(getattr(room, "db", None), "area", None) or "").strip()
    return area_name in PROCEDURAL_LANDING_AREAS


def migrate_character_to_canonical_arrival(character, *, session=None, fallback=None):
    if not character:
        return False, None

    current_room = getattr(character, "location", None)
    already_migrated = bool(getattr(getattr(character, "db", None), "canonical_migrated", False))
    if already_migrated and not is_procedural_landing_room(current_room):
        return False, current_room
    if not is_procedural_landing_room(current_room):
        return False, current_room

    destination, destination_source = resolve_canonical_arrival_room(fallback=fallback)
    if destination is None:
        return False, None

    origin_room = current_room
    if current_room != destination:
        character.move_to(destination, quiet=True, use_destination=False)
    if is_procedural_landing_room(getattr(character, "home", None)):
        character.home = destination
    character.db.prelogout_location = destination
    character.db.canonical_migrated = True
    character.db.canonical_migration_origin = getattr(origin_room, "id", None)
    try:
        character.msg(CANONICAL_MIGRATION_MESSAGE, session=session)
    except TypeError:
        character.msg(CANONICAL_MIGRATION_MESSAGE)
    logger.log_info(
        f"Canonical arrival migration moved {getattr(character, 'key', 'unknown')} from {getattr(origin_room, 'key', 'unknown')}"
        f"(#{getattr(origin_room, 'id', 'unknown')}) to {getattr(destination, 'key', 'unknown')}"
        f"(#{getattr(destination, 'id', 'unknown')}) via {destination_source} arrival"
    )
    return True, destination