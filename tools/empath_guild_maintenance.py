import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

    import django

    django.setup()

    import evennia

    if not bool(getattr(evennia, "_LOADED", False)):
        evennia._init()


def _find_tagged_room(ObjectDB, room_typeclass, tag_key):
    if not tag_key:
        return None
    for room in ObjectDB.objects.filter(db_typeclass_path=room_typeclass):
        try:
            if room.tags.has(str(tag_key)):
                return room
        except Exception:
            continue
    return None


def _get_lane_room(ObjectDB):
    room = ObjectDB.objects.get_id(4280)
    if room and str(getattr(room, "key", "") or "") == "Larkspur Lane, Midway":
        return room
    return None


def _resolve_authoritative_guild(ObjectDB, room_typeclass):
    tagged_room = _find_tagged_room(ObjectDB, room_typeclass, "guild_empath")
    if tagged_room:
        lane_room = _get_lane_room(ObjectDB)
        guild_exit = ObjectDB.objects.filter(db_key__iexact="guild", db_location=lane_room).first() if lane_room else None
        return tagged_room, lane_room, guild_exit
    lane_room = _get_lane_room(ObjectDB)
    if lane_room:
        guild_exit = ObjectDB.objects.filter(db_key__iexact="guild", db_location=lane_room).first()
        destination = getattr(guild_exit, "destination", None)
        if destination:
            return destination, lane_room, guild_exit
    return tagged_room, lane_room, None


def _collect_empath_guild_rooms(ObjectDB, room_typeclass):
    rooms = []
    seen_ids = set()
    for room in ObjectDB.objects.filter(db_typeclass_path=room_typeclass, db_key__iexact="Empath Guild"):
        if room.id in seen_ids:
            continue
        rooms.append(room)
        seen_ids.add(room.id)
    tagged_room = _find_tagged_room(ObjectDB, room_typeclass, "guild_empath")
    if tagged_room and tagged_room.id not in seen_ids:
        rooms.append(tagged_room)
        seen_ids.add(tagged_room.id)
    return rooms


def _room_payload(room, canonical_id=None):
    if not room:
        return None
    tags = []
    try:
        tags = sorted(str(tag_key) for tag_key in list(room.tags.all()) if tag_key)
    except Exception:
        tags = []
    contents = []
    try:
        contents = sorted(str(getattr(obj, "key", "") or "") for obj in list(getattr(room, "contents", []) or []))
    except Exception:
        contents = []
    return {
        "id": int(room.id),
        "key": str(getattr(room, "key", "") or ""),
        "is_canonical": bool(canonical_id and int(room.id) == int(canonical_id)),
        "tags": tags,
        "contents": contents,
    }


def _object_payload(obj):
    if not obj:
        return None
    return {
        "id": int(obj.id),
        "key": str(getattr(obj, "key", "") or ""),
        "typeclass": str(getattr(obj, "db_typeclass_path", "") or ""),
        "location_id": int(getattr(getattr(obj, "location", None), "id", 0) or 0) or None,
    }


def _deprecate_duplicates(duplicates):
    changed = []
    for room in duplicates:
        room.tags.add("deprecated_duplicate_room")
        room.tags.add("deprecated_empath_guild")
        room.db.deprecated_reason = "Duplicate Empath Guild room superseded by authoritative lane exit destination."
        room.db.deprecated_at = float(__import__("time").time())
        changed.append(int(room.id))
    return changed


def _delete_duplicates(duplicates):
    deleted = []
    skipped = []
    for room in duplicates:
        contents = [obj for obj in list(getattr(room, "contents", []) or []) if str(getattr(obj, "key", "") or "").lower() != "out"]
        if contents:
            skipped.append({
                "id": int(room.id),
                "reason": "room still has non-exit contents",
                "contents": sorted(str(getattr(obj, "key", "") or "") for obj in contents),
            })
            continue
        room.delete()
        deleted.append(int(room.id))
    return deleted, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit and maintain duplicate Empath Guild rooms.")
    parser.add_argument("--deprecate", action="store_true", help="Tag non-canonical Empath Guild rooms as deprecated.")
    parser.add_argument("--delete", action="store_true", help="Delete non-canonical Empath Guild rooms that no longer contain non-exit contents.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    if args.deprecate and args.delete:
        parser.error("Choose either --deprecate or --delete, not both.")

    _setup_django()

    from evennia.objects.models import ObjectDB

    room_typeclass = "typeclasses.rooms.Room"
    canonical_room, lane_room, lane_guild_exit = _resolve_authoritative_guild(ObjectDB, room_typeclass)
    all_rooms = _collect_empath_guild_rooms(ObjectDB, room_typeclass)
    canonical_id = int(getattr(canonical_room, "id", 0) or 0) or None
    duplicates = [room for room in all_rooms if canonical_id and int(room.id) != canonical_id]
    non_room_matches = list(ObjectDB.objects.filter(db_key__iexact="Empath Guild").exclude(db_typeclass_path=room_typeclass))

    result = {
        "canonical_room": _room_payload(canonical_room, canonical_id=canonical_id),
        "lane_room": _room_payload(lane_room, canonical_id=canonical_id),
        "lane_exit_destination_id": int(getattr(getattr(lane_guild_exit, "destination", None), "id", 0) or 0) or None,
        "duplicate_rooms": [_room_payload(room, canonical_id=canonical_id) for room in duplicates],
        "same_name_non_room_objects": [_object_payload(obj) for obj in non_room_matches],
        "action": "audit",
        "changed_ids": [],
        "deleted_ids": [],
        "skipped": [],
    }

    if args.deprecate:
        result["action"] = "deprecate"
        result["changed_ids"] = _deprecate_duplicates(duplicates)
    elif args.delete:
        result["action"] = "delete"
        deleted_ids, skipped = _delete_duplicates(duplicates)
        result["deleted_ids"] = deleted_ids
        result["skipped"] = skipped

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print("Empath Guild Maintenance")
    if result["canonical_room"]:
        print(f"Canonical Room: {result['canonical_room']['key']}(#{result['canonical_room']['id']})")
    else:
        print("Canonical Room: missing")
    print(f"Lane Exit Destination: {result['lane_exit_destination_id']}")
    print(f"Duplicate Count: {len(result['duplicate_rooms'])}")
    for entry in result["duplicate_rooms"]:
        print(f"- Duplicate: {entry['key']}(#{entry['id']}) tags={','.join(entry['tags']) or '(none)'}")
    if result["same_name_non_room_objects"]:
        print(f"Same-name Non-room Objects: {len(result['same_name_non_room_objects'])}")
        for entry in result["same_name_non_room_objects"]:
            print(
                f"- Collision: {entry['key']}(#{entry['id']}) typeclass={entry['typeclass']} location_id={entry['location_id']}"
            )
    if result["changed_ids"]:
        print(f"Deprecated: {', '.join(str(room_id) for room_id in result['changed_ids'])}")
    if result["deleted_ids"]:
        print(f"Deleted: {', '.join(str(room_id) for room_id in result['deleted_ids'])}")
    for entry in result["skipped"]:
        print(f"Skipped #{entry['id']}: {entry['reason']} ({', '.join(entry['contents'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())