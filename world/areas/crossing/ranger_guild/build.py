from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
GUILDLEADER_TYPECLASS = "typeclasses.npcs.RangerGuildleader"
AREA_NAME = "Ranger Guild"
AREA_SPACE_TAG = "ranger_guild_space"
MAP_BUILD_TAG = "ranger-guild-map"
CANONICAL_TAG = "guild_ranger"
ENTRY_TAG = "guild_ranger_entry"
JOIN_SITE_TAG = "ranger_guildhall"

LANE_DBREF = 4244
LANE_KEY = "Cracked Bell Alley, East Reach"

ROOM_SPECS = {
    "main_hall": {
        "key": "Ranger Guild",
        "aliases": ["guild", "ranger guild", "hall", "glade"],
        "desc": (
            "A sheltered hall of timber and living boughs stands just apart from the city's harder edges. "
            "Bow racks, weathered maps, and worn field gear leave no doubt that this guild belongs more to trail and tree line than to stone streets."
        ),
        "room_tag": "main_hall",
        "coords": (0, 0),
    },
    "training_yard": {
        "key": "Ranger Guild, Training Yard",
        "aliases": ["yard", "training yard", "range"],
        "desc": (
            "Targets of straw and wicker line the yard beside a packed run of earth worn smooth by steady drill. "
            "Everything here favors patience, distance, and a clean release over spectacle."
        ),
        "room_tag": "training_yard",
        "coords": (0, 1),
    },
    "council_chamber": {
        "key": "Ranger Guild, Council Chamber",
        "aliases": ["chamber", "council chamber", "council"],
        "desc": (
            "A broad table cut from old wood anchors the chamber beneath maps, trail notes, and weather-marked reports. "
            "The room feels more like a planning shelter than an office, built for decisions that begin outdoors and end there."
        ),
        "room_tag": "council_chamber",
        "coords": (1, 0),
    },
    "perch": {
        "key": "Ranger Guild, Perch",
        "aliases": ["perch", "lookout", "platform"],
        "desc": (
            "A raised perch looks over the lane and the roofs beyond it, offering a cleaner line to wind, weather, and distant movement than the city usually allows. "
            "From here, even the Crossing feels like something observed rather than obeyed."
        ),
        "room_tag": "perch",
        "coords": (-1, 1),
    },
}

EXIT_SPECS = [
    ("main_hall", "north", ["yard", "training"], "training_yard"),
    ("training_yard", "south", ["hall", "guild"], "main_hall"),
    ("main_hall", "east", ["chamber", "council"], "council_chamber"),
    ("council_chamber", "west", ["hall", "guild"], "main_hall"),
    ("main_hall", "up", ["perch", "lookout"], "perch"),
    ("perch", "down", ["hall", "guild"], "main_hall"),
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
        if str(getattr(obj, "key", "") or "").strip().lower() in {"kalika", "guildleader kalika"}:
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


def ensure_crossing_ranger_guildhall():
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
        room.db.ranger_guild_room = spec["room_tag"]
        room.db.map_x = spec["coords"][0]
        room.db.map_y = spec["coords"][1]
        _clear_room_tags(room, [CANONICAL_TAG, ENTRY_TAG])
        room.tags.add(AREA_SPACE_TAG)
        room.tags.add(JOIN_SITE_TAG)
        room.tags.add(MAP_BUILD_TAG, category="build")
        if room_key == "main_hall":
            room.tags.add(CANONICAL_TAG)
            room.tags.add(ENTRY_TAG)
            room.tags.add("poi_guild_ranger")
        rooms[room_key] = room

    for source_key, exit_key, aliases, dest_key in EXIT_SPECS:
        _ensure_exit(rooms[source_key], exit_key, rooms[dest_key], aliases=aliases)

    if lane_room:
        lane_room.tags.add("guild_access_ranger")
        lane_to_guild = _ensure_exit(
            lane_room,
            "guild",
            rooms["main_hall"],
            aliases=["ranger", "ranger guild", "glade"],
            existing_keys=["north"],
        )
        lane_to_guild.db.exit_display_name = "Ranger Guild"
        guild_to_lane = _ensure_exit(
            rooms["main_hall"],
            "out",
            lane_room,
            aliases=["south", "alley", "street", "back"],
            existing_keys=["south"],
        )
        guild_to_lane.db.exit_display_name = "Out"

    kalika = _ensure_npc(
        "Kalika",
        rooms["main_hall"],
        aliases=["guildleader", "ranger guildleader", "leader"],
        desc=(
            "An elven ranger with ginger hair and the easy balance of someone more accustomed to root and ridge than to city stone watches the room from beside an ash longbow. "
            "A falchion rides at her side above weathered leather, green cotton, and soft doeskin worked for long travel."
        ),
    )
    kalika.db.guild_role = "guildmaster"
    kalika.db.trains_profession = "ranger"

    return rooms