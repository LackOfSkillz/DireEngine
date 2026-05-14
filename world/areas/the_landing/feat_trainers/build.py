from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
TRAINER_TYPECLASS = "typeclasses.feat_trainer.FeatTrainerNPC"
AREA_NAME = "The Landing"
MAP_BUILD_TAG = "landing-feat-trainers"
HUB_DBREF = 4305
HUB_KEY = "Town Green NE"
ROOM_KEY = "The Hall of Arcane Refinement"
TRAINER_KEY = "Instructor Sariel"


def _find_room(*keys):
    wanted = [str(key or "").strip() for key in keys if str(key or "").strip()]
    for key in wanted:
        room = ObjectDB.objects.filter(db_key__iexact=key, db_typeclass_path=ROOM_TYPECLASS).first()
        if room:
            return room
    return None


def _find_exit(room, *names):
    wanted = {str(name or "").strip().lower() for name in names if str(name or "").strip()}
    if not room or not wanted:
        return None
    for exit_obj in list(getattr(room, "exits", []) or []):
        key = str(getattr(exit_obj, "key", "") or "").strip().lower()
        aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()}
        if key in wanted or aliases.intersection(wanted):
            return exit_obj
    return None


def _find_hub_room():
    room = ObjectDB.objects.get_id(HUB_DBREF)
    if room and str(getattr(room, "key", "") or "") == HUB_KEY:
        return room
    return _find_room(HUB_KEY)


def _ensure_room():
    room = _find_room(ROOM_KEY)
    if not room:
        room = create_object(ROOM_TYPECLASS, key=ROOM_KEY)
    room.key = ROOM_KEY
    room.db.desc = (
        "Shelves of annotated spell diagrams and chalk-scored practice matrices line the walls of this quiet hall. "
        "The room feels less like a classroom than a place where small inefficiencies are hunted down and corrected. "
        "A single instructor watches from beside a standing slate covered in mana-flow notes."
    )
    room.db.area = AREA_NAME
    room.db.region_name = AREA_NAME
    room.tags.add(MAP_BUILD_TAG, category="build")
    room.tags.add("feat_trainer")
    room.db.feat_trainer = True
    return room


def _ensure_exit(src, key, dest, aliases=None, existing_keys=None):
    exit_obj = _find_exit(src, key, *(existing_keys or []))
    if not exit_obj:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=src, destination=dest, home=src)
    exit_obj.key = key
    exit_obj.destination = dest
    exit_obj.aliases.clear()
    for alias in aliases or []:
        exit_obj.aliases.add(alias)
    return exit_obj


def _ensure_trainer(room):
    trainer = ObjectDB.objects.filter(db_key__iexact=TRAINER_KEY, db_location=room).first()
    if not trainer:
        trainer = create_object(TRAINER_TYPECLASS, key=TRAINER_KEY, location=room, home=room)
    trainer.key = TRAINER_KEY
    trainer.db.is_npc = True
    trainer.db.is_trainer = True
    trainer.db.trainer_kind = "feat"
    trainer.db.desc = (
        "Sariel watches magical work the way a veteran armorer watches cracks under a fresh polish. "
        "Nothing in the room seems likely to escape that attention for long."
    )
    trainer.aliases.add("sariel")
    trainer.aliases.add("instructor")
    trainer.aliases.add("feat trainer")
    return trainer


def ensure_the_landing_feat_trainers():
    hub_room = _find_hub_room()
    if not hub_room:
        return None
    room = _ensure_room()
    _ensure_trainer(room)
    to_room = _ensure_exit(
        hub_room,
        "feats",
        room,
        aliases=["feat", "feat hall", "arcane hall", "sariel"],
        existing_keys=["feats"],
    )
    to_room.db.exit_display_name = ROOM_KEY
    to_hub = _ensure_exit(room, "out", hub_room, aliases=["back", "green", "town green", "hub"], existing_keys=["out"])
    to_hub.db.exit_display_name = "Out"
    return room