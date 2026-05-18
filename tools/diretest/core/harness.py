"""Temporary object factories for DireTest runs."""

from __future__ import annotations

import inspect
import time
from uuid import uuid4

from django.conf import settings
from django.db import close_old_connections
from evennia.utils import logger

from .leaks import detect_leaks
from .snapshot_schema import LEAK_KEY_PREFIX


def _object_exists(obj):
    from evennia.objects.models import ObjectDB

    object_id = int(getattr(obj, "id", 0) or 0)
    return object_id > 0 and ObjectDB.objects.filter(id=object_id).exists()


def _is_database_locked(error):
    return "database is locked" in str(error or "").lower()


def _is_already_deleted(error):
    return "already deleted" in str(error or "").lower()


def _get_fresh_object(obj):
    from evennia.objects.models import ObjectDB

    object_id = int(getattr(obj, "id", 0) or 0)
    if object_id <= 0:
        return None
    return ObjectDB.objects.filter(id=object_id).first()


def _canonical_marker_details(obj):
    source = _get_fresh_object(obj) or obj
    db = getattr(source, "db", None)
    return {
        "canonical_map_id": getattr(db, "canonical_map_id", None),
        "canonical_phase": getattr(db, "canonical_phase", None),
        "canonical_source": getattr(db, "canonical_source", None),
    }


def _is_room_object(obj):
    source = _get_fresh_object(obj) or obj
    typeclass_path = str(getattr(source, "db_typeclass_path", "") or "")
    return typeclass_path.endswith("typeclasses.rooms.Room") or typeclass_path.endswith("rooms.Room")


def _is_canonical_room(obj):
    return _is_room_object(obj) and _canonical_marker_details(obj)["canonical_map_id"] is not None


def _is_canonical_protected(obj):
    details = _canonical_marker_details(obj)
    return _is_room_object(obj) and any(details.values())


def _find_test_caller():
    for frame_info in inspect.stack()[2:]:
        filename = str(getattr(frame_info, "filename", "") or "")
        if "\\tests\\" not in filename.lower() and "/tests/" not in filename.lower():
            continue
        function_name = str(getattr(frame_info, "function", "") or "")
        if function_name.startswith("test_"):
            return f"{filename}:{function_name}"
    return "unknown test caller"


def _log_canonical_protection(obj, source):
    details = _canonical_marker_details(obj)
    logger.log_warn(
        "[DireTest] Skipping canonical-protected object during "
        f"{source}: id={int(getattr(obj, 'id', 0) or 0)} "
        f"key={str(getattr(obj, 'key', '') or '')!r} "
        f"canonical_map_id={details['canonical_map_id']!r} "
        f"canonical_phase={details['canonical_phase']!r} "
        f"caller={_find_test_caller()}"
    )


def _attribute_has_live_links(attribute):
    for accessor in ("objectdb_set", "accountdb_set", "channeldb_set", "scriptdb_set"):
        relation = getattr(attribute, accessor, None)
        if relation is not None and relation.exists():
            return True
    return False


def _detach_object_attributes(obj):
    from evennia.typeclasses.models import Attribute

    fresh_obj = _get_fresh_object(obj)
    if fresh_obj is None:
        return []

    attribute_ids = [
        int(attribute.id)
        for attribute in list(fresh_obj.db_attributes.all())
        if int(getattr(attribute, "id", 0) or 0) > 0
    ]
    if not attribute_ids:
        return []

    fresh_obj.db_attributes.remove(*attribute_ids)
    for attribute in list(Attribute.objects.filter(id__in=attribute_ids)):
        if _attribute_has_live_links(attribute):
            continue
        attribute.delete()
    return attribute_ids


def _iter_child_objects(obj):
    from evennia.objects.models import ObjectDB

    fresh_obj = _get_fresh_object(obj)
    if fresh_obj is None:
        return []

    object_id = int(getattr(fresh_obj, "id", 0) or 0)
    contents = list(getattr(fresh_obj, "contents", []) or [])
    outgoing_exits = [child for child in contents if getattr(child, "db_destination", None)]
    incoming_exits = list(ObjectDB.objects.filter(db_destination=fresh_obj).exclude(id=object_id))
    nested_contents = [child for child in contents if not getattr(child, "db_destination", None)]

    children = []
    seen_ids = set()
    for child in outgoing_exits + incoming_exits + nested_contents:
        child_id = int(getattr(child, "id", 0) or 0)
        if child_id <= 0 or child_id == object_id or child_id in seen_ids:
            continue
        seen_ids.add(child_id)
        children.append(child)
    return children


def _ensure_evennia_command_aliases():
    import evennia

    if not bool(getattr(evennia, "_LOADED", False)):
        evennia._init()


def _initialize_character_cmdsets(character):
    _ensure_evennia_command_aliases()

    cmdset_paths = list(getattr(character, "cmdset_storage", []) or [])
    default_cmdset = str(getattr(settings, "CMDSET_CHARACTER", "") or "").strip()
    if default_cmdset and default_cmdset not in cmdset_paths:
        cmdset_paths.insert(0, default_cmdset)
        character.cmdset_storage = cmdset_paths

    character.cmdset.update(init_mode=True)


def cleanup_test_objects(target_ids=None, max_attempts=3, retry_delay=0.1):
    from evennia.objects.models import ObjectDB

    target_id_set = {int(object_id) for object_id in list(target_ids or []) if int(object_id or 0) > 0}
    deleted_ids = set()
    failures = []

    for attempt in range(max_attempts):
        close_old_connections()
        query = ObjectDB.objects.filter(db_key__startswith=LEAK_KEY_PREFIX).order_by("-id")
        if target_id_set:
            query = query.filter(id__in=list(target_id_set))
        leaked_objects = list(query)
        if not leaked_objects:
            break

        failures = []
        for obj in leaked_objects:
            ok, failure = safe_delete(obj, max_attempts=1)
            if ok:
                deleted_ids.add(int(getattr(obj, "id", 0) or 0))
            elif failure:
                failures.append(failure)

        if not failures:
            break

        if attempt + 1 < max_attempts and all(_is_database_locked(failure.get("error")) for failure in failures):
            time.sleep(retry_delay * (attempt + 1))
            continue
        break

    remaining = detect_leaks()
    if target_id_set:
        remaining = [entry for entry in remaining if int(entry.get("id", 0) or 0) in target_id_set]
    return {
        "deleted_ids": sorted(object_id for object_id in deleted_ids if object_id > 0),
        "deletion_failures": failures,
        "remaining": remaining,
    }


def safe_delete(obj, max_attempts=3, retry_delay=0.1, recurse=True, _visited=None):
    """Delete a tracked object without stopping teardown on failure."""

    if obj is None:
        return True, None

    object_id = int(getattr(obj, "id", 0) or 0)
    if object_id <= 0:
        return True, None

    if _visited is None:
        _visited = set()
    if object_id in _visited:
        return True, None
    _visited.add(object_id)

    if not _object_exists(obj):
        return True, None

    if _is_canonical_protected(obj):
        _log_canonical_protection(obj, "safe_delete")
        return True, None

    if recurse:
        for child in _iter_child_objects(obj):
            ok, failure = safe_delete(
                child,
                max_attempts=max_attempts,
                retry_delay=retry_delay,
                recurse=True,
                _visited=_visited,
            )
            if not ok:
                return False, failure

    last_error = None
    for attempt in range(max_attempts):
        close_old_connections()
        try:
            _detach_object_attributes(obj)
            obj.delete()
        except Exception as error:
            last_error = error
            if _is_already_deleted(error):
                return True, None
            if _is_database_locked(error) and attempt + 1 < max_attempts:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return False, {
                "id": object_id,
                "key": str(getattr(obj, "key", "") or ""),
                "stage": "delete",
                "error": str(error),
            }

        close_old_connections()
        if not _object_exists(obj):
            return True, None
        last_error = RuntimeError("Object still exists after delete().")
        if attempt + 1 < max_attempts:
            time.sleep(retry_delay * (attempt + 1))

    return False, {
        "id": object_id,
        "key": str(getattr(obj, "key", "") or ""),
        "stage": "delete",
        "error": str(last_error),
    }


class DireTestHarness:
    """Create and track temporary test fixtures for a scenario run."""

    def __init__(self):
        self.created_objects = []
        self.deletion_failures = []
        self.leaks = []

    def _build_name(self, prefix):
        return f"{prefix}{uuid4().hex[:8].upper()}"

    def create_test_room(self, key=None):
        from evennia.utils.create import create_object

        room = create_object("typeclasses.rooms.Room", key=str(key or self._build_name("TEST_ROOM_")), nohome=True)
        self.created_objects.append(room)
        return room

    def create_test_character(self, room=None, key=None):
        from evennia.utils.create import create_object

        target_room = room or self.create_test_room()
        character = create_object(
            "typeclasses.characters.Character",
            key=str(key or self._build_name("TEST_CHAR_")),
            location=target_room,
            home=target_room,
        )
        _initialize_character_cmdsets(character)
        self.created_objects.append(character)
        return character

    def create_test_object(self, key=None, location=None, typeclass="typeclasses.objects.Object", **attributes):
        from evennia.utils.create import create_object

        obj = create_object(typeclass, key=str(key or self._build_name("TEST_OBJ_")), location=location)
        for attr_name, attr_value in dict(attributes or {}).items():
            setattr(obj.db, str(attr_name), attr_value)
        self.created_objects.append(obj)
        return obj

    def create_test_exit(self, location, destination, key, aliases=None):
        from evennia.utils.create import create_object

        exit_obj = create_object(
            "typeclasses.exits.Exit",
            key=str(key),
            location=location,
            destination=destination,
            aliases=list(aliases or []),
        )
        self.created_objects.append(exit_obj)
        return exit_obj

    def track_object(self, obj):
        if obj is not None and obj not in self.created_objects:
            self.created_objects.append(obj)
        return obj

    def teardown(self):
        """Delete tracked objects, clear references, and record any leaks."""

        self.deletion_failures = []
        self.leaks = []
        tracked_ids = [int(getattr(obj, "id", 0) or 0) for obj in list(self.created_objects or [])]

        for obj in reversed(list(self.created_objects or [])):
            ok, failure = safe_delete(obj)
            if not ok and failure:
                self.deletion_failures.append(failure)

        cleanup = cleanup_test_objects(target_ids=tracked_ids)
        self.deletion_failures.extend(list(cleanup.get("deletion_failures", []) or []))

        self.created_objects = []
        self.leaks = detect_leaks()
        return {
            "deletion_failures": list(self.deletion_failures),
            "leaks": list(self.leaks),
        }