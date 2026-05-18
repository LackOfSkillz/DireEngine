import time

from django.core.exceptions import ObjectDoesNotExist
from django.db import close_old_connections

from evennia.objects.models import ObjectDB
from evennia.utils import logger


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
CHARACTER_TYPECLASS = "typeclasses.characters.Character"
PROCEDURAL_LANDING_AREAS = {"New Landing"}
PROCEDURAL_LANDING_BUILD_TAG = "new_landing"
CANONICAL_MIGRATION_MESSAGE = "The world shifts slightly, and you find yourself somewhere familiar yet new."


def _is_locked_database_error(error):
    return "database is locked" in str(error or "").lower()


def _with_locked_db_retry(action, *, attempts=4, retry_delay=0.1):
    last_error = None
    for attempt in range(attempts):
        close_old_connections()
        try:
            return action()
        except Exception as error:
            last_error = error
            if not _is_locked_database_error(error) or attempt + 1 >= attempts:
                raise
            time.sleep(retry_delay * (attempt + 1))
    raise last_error


def _delete_if_present(obj):
    if obj is None:
        return False

    def _delete():
        try:
            obj.delete()
        except ObjectDoesNotExist:
            return False
        return True

    return _with_locked_db_retry(_delete)


def _is_character_or_account_object(obj):
    if obj is None:
        return False
    if getattr(obj, "db_typeclass_path", "") == CHARACTER_TYPECLASS:
        return True
    return getattr(obj, "db_account_id", None) is not None


def _relocate_object(obj, destination):
    if obj is None or destination is None:
        return False

    try:
        return _with_locked_db_retry(lambda: obj.move_to(destination, quiet=True, use_destination=False))
    except Exception as error:
        if "nonetype" not in str(error or "").lower() and "session_handler" not in str(error or "").lower():
            raise

    def _set_location():
        obj.db_location = destination
        obj.save(update_fields=["db_location"])
        return True

    return _with_locked_db_retry(_set_location)


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
    try:
        build_tags = list(room.tags.get(category="build", return_list=True) or [])
    except Exception:
        build_tags = []
    if PROCEDURAL_LANDING_BUILD_TAG in build_tags:
        return True
    area_name = str(getattr(getattr(room, "db", None), "area", None) or "").strip()
    return area_name in PROCEDURAL_LANDING_AREAS


def iter_procedural_landing_rooms():
    rooms = []
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if is_procedural_landing_room(room):
            rooms.append(room)
    return rooms


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


def delete_procedural_landing_rooms(*, fallback=None):
    destination, destination_source = resolve_canonical_arrival_room(fallback=fallback)
    if destination is None:
        raise RuntimeError("Canonical arrival destination could not be resolved before procedural Landing deletion.")

    deleted_room_ids = []
    migrated_character_ids = []
    for room in iter_procedural_landing_rooms():
        if getattr(getattr(room, "db", None), "canonical_map_id", None) is not None:
            raise RuntimeError(f"Procedural Landing cleanup encountered canonical-tagged room {room.key}(#{room.id}).")
        for obj in list(getattr(room, "contents", []) or []):
            if getattr(obj, "db_typeclass_path", "") == EXIT_TYPECLASS:
                _delete_if_present(obj)
                continue
            if _is_character_or_account_object(obj):
                if getattr(obj, "location", None) == room:
                    _relocate_object(obj, destination)
                if is_procedural_landing_room(getattr(obj, "home", None)):
                    _with_locked_db_retry(lambda: setattr(obj, "home", destination))
                _with_locked_db_retry(lambda: setattr(obj.db, "prelogout_location", destination))
                _with_locked_db_retry(lambda: setattr(obj.db, "canonical_migrated", True))
                _with_locked_db_retry(lambda: setattr(obj.db, "canonical_migration_origin", room.id))
                migrated_character_ids.append(getattr(obj, "id", None))
                continue
            _delete_if_present(obj)
        _delete_if_present(room)
        deleted_room_ids.append(room.id)

    logger.log_info(
        f"Procedural Landing cleanup deleted {len(deleted_room_ids)} rooms and migrated {len(migrated_character_ids)} characters via {destination_source} arrival."
    )
    return {
        "deleted_room_ids": deleted_room_ids,
        "deleted_room_count": len(deleted_room_ids),
        "migrated_character_ids": migrated_character_ids,
        "migrated_character_count": len(migrated_character_ids),
        "destination_id": getattr(destination, "id", None),
    }