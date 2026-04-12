from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
NPC_TYPECLASS = "typeclasses.npcs.NPC"
HEALER_TYPECLASS = "typeclasses.npcs.HealerNPC"
GUILDLEADER_TYPECLASS = "typeclasses.npcs.EmpathGuildleader"
AREA_NAME = "Empath Guild"
AREA_SPACE_TAG = "empath_guild_space"
MAP_BUILD_TAG = "empath-guild-map"
CANONICAL_TAG = "guild_empath"
ENTRY_TAG = "guild_empath_entry"
JOIN_SITE_TAG = "empath_guildhall"
ZONE_TAGS = {
    "recovery": "empath_zone_recovery",
    "training": "empath_zone_training",
    "triage": "empath_zone_triage",
}
ROOM_ZONES = {
    "entry_hall": ("triage",),
    "infirmary": ("triage", "recovery"),
    "sitting_room": ("recovery",),
    "training": ("training",),
    "viewing_area": ("training",),
    "blue_area": ("triage",),
    "yellow_area": ("triage",),
    "white_area": ("triage",),
}

LANE_DBREF = 4280
LANE_KEY = "Larkspur Lane, Midway"

ROOM_SPECS = {
    "entry_hall": {
        "key": "Empath Guild, Entry Hall",
        "legacy_keys": ["Empath Guild, Main Hall"],
        "aliases": ["entry hall", "entry", "foyer", "guild entry"],
        "desc": (
            "The guild's southern hall opens directly toward the Crossing, making it the first refuge for the limping, the fevered, "
            "and the desperate. A broad stair rises deeper into the guild, while side passages break toward quieter workrooms. "
            "Nothing here feels ceremonial. It feels ready."
        ),
        "room_tag": "entry_hall",
        "coords": (0, 3),
    },
    "main_hall": {
        "key": "Empath Guild",
        "aliases": ["main hall", "hall", "healerie", "guild"],
        "desc": (
            "This central landing ties the working heart of the guild together. Doors open toward the blue treatment area, "
            "a western arch, and the upper instructional wing, while the stair back down leads toward the public-facing rooms. "
            "The air is clean, hushed, and full of pain being managed before it becomes panic."
        ),
        "room_tag": "main_hall",
        "coords": (0, 0),
    },
    "infirmary": {
        "key": "Empath Guild, Infirmary",
        "aliases": ["infirmary", "ward"],
        "desc": (
            "Curtained bedspaces and neatly ordered trays fill the infirmary. "
            "Everything here is arranged for triage first and comfort second."
        ),
        "room_tag": "infirmary",
        "coords": (-2, 3),
    },
    "sitting_room": {
        "key": "Empath Guild, Sitting Room",
        "aliases": ["sitting room", "parlor", "quiet room"],
        "desc": (
            "Soft chairs and low tables make this one of the few rooms in the guild intended for stillness instead of crisis. "
            "Even here, the hush is the hush of healers between burdens rather than leisure."
        ),
        "room_tag": "sitting_room",
        "coords": (-2, 1),
    },
    "office": {
        "key": "Empath Guildleader's Office",
        "aliases": ["office", "guildleader office", "leader office"],
        "desc": (
            "Ledgers, patient notes, and a severe writing desk leave little doubt about the room's purpose. "
            "This is where judgment is passed on who may bear the guild's burden."
        ),
        "room_tag": "office",
        "coords": (2, 1),
    },
    "library": {
        "key": "Empath Guild, Library",
        "aliases": ["library", "stacks", "books"],
        "desc": (
            "Shelves of anatomy, herbals, and guild records line the walls from floor to lintel. "
            "The room smells of vellum, lavender, and long study under pressure."
        ),
        "room_tag": "library",
        "coords": (2, 2),
    },
    "west_arch": {
        "key": "Empath Guild, West Arch",
        "aliases": ["arch", "west arch", "arch hall"],
        "desc": (
            "A broad arch frames the western side of the guild, where lectures, city access, and the deeper treatment wing all brush against one another. "
            "The stone here bears the wear of urgent feet and practiced routine."
        ),
        "room_tag": "west_arch",
        "coords": (-2, 0),
    },
    "training": {
        "key": "Empath Guild, Lecture Hall",
        "legacy_keys": ["Empath Guild, Training Room"],
        "aliases": ["lecture hall", "lecture", "training room", "practice room", "training"],
        "desc": (
            "Tiered benches and a demonstration space make this room equal parts classroom and hard lesson. "
            "What is taught here is never abstract for long."
        ),
        "room_tag": "training",
        "coords": (-2, -2),
    },
    "viewing_area": {
        "key": "Empath Guild, Viewing Area",
        "aliases": ["viewing area", "gallery", "overview"],
        "desc": (
            "A raised viewing space looks down over the treatment chambers below, allowing instruction and supervision without crowding the work. "
            "From here, patterns of pain become lessons."
        ),
        "room_tag": "viewing_area",
        "coords": (2, -2),
    },
    "blue_area": {
        "key": "Empath Guild, Blue Area",
        "aliases": ["blue area", "blue ward", "blue"],
        "desc": (
            "Blue drapery and crisp linens distinguish this treatment chamber from the others around it. "
            "Everything is ordered for patients who need calm hands and quick assessment."
        ),
        "room_tag": "blue_area",
        "coords": (2, 0),
    },
    "yellow_area": {
        "key": "Empath Guild, Yellow Area",
        "aliases": ["yellow area", "yellow ward", "yellow"],
        "desc": (
            "Warm-toned curtains soften the light here, but not the urgency. The yellow area feels prepared for difficult cases watched at length."
        ),
        "room_tag": "yellow_area",
        "coords": (4, -2),
    },
    "white_area": {
        "key": "Empath Guild, White Area",
        "aliases": ["white area", "white ward", "white"],
        "desc": (
            "Whitewashed screens and immaculate bandaging tables give this chamber a near-clinical starkness. "
            "It is the sort of room where every stain is noticed and every lapse matters."
        ),
        "room_tag": "white_area",
        "coords": (4, 0),
    },
}

EXIT_SPECS = (
    ("entry_hall", "north", ["stair", "up", "guild"], "main_hall"),
    ("main_hall", "south", ["stairs", "down", "entry"], "entry_hall"),
    ("entry_hall", "west", ["infirmary", "ward"], "infirmary"),
    ("infirmary", "east", ["hall", "entry"], "entry_hall"),
    ("infirmary", "north", ["door", "sitting room", "sitting"], "sitting_room"),
    ("sitting_room", "south", ["infirmary", "door"], "infirmary"),
    ("entry_hall", "east", ["library", "books"], "library"),
    ("library", "west", ["hall", "entry"], "entry_hall"),
    ("entry_hall", "northeast", ["office", "guildleader"], "office"),
    ("office", "southwest", ["hall", "entry"], "entry_hall"),
    ("main_hall", "west", ["arch", "west arch"], "west_arch"),
    ("west_arch", "east", ["hall", "healerie"], "main_hall"),
    ("west_arch", "north", ["door", "lecture hall", "lecture"], "training"),
    ("training", "south", ["arch", "door"], "west_arch"),
    ("main_hall", "east", ["doors", "blue area", "blue"], "blue_area"),
    ("blue_area", "west", ["hall", "doors"], "main_hall"),
    ("blue_area", "north", ["viewing area", "viewing"], "viewing_area"),
    ("viewing_area", "south", ["blue area", "blue"], "blue_area"),
    ("viewing_area", "east", ["yellow area", "yellow"], "yellow_area"),
    ("yellow_area", "west", ["viewing area", "viewing"], "viewing_area"),
    ("blue_area", "east", ["white area", "white"], "white_area"),
    ("white_area", "west", ["blue area", "blue"], "blue_area"),
    ("yellow_area", "south", ["white area", "white"], "white_area"),
    ("white_area", "north", ["yellow area", "yellow"], "yellow_area"),
    ("viewing_area", "southeast", ["white area"], "white_area"),
    ("white_area", "northwest", ["viewing area"], "viewing_area"),
    ("blue_area", "northeast", ["yellow area"], "yellow_area"),
    ("yellow_area", "southwest", ["blue area"], "blue_area"),
)


def _find_room(*keys):
    wanted = [str(key or "").strip() for key in keys if str(key or "").strip()]
    for key in wanted:
        room = ObjectDB.objects.filter(db_key__iexact=key, db_typeclass_path=ROOM_TYPECLASS).first()
        if room:
            return room
    return None


def _search_tag(tag_name):
    return ObjectDB.objects.get_by_tag(tag_name)


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


def _ensure_room(key, desc, aliases=None, legacy_keys=None):
    room = _find_room(key, *(legacy_keys or []))
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key)
    room.key = key
    room.db.desc = desc
    room.db.area = AREA_NAME
    room.db.region_name = "The Landing"
    for alias in aliases or []:
        room.aliases.add(alias)
    return room


def _ensure_exit(src, key, dest, aliases=None, existing_keys=None):
    exit_obj = _find_exit(src, key, *(existing_keys or []), *(aliases or []))
    if not exit_obj:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=src, destination=dest, home=src)
    exit_obj.key = key
    exit_obj.destination = dest
    for alias in aliases or []:
        exit_obj.aliases.add(alias)
    return exit_obj


def _ensure_npc(typeclass, key, room, aliases=None, desc=""):
    npc = ObjectDB.objects.filter(db_key__iexact=key, db_location=room).first()
    if not npc:
        npc = create_object(typeclass, key=key, location=room, home=room)
    npc.key = key
    npc.home = room
    if getattr(npc, "location", None) != room:
        npc.move_to(room, quiet=True, use_destination=False)
    npc.db.desc = desc
    npc.db.is_npc = True
    for alias in aliases or []:
        npc.aliases.add(alias)
    return npc


def _ensure_ambient_npcs(rooms):
    entry_hall = rooms["entry_hall"]
    hall = rooms["main_hall"]
    infirmary = rooms["infirmary"]
    _ensure_npc(
        NPC_TYPECLASS,
        "Attending Empath",
        hall,
        aliases=["empath", "attending healer"],
        desc="An apprentice empath keeps one eye on the treatment wing and another on the stair, reading the room before anyone speaks.",
    )
    _ensure_npc(
        NPC_TYPECLASS,
        "Wounded Traveler",
        entry_hall,
        aliases=["traveler", "patient"],
        desc="A tired traveler waits with both hands wrapped and an expression set hard against pain.",
    )
    _ensure_npc(
        NPC_TYPECLASS,
        "Resting Patient",
        infirmary,
        aliases=["patient", "resting patient"],
        desc="A recovering patient lies still beneath a folded blanket while a careful dressing dries cleanly.",
    )
    _ensure_npc(
        HEALER_TYPECLASS,
        "House Healer",
        infirmary,
        aliases=["healer", "attending healer", "house healer"],
        desc="A composed healer stands ready to provide practical treatment for those who cannot wait on player charity.",
    )
    _ensure_npc(
        NPC_TYPECLASS,
        "Guild Librarian",
        rooms["library"],
        aliases=["librarian", "archivist"],
        desc="A careful guild librarian keeps records close at hand and watches borrowers the way a surgeon watches a knife.",
    )


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


def ensure_crossing_empath_guildhall():
    lane_room = ObjectDB.objects.get_id(LANE_DBREF)
    if lane_room and str(getattr(lane_room, "key", "") or "") != LANE_KEY:
        lane_room = None

    canonical_room = _find_tagged_room(CANONICAL_TAG) or _find_room(ROOM_SPECS["main_hall"]["key"])
    entry_room = _find_tagged_room(ENTRY_TAG) or _find_room(ROOM_SPECS["entry_hall"]["key"], *ROOM_SPECS["entry_hall"].get("legacy_keys", []))
    if not entry_room and lane_room:
        lane_exit = _find_exit(lane_room, "guild", "north")
        candidate = getattr(lane_exit, "destination", None)
        if candidate and getattr(candidate, "db_typeclass_path", "") == ROOM_TYPECLASS and candidate != canonical_room:
            entry_room = candidate

    rooms = {}
    for room_key, spec in ROOM_SPECS.items():
        if room_key == "main_hall" and canonical_room:
            room = canonical_room
            room.key = spec["key"]
            room.db.desc = spec["desc"]
        elif room_key == "entry_hall" and entry_room:
            room = entry_room
            room.key = spec["key"]
            room.db.desc = spec["desc"]
        else:
            room = _ensure_room(spec["key"], spec["desc"], aliases=spec["aliases"], legacy_keys=spec.get("legacy_keys"))
        room.db.area = AREA_NAME
        room.db.region_name = "The Landing"
        room.db.guild_tag = JOIN_SITE_TAG
        room.db.empath_guild_room = spec["room_tag"]
        room.db.map_x = spec["coords"][0]
        room.db.map_y = spec["coords"][1]
        zone_names = ROOM_ZONES.get(room_key, ())
        room.db.empath_zone = zone_names[0] if zone_names else ""
        _clear_room_tags(room, [CANONICAL_TAG, ENTRY_TAG, *ZONE_TAGS.values()])
        room.tags.add(AREA_SPACE_TAG)
        room.tags.add(JOIN_SITE_TAG)
        room.tags.add(MAP_BUILD_TAG, category="build")
        for zone_name in zone_names:
            room.tags.add(ZONE_TAGS[zone_name])
        if room_key == "main_hall":
            room.tags.add(CANONICAL_TAG)
            room.tags.add("poi_guild_empath")
        if room_key == "entry_hall":
            room.tags.add(ENTRY_TAG)
        rooms[room_key] = room

    for source_key, exit_key, aliases, dest_key in EXIT_SPECS:
        _ensure_exit(rooms[source_key], exit_key, rooms[dest_key], aliases=aliases)

    if lane_room:
        lane_room.tags.add("guild_access_empath")
        lane_to_guild = _ensure_exit(
            lane_room,
            "north",
            rooms["entry_hall"],
            aliases=["empath", "empath guild", "door", "guild"],
            existing_keys=["guild"],
        )
        lane_to_guild.db.exit_display_name = "Empath Guild"
        guild_to_lane = _ensure_exit(
            rooms["entry_hall"],
            "out",
            lane_room,
            aliases=["south", "street", "lane", "back"],
            existing_keys=["south"],
        )
        guild_to_lane.db.exit_display_name = "Out"
        west_arch_to_lane = _ensure_exit(
            rooms["west_arch"],
            "west",
            lane_room,
            aliases=["arch", "crossing", "city"],
            existing_keys=["crossing"],
        )
        west_arch_to_lane.db.exit_display_name = "Crossing"

    leader = _ensure_npc(
        GUILDLEADER_TYPECLASS,
        "Guildleader Merla",
        rooms["office"],
        aliases=["guildleader", "merla", "leader"],
        desc="Merla watches with the still, measuring focus of someone who has carried too much pain to waste words on ceremony.",
    )
    leader.db.guild_role = "guildmaster"
    leader.db.trains_profession = "empath"

    _ensure_ambient_npcs(rooms)
    return rooms