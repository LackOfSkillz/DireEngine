from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
GUILDLEADER_TYPECLASS = "typeclasses.npcs.BarbarianGuildleader"
AREA_NAME = "Barbarian Guild"
AREA_SPACE_TAG = "barbarian_guild_space"
MAP_BUILD_TAG = "barbarian-guild-map"
CANONICAL_TAG = "guild_barbarian"
ENTRY_TAG = "guild_barbarian_entry"
JOIN_SITE_TAG = "barbarian_guildhall"

# DRG-BARBARIAN-GUILDHALL-001: directengine_canon placement choice for the
# current free-tier ship. Canon authority is Crossing identity, not this lane.
LANE_DBREF = 4238
LANE_KEY = "Cedarcoil Lane, East Reach"

ROOM_SPECS = {
    "main_hall": {
        "key": "Barbarian Guild",
        "aliases": ["guild", "barbarian guild", "hall"],
        "desc": (
            "The guildhall feels more like a hard-used war room than a civic chamber. Scarred timbers, weapon racks, split practice posts, and the blunt smell of sweat and oil leave no doubt about its purpose. "
            "Nothing here flatters weakness, and nothing asks permission to seem severe."
        ),
        "room_tag": "main_hall",
        "coords": (0, 0),
    },
    "training_floor": {
        "key": "Barbarian Guild, Training Floor",
        "aliases": ["training floor", "training", "floor"],
        "desc": (
            "Heavy dummies, broken hafts, and chalked drill lines crowd the floor beneath a haze of sawdust and old impact scars. The space is built to make endurance a habit rather than a boast."
        ),
        "room_tag": "training_floor",
        "coords": (0, 1),
    },
    "leader_corner": {
        "key": "Barbarian Guild, Leader's Corner",
        "aliases": ["leader corner", "corner", "t'kiel"],
        "desc": (
            "A raised corner of the hall holds a heavy chair, a scarred table, and just enough open space to remind visitors that authority here is enforced in person. Nothing about the arrangement feels ceremonial; it feels practical and final."
        ),
        "room_tag": "leader_corner",
        "coords": (1, 0),
    },
}

EXIT_SPECS = [
    ("main_hall", "north", ["training", "floor"], "training_floor"),
    ("training_floor", "south", ["hall", "guild"], "main_hall"),
    ("main_hall", "east", ["corner", "leader", "t'kiel"], "leader_corner"),
    ("leader_corner", "west", ["hall", "guild"], "main_hall"),
]


def _find_room(*keys):
    wanted = {str(key or "").strip().lower() for key in keys if str(key or "").strip()}
    if not wanted:
        return None
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if str(getattr(room, "key", "") or "").strip().lower() in wanted:
            return room
    return None


def _find_exit(source, *keys):
    if not source:
        return None
    wanted = {str(key or "").strip().lower() for key in keys if str(key or "").strip()}
    for obj in list(getattr(source, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != EXIT_TYPECLASS:
            continue
        if str(getattr(obj, "key", "") or "").strip().lower() in wanted:
            return obj
    return None


def _ensure_room(key, desc, *, aliases=None):
    room = _find_room(key, *(aliases or []))
    if room is None:
        room = create_object(ROOM_TYPECLASS, key=key, nohome=True)
    room.key = key
    room.db.desc = desc
    for alias in aliases or []:
        room.aliases.add(alias)
    return room


def _ensure_exit(source, key, destination, *, aliases=None, existing_keys=None):
    exit_obj = _find_exit(source, key, *(existing_keys or []), *(aliases or []))
    if exit_obj is None:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=source, destination=destination, nohome=True)
    exit_obj.key = key
    exit_obj.destination = destination
    for alias in aliases or []:
        exit_obj.aliases.add(alias)
    return exit_obj


def _ensure_npc(key, location, *, aliases=None, desc=""):
    npc = None
    for obj in list(getattr(location, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != GUILDLEADER_TYPECLASS:
            continue
        if str(getattr(obj, "key", "") or "").strip().lower() in {"t'kiel", "tkiel", "guildleader t'kiel"}:
            npc = obj
            break
    if npc is None:
        npc = create_object(GUILDLEADER_TYPECLASS, key=key, location=location, home=location, nohome=True)
    else:
        npc.location = location
        npc.home = location
    npc.key = key
    npc.db.desc = desc
    for alias in aliases or []:
        npc.aliases.add(alias)
    return npc


def _clear_room_tags(room, tag_names):
    for tag_name in tag_names:
        try:
            room.tags.remove(tag_name)
        except Exception:
            continue


def _find_tagged_room(tag_name):
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        try:
            if room.tags.has(tag_name):
                return room
        except Exception:
            continue
    return None


def ensure_crossing_barbarian_guildhall():
    lane_room = ObjectDB.objects.get_id(LANE_DBREF)
    if lane_room and str(getattr(lane_room, "key", "") or "") != LANE_KEY:
        lane_room = None

    canonical_room = _find_tagged_room(CANONICAL_TAG) or _find_room(ROOM_SPECS["main_hall"]["key"])

    rooms = {}
    for room_key, spec in ROOM_SPECS.items():
        if room_key == "main_hall" and canonical_room:
            room = canonical_room
            room.key = spec["key"]
            room.db.desc = spec["desc"]
        else:
            room = _ensure_room(spec["key"], spec["desc"], aliases=spec.get("aliases"))
        room.db.area = AREA_NAME
        room.db.region_name = "The Landing"
        room.db.guild_tag = JOIN_SITE_TAG
        room.db.barbarian_guild_room = spec["room_tag"]
        room.db.map_x = spec["coords"][0]
        room.db.map_y = spec["coords"][1]
        _clear_room_tags(room, [CANONICAL_TAG, ENTRY_TAG])
        room.tags.add(AREA_SPACE_TAG)
        room.tags.add(JOIN_SITE_TAG)
        room.tags.add(MAP_BUILD_TAG, category="build")
        if room_key == "main_hall":
            room.tags.add(CANONICAL_TAG)
            room.tags.add(ENTRY_TAG)
            room.tags.add("poi_guild_barbarian")
        rooms[room_key] = room

    for source_key, exit_key, aliases, dest_key in EXIT_SPECS:
        _ensure_exit(rooms[source_key], exit_key, rooms[dest_key], aliases=aliases)

    if lane_room:
        lane_room.tags.add("guild_access_barbarian")
        lane_to_guild = _ensure_exit(
            lane_room,
            "guild",
            rooms["main_hall"],
            aliases=["barbarian", "barbarian guild", "hall"],
        )
        lane_to_guild.db.exit_display_name = "Barbarian Guild"
        guild_to_lane = _ensure_exit(
            rooms["main_hall"],
            "out",
            lane_room,
            aliases=["south", "alley", "street", "back"],
            existing_keys=["south"],
        )
        guild_to_lane.db.exit_display_name = "Out"

    tkiel = _ensure_npc(
        "T'Kiel",
        rooms["main_hall"],
        aliases=["guildleader", "barbarian guildleader", "tkiel", "leader"],
        desc=(
            "T'Kiel stands like a block of old stone given human shape, broad-shouldered and unsentimental in the way she watches the room. The Guildmistress carries herself with the confidence of someone who has long since decided that endurance matters more than courtesy."
        ),
    )
    tkiel.db.guild_role = "guildmaster"
    tkiel.db.trains_profession = "barbarian"

    return rooms